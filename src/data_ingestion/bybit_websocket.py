import asyncio
import json
import logging
from typing import Callable, Dict, Optional, List
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed

from src.config import settings
from src.models import OrderBook, OrderBookLevel, Trade, OHLCV

logger = logging.getLogger(__name__)


class BybitWebSocketClient:
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.ws_url = settings.bybit_ws_public_url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False

        self.orderbook_callback: Optional[Callable] = None
        self.trade_callback: Optional[Callable] = None
        self.kline_callback: Optional[Callable] = None

        self.orderbook_data: Optional[OrderBook] = None
        self.reconnect_delay = 5

    def on_orderbook(self, callback: Callable):
        self.orderbook_callback = callback

    def on_trade(self, callback: Callable):
        self.trade_callback = callback

    def on_kline(self, callback: Callable):
        self.kline_callback = callback

    async def connect(self):
        try:
            self.ws = await websockets.connect(self.ws_url)
            logger.info(f"Connected to Bybit WebSocket: {self.ws_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def subscribe(self, channels: List[str]):
        if not self.ws:
            logger.error("WebSocket not connected")
            return

        subscribe_msg = {
            "op": "subscribe",
            "args": channels
        }

        try:
            await self.ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to channels: {channels}")
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")

    async def _handle_orderbook_snapshot(self, data: Dict):
        try:
            orderbook_data = data.get("data", {})
            bids = [
                OrderBookLevel(price=float(bid[0]), quantity=float(bid[1]))
                for bid in orderbook_data.get("b", [])
            ]
            asks = [
                OrderBookLevel(price=float(ask[0]), quantity=float(ask[1]))
                for ask in orderbook_data.get("a", [])
            ]

            self.orderbook_data = OrderBook(
                symbol=orderbook_data.get("s", self.symbol),
                timestamp=datetime.fromtimestamp(orderbook_data.get("ts", 0) / 1000),
                bids=bids,
                asks=asks
            )

            if self.orderbook_callback:
                await self.orderbook_callback(self.orderbook_data)

        except Exception as e:
            logger.error(f"Error handling orderbook snapshot: {e}")

    async def _handle_orderbook_delta(self, data: Dict):
        if not self.orderbook_data:
            return

        try:
            orderbook_data = data.get("data", {})

            for bid in orderbook_data.get("b", []):
                price, qty = float(bid[0]), float(bid[1])
                if qty == 0:
                    self.orderbook_data.bids = [
                        b for b in self.orderbook_data.bids if b.price != price
                    ]
                else:
                    updated = False
                    for b in self.orderbook_data.bids:
                        if b.price == price:
                            b.quantity = qty
                            updated = True
                            break
                    if not updated:
                        self.orderbook_data.bids.append(
                            OrderBookLevel(price=price, quantity=qty)
                        )

            for ask in orderbook_data.get("a", []):
                price, qty = float(ask[0]), float(ask[1])
                if qty == 0:
                    self.orderbook_data.asks = [
                        a for a in self.orderbook_data.asks if a.price != price
                    ]
                else:
                    updated = False
                    for a in self.orderbook_data.asks:
                        if a.price == price:
                            a.quantity = qty
                            updated = True
                            break
                    if not updated:
                        self.orderbook_data.asks.append(
                            OrderBookLevel(price=price, quantity=qty)
                        )

            self.orderbook_data.bids.sort(key=lambda x: x.price, reverse=True)
            self.orderbook_data.asks.sort(key=lambda x: x.price)

            self.orderbook_data.timestamp = datetime.fromtimestamp(
                orderbook_data.get("ts", 0) / 1000
            )

            if self.orderbook_callback:
                await self.orderbook_callback(self.orderbook_data)

        except Exception as e:
            logger.error(f"Error handling orderbook delta: {e}")

    async def _handle_trade(self, data: Dict):
        try:
            trade_data = data.get("data", [])
            for item in trade_data:
                trade = Trade(
                    symbol=item.get("s", self.symbol),
                    timestamp=datetime.fromtimestamp(item.get("T", 0) / 1000),
                    price=float(item.get("p", 0)),
                    quantity=float(item.get("v", 0)),
                    side=item.get("S", "")
                )

                if self.trade_callback:
                    await self.trade_callback(trade)

        except Exception as e:
            logger.error(f"Error handling trade: {e}")

    async def _handle_kline(self, data: Dict):
        try:
            kline_list = data.get("data", [])
            for kline_data in kline_list:
                kline = OHLCV(
                    symbol=self.symbol,
                    timestamp=datetime.fromtimestamp(kline_data.get("start", 0) / 1000),
                    open=float(kline_data.get("open", 0)),
                    high=float(kline_data.get("high", 0)),
                    low=float(kline_data.get("low", 0)),
                    close=float(kline_data.get("close", 0)),
                    volume=float(kline_data.get("volume", 0)),
                    timeframe=kline_data.get("interval", "")
                )

                if self.kline_callback:
                    await self.kline_callback(kline)

        except Exception as e:
            logger.error(f"Error handling kline: {e}")

    async def _process_message(self, message: str):
        try:
            data = json.loads(message)

            if data.get("op") == "pong":
                return

            topic = data.get("topic", "")

            if "orderbook" in topic:
                msg_type = data.get("type", "")
                if msg_type == "snapshot":
                    await self._handle_orderbook_snapshot(data)
                elif msg_type == "delta":
                    await self._handle_orderbook_delta(data)

            elif "publicTrade" in topic:
                await self._handle_trade(data)

            elif "kline" in topic:
                await self._handle_kline(data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _heartbeat(self):
        while self.is_running and self.ws:
            try:
                await self.ws.send(json.dumps({"op": "ping"}))
                await asyncio.sleep(20)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def start(self, channels: List[str]):
        self.is_running = True

        while self.is_running:
            try:
                connected = await self.connect()
                if not connected:
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                await self.subscribe(channels)

                heartbeat_task = asyncio.create_task(self._heartbeat())

                async for message in self.ws:
                    await self._process_message(message)

            except ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self.reconnect_delay)
            finally:
                if heartbeat_task:
                    heartbeat_task.cancel()

    async def stop(self):
        self.is_running = False
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket connection closed")
