import asyncio
import inspect
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

import websockets
from websockets.exceptions import ConnectionClosed

from src.config import settings
from src.models import OHLCV, OrderBook, OrderBookLevel, Trade

logger = logging.getLogger(__name__)


AsyncOrSyncCallback = Union[
    Callable[[Any], Any],
    Callable[[Any], Awaitable[Any]],
]


@dataclass
class _Backoff:
    base: float
    max_delay: float
    jitter: float
    attempt: int = 0

    def next_delay(self) -> float:
        # exponential backoff with jitter
        delay = min(self.max_delay, self.base * (2 ** self.attempt))
        self.attempt += 1
        if self.jitter > 0:
            delay = max(0.0, delay + random.uniform(-self.jitter, self.jitter))
        return delay

    def reset(self) -> None:
        self.attempt = 0


class BybitWebSocketClient:
    """
    Bybit Public WebSocket client focused on:
    - Robust reconnect with exponential backoff (+ jitter)
    - Backpressure control via bounded queues
    - Throttled callbacks for high-frequency streams (orderbook/trades)

    Notes:
    - Orderbook is stored internally as price->qty maps (bids/asks) and materialized
      into sorted levels only at publish cadence.
    - Trades / klines are queued; if queue is full, oldest items are dropped.
    """

    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.ws_url = settings.bybit_ws_public_url

        # Settings-driven tunables
        self.ping_interval_sec: float = float(getattr(settings, "bybit_ws_ping_interval_sec", 20))
        self.connect_timeout_sec: float = float(getattr(settings, "bybit_ws_connect_timeout_sec", 10))
        self.orderbook_depth: int = int(getattr(settings, "bybit_ws_orderbook_depth", 50))
        self.orderbook_publish_hz: float = float(getattr(settings, "bybit_ws_orderbook_publish_hz", 2.0))
        self.trade_publish_interval_sec: float = float(getattr(settings, "bybit_ws_trade_publish_interval_sec", 0.5))
        self.max_queue: int = int(getattr(settings, "bybit_ws_max_queue", 2000))

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running: bool = False

        self.orderbook_callback: Optional[AsyncOrSyncCallback] = None
        self.trade_callback: Optional[AsyncOrSyncCallback] = None
        self.kline_callback: Optional[AsyncOrSyncCallback] = None

        # Internal state for orderbook (maps) and last ts
        self._bids: Dict[float, float] = {}
        self._asks: Dict[float, float] = {}
        self._orderbook_symbol: str = symbol
        self._orderbook_ts_ms: int = 0
        self._has_snapshot: bool = False
        self._orderbook_dirty = asyncio.Event()

        # Queues for high frequency streams
        self._trade_q: asyncio.Queue[Trade] = asyncio.Queue(maxsize=self.max_queue)
        self._kline_q: asyncio.Queue[OHLCV] = asyncio.Queue(maxsize=self.max_queue)

        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._orderbook_publish_task: Optional[asyncio.Task] = None
        self._trade_publish_task: Optional[asyncio.Task] = None
        self._kline_publish_task: Optional[asyncio.Task] = None

        self._backoff = _Backoff(
            base=float(getattr(settings, "bybit_ws_reconnect_base_delay_sec", 2)),
            max_delay=float(getattr(settings, "bybit_ws_reconnect_max_delay_sec", 60)),
            jitter=float(getattr(settings, "bybit_ws_reconnect_jitter_sec", 0.5)),
        )

    def on_orderbook(self, callback: AsyncOrSyncCallback) -> None:
        self.orderbook_callback = callback

    def on_trade(self, callback: AsyncOrSyncCallback) -> None:
        self.trade_callback = callback

    def on_kline(self, callback: AsyncOrSyncCallback) -> None:
        self.kline_callback = callback

    async def _maybe_await(self, cb: AsyncOrSyncCallback, payload: Any) -> None:
        try:
            res = cb(payload)
            if inspect.isawaitable(res):
                await res
        except Exception:
            logger.exception("Callback raised an exception")

    async def connect(self) -> bool:
        try:
            self.ws = await asyncio.wait_for(
                websockets.connect(self.ws_url, ping_interval=None),
                timeout=self.connect_timeout_sec,
            )
            logger.info("Connected to Bybit WebSocket: %s", self.ws_url)
            self._backoff.reset()
            return True
        except Exception as e:
            logger.error("Failed to connect to WebSocket: %s", e)
            self.ws = None
            return False

    async def subscribe(self, channels: List[str]) -> None:
        if not self.ws:
            logger.error("WebSocket not connected")
            return

        subscribe_msg = {"op": "subscribe", "args": channels}
        try:
            await self.ws.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to channels: %s", channels)
        except Exception as e:
            logger.error("Failed to subscribe: %s", e)

    # -----------------------
    # Orderbook handling
    # -----------------------
    async def _handle_orderbook_snapshot(self, data: Dict[str, Any]) -> None:
        try:
            ob = data.get("data", {}) or {}
            self._orderbook_symbol = ob.get("s", self.symbol)
            self._orderbook_ts_ms = int(ob.get("ts", 0) or 0)

            bids = ob.get("b", []) or []
            asks = ob.get("a", []) or []

            self._bids = {float(p): float(q) for p, q in bids if float(q) > 0}
            self._asks = {float(p): float(q) for p, q in asks if float(q) > 0}

            self._has_snapshot = True
            self._orderbook_dirty.set()
        except Exception as e:
            logger.error("Error handling orderbook snapshot: %s", e)

    async def _handle_orderbook_delta(self, data: Dict[str, Any]) -> None:
        if not self._has_snapshot:
            # Ignore deltas until we have a snapshot
            return

        try:
            ob = data.get("data", {}) or {}
            self._orderbook_ts_ms = int(ob.get("ts", 0) or self._orderbook_ts_ms)

            for p, q in (ob.get("b", []) or []):
                price = float(p)
                qty = float(q)
                if qty <= 0:
                    self._bids.pop(price, None)
                else:
                    self._bids[price] = qty

            for p, q in (ob.get("a", []) or []):
                price = float(p)
                qty = float(q)
                if qty <= 0:
                    self._asks.pop(price, None)
                else:
                    self._asks[price] = qty

            self._orderbook_dirty.set()
        except Exception as e:
            logger.error("Error handling orderbook delta: %s", e)

    def _materialize_orderbook(self) -> OrderBook:
        # materialize top N bids/asks
        bids_sorted = sorted(self._bids.items(), key=lambda x: x[0], reverse=True)[: self.orderbook_depth]
        asks_sorted = sorted(self._asks.items(), key=lambda x: x[0])[: self.orderbook_depth]

        bids = [OrderBookLevel(price=p, quantity=q) for p, q in bids_sorted]
        asks = [OrderBookLevel(price=p, quantity=q) for p, q in asks_sorted]

        return OrderBook(
            symbol=self._orderbook_symbol,
            timestamp=datetime.fromtimestamp(self._orderbook_ts_ms / 1000) if self._orderbook_ts_ms else datetime.utcfromtimestamp(0),
            bids=bids,
            asks=asks,
        )

    async def _orderbook_publisher(self) -> None:
        if self.orderbook_publish_hz <= 0:
            # Publish on every change (not recommended)
            while self.is_running:
                await self._orderbook_dirty.wait()
                self._orderbook_dirty.clear()
                if self.orderbook_callback and self._has_snapshot:
                    await self._maybe_await(self.orderbook_callback, self._materialize_orderbook())
            return

        interval = 1.0 / self.orderbook_publish_hz
        while self.is_running:
            try:
                # Wait for a change or timeout to keep cadence.
                try:
                    await asyncio.wait_for(self._orderbook_dirty.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass

                if not self._orderbook_dirty.is_set():
                    continue

                self._orderbook_dirty.clear()
                if self.orderbook_callback and self._has_snapshot:
                    await self._maybe_await(self.orderbook_callback, self._materialize_orderbook())
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Orderbook publisher error")

    # -----------------------
    # Trade / Kline handling
    # -----------------------
    async def _enqueue_drop_oldest(self, q: asyncio.Queue, item: Any) -> None:
        if q.full():
            try:
                _ = q.get_nowait()
            except Exception:
                pass
        await q.put(item)

    async def _handle_trade(self, data: Dict[str, Any]) -> None:
        try:
            trade_data = data.get("data", []) or []
            for item in trade_data:
                trade = Trade(
                    symbol=item.get("s", self.symbol),
                    timestamp=datetime.fromtimestamp((item.get("T", 0) or 0) / 1000),
                    price=float(item.get("p", 0) or 0),
                    quantity=float(item.get("v", 0) or 0),
                    side=(item.get("S", "") or "").lower(),  # Convert to lowercase for Pydantic validation
                )
                await self._enqueue_drop_oldest(self._trade_q, trade)
        except Exception as e:
            logger.error("Error handling trade: %s", e)

    async def _handle_kline(self, data: Dict[str, Any]) -> None:
        try:
            kline_list = data.get("data", []) or []
            for k in kline_list:
                kline = OHLCV(
                    symbol=self.symbol,
                    timestamp=datetime.fromtimestamp((k.get("start", 0) or 0) / 1000),
                    open=float(k.get("open", 0) or 0),
                    high=float(k.get("high", 0) or 0),
                    low=float(k.get("low", 0) or 0),
                    close=float(k.get("close", 0) or 0),
                    volume=float(k.get("volume", 0) or 0),
                    timeframe=str(k.get("interval", "") or ""),
                )
                await self._enqueue_drop_oldest(self._kline_q, kline)
        except Exception as e:
            logger.error("Error handling kline: %s", e)

    async def _trade_publisher(self) -> None:
        while self.is_running:
            try:
                if not self.trade_callback:
                    # If there's no consumer yet, avoid building up unbounded latency; just drain.
                    try:
                        _ = await asyncio.wait_for(self._trade_q.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
                    continue

                # Batch for a short interval to reduce callback overhead
                batch: List[Trade] = []
                start = asyncio.get_running_loop().time()

                while True:
                    remaining = self.trade_publish_interval_sec - (asyncio.get_running_loop().time() - start)
                    if remaining <= 0:
                        break
                    try:
                        t = await asyncio.wait_for(self._trade_q.get(), timeout=remaining)
                        batch.append(t)
                    except asyncio.TimeoutError:
                        break

                for t in batch:
                    await self._maybe_await(self.trade_callback, t)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Trade publisher error")

    async def _kline_publisher(self) -> None:
        while self.is_running:
            try:
                k = await self._kline_q.get()
                if self.kline_callback:
                    await self._maybe_await(self.kline_callback, k)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Kline publisher error")

    # -----------------------
    # Message processing
    # -----------------------
    async def _process_message(self, message: str) -> None:
        try:
            data = json.loads(message)

            # bybit public WS uses op pong for ping responses
            if data.get("op") == "pong":
                return

            topic = data.get("topic", "") or ""

            if "orderbook" in topic:
                msg_type = data.get("type", "") or ""
                if msg_type == "snapshot":
                    await self._handle_orderbook_snapshot(data)
                elif msg_type == "delta":
                    await self._handle_orderbook_delta(data)

            elif "publicTrade" in topic:
                await self._handle_trade(data)

            elif "kline" in topic:
                await self._handle_kline(data)

        except json.JSONDecodeError as e:
            logger.error("Failed to decode message: %s", e)
        except Exception:
            logger.exception("Error processing message")

    async def _heartbeat(self) -> None:
        while self.is_running and self.ws:
            try:
                await self.ws.send(json.dumps({"op": "ping"}))
                await asyncio.sleep(self.ping_interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error: %s", e)
                break

    def _cancel_task(self, t: Optional[asyncio.Task]) -> None:
        if t and not t.done():
            t.cancel()

    async def _close_ws(self) -> None:
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            finally:
                self.ws = None

    async def start(self, channels: List[str]) -> None:
        """
        Connects and runs until stop() is called.
        Reconnects automatically on disconnect with exponential backoff.
        """
        self.is_running = True

        # start publishers (persist across reconnects)
        self._orderbook_publish_task = asyncio.create_task(self._orderbook_publisher())
        self._trade_publish_task = asyncio.create_task(self._trade_publisher())
        self._kline_publish_task = asyncio.create_task(self._kline_publisher())

        while self.is_running:
            try:
                connected = await self.connect()
                if not connected:
                    await asyncio.sleep(self._backoff.next_delay())
                    continue

                await self.subscribe(channels)

                self._heartbeat_task = asyncio.create_task(self._heartbeat())

                async for message in self.ws:
                    await self._process_message(message)

            except ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("WebSocket error: %s", e)
            finally:
                self._cancel_task(self._heartbeat_task)
                self._heartbeat_task = None
                await self._close_ws()

                if self.is_running:
                    await asyncio.sleep(self._backoff.next_delay())

        # shutdown publishers
        self._cancel_task(self._orderbook_publish_task)
        self._cancel_task(self._trade_publish_task)
        self._cancel_task(self._kline_publish_task)

        logger.info("BybitWebSocketClient stopped")

    async def stop(self) -> None:
        self.is_running = False
        self._orderbook_dirty.set()
        self._cancel_task(self._heartbeat_task)
        await self._close_ws()
