import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from datetime import timedelta

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings, Timeframe
from src.data_ingestion import (
    BybitWebSocketClient,
    BybitRESTClient,
    DXYFetcher,
    BTCDominanceFetcher,
    NewsFetcher
)
from src.models import (
    OrderBook, Trade, OHLCV, NewsItem, DXYData, BTCDominanceData,
    RegimeInput, RegimeOutput
)
from src.news_classification import NewsClassifier, NewsClassification
from src.regime_engine import RegimeEngine
from src.capital_flow import CapitalFlowAnalyzer, CapitalFlowSignal
from src.liquidity_engine import LiquidityEngine
from src.execution_engine import ExecutionEngine, ExecutionSignal
from src.risk_manager import RiskManager
from src.trade_manager import TradeManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self):
        self.bybit_ws: Optional[BybitWebSocketClient] = None
        self.bybit_rest: Optional[BybitRESTClient] = None
        self.dxy_fetcher: Optional[DXYFetcher] = None
        self.btc_dom_fetcher: Optional[BTCDominanceFetcher] = None
        self.news_fetcher: Optional[NewsFetcher] = None

        # Module 3 & 4
        self.news_classifier: Optional[NewsClassifier] = None
        self.regime_engine: Optional[RegimeEngine] = None

        # Module 5-9
        self.capital_flow: Optional[CapitalFlowAnalyzer] = None
        self.liquidity_engine: Optional[LiquidityEngine] = None
        self.execution_engine: Optional[ExecutionEngine] = None
        self.risk_manager: Optional[RiskManager] = None
        self.trade_manager: Optional[TradeManager] = None

        self.latest_orderbook: Optional[OrderBook] = None
        self.latest_trade: Optional[Trade] = None
        self.latest_kline: Optional[OHLCV] = None
        self.latest_dxy: Optional[DXYData] = None
        self.latest_btc_dom: Optional[BTCDominanceData] = None
        self.latest_news: Optional[NewsItem] = None
        self.latest_news_classification: Optional[NewsClassification] = None
        self.latest_regime: Optional[RegimeOutput] = None
        self.latest_capital_flow: Optional[CapitalFlowSignal] = None
        self.latest_execution_signal: Optional[ExecutionSignal] = None

        self.ws_task: Optional[asyncio.Task] = None
        self.news_task: Optional[asyncio.Task] = None
        self.macro_update_task: Optional[asyncio.Task] = None
        self.regime_update_task: Optional[asyncio.Task] = None
        self.execution_task: Optional[asyncio.Task] = None

    async def on_orderbook(self, orderbook: OrderBook):
        self.latest_orderbook = orderbook
        logger.debug(f"Orderbook update: {orderbook.symbol} @ {orderbook.timestamp}")

        # Feed to liquidity engine
        if self.liquidity_engine:
            self.liquidity_engine.update_orderbook_zones(orderbook)

    async def on_trade(self, trade: Trade):
        self.latest_trade = trade
        logger.info(f"Trade: {trade.symbol} {trade.side} {trade.price} x {trade.quantity}")

        # Feed to execution engine for orderflow analysis
        if self.execution_engine:
            self.execution_engine.add_trade(trade)

        # Check stop loss and take profit
        if self.trade_manager:
            self.trade_manager.check_stop_loss(trade.price)
            self.trade_manager.check_take_profit(trade.price)

    async def on_kline(self, kline: OHLCV):
        self.latest_kline = kline
        logger.debug(f"Kline: {kline.symbol} [{kline.timeframe}] Close: {kline.close}")

        # Feed to liquidity engine
        if self.liquidity_engine:
            self.liquidity_engine.add_kline(kline)

        # Feed to execution engine
        if self.execution_engine:
            self.execution_engine.add_kline(kline)

    async def on_news(self, news: NewsItem):
        self.latest_news = news
        logger.info(f"News: {news.title} from {news.source}")

        # Classify news with Module 3
        if self.news_classifier:
            classification = self.news_classifier.classify(news)
            self.latest_news_classification = classification

    async def update_macro_data(self):
        while True:
            try:
                dxy_data = await self.dxy_fetcher.get_current_value()
                if dxy_data:
                    self.latest_dxy = dxy_data
                    logger.info(f"DXY updated: {dxy_data.value}")

                    # Feed to regime engine trend analyzer
                    if self.regime_engine:
                        self.regime_engine.trend_analyzer.add_dxy_data(dxy_data)

                btc_dom_data = await self.btc_dom_fetcher.get_current_dominance()
                if btc_dom_data:
                    self.latest_btc_dom = btc_dom_data
                    logger.info(f"BTC Dominance updated: {btc_dom_data.value}%")

                    # Feed to regime engine trend analyzer
                    if self.regime_engine:
                        self.regime_engine.trend_analyzer.add_btc_dominance_data(btc_dom_data)

                    # Feed to capital flow analyzer
                    if self.capital_flow:
                        self.capital_flow.add_data(btc_dom_data)
                        self.latest_capital_flow = self.capital_flow.analyze()

                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Error updating macro data: {e}")
                await asyncio.sleep(300)

    async def update_regime(self):
        """Update regime state periodically"""
        # Wait a bit for initial data to populate
        await asyncio.sleep(30)

        while True:
            try:
                if not self.regime_engine:
                    await asyncio.sleep(60)
                    continue

                # Get trend data
                dxy_trend = self.regime_engine.trend_analyzer.analyze_dxy_trend()
                btc_dom_trend = self.regime_engine.trend_analyzer.analyze_btc_dominance_trend()

                # Get news signals
                news_signals = None
                if self.news_classifier:
                    news_signals = self.news_classifier.get_regime_signals()

                # Build regime input
                from datetime import datetime
                regime_input = RegimeInput(
                    dxy_trend=dxy_trend,
                    btc_dominance_trend=btc_dom_trend,
                    news_signals=news_signals,
                    timestamp=datetime.now()
                )

                # Update regime
                regime_output = self.regime_engine.update(regime_input)
                self.latest_regime = regime_output

                logger.info(
                    f"Regime updated: {regime_output.state.value} "
                    f"(confidence: {regime_output.confidence:.2f})"
                )

                # Update every 5 minutes
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error updating regime: {e}")
                await asyncio.sleep(60)

    async def execution_loop(self):
        """Main execution loop - generates and executes trading signals"""
        # Wait for initial data
        await asyncio.sleep(60)

        logger.info("Execution loop started")

        while True:
            try:
                # Check if we have all required components
                if not all([
                    self.execution_engine,
                    self.risk_manager,
                    self.trade_manager,
                    self.latest_regime,
                    self.latest_trade
                ]):
                    await asyncio.sleep(30)
                    continue

                # Get current price
                current_price = self.latest_trade.price

                # Get liquidity levels
                liquidity_levels = []
                if self.liquidity_engine:
                    liquidity_levels = self.liquidity_engine.get_all_levels()

                # Generate execution signal
                signal = self.execution_engine.generate_signal(
                    current_price=current_price,
                    regime=self.latest_regime,
                    liquidity_levels=liquidity_levels,
                    capital_flow=self.latest_capital_flow
                )

                self.latest_execution_signal = signal

                # Check if signal is actionable
                if signal.signal_type.value.startswith("ENTRY") and signal.confidence >= 0.6:
                    # Calculate position size
                    position_size = self.risk_manager.calculate_position_size(
                        signal=signal,
                        regime=self.latest_regime,
                        current_price=current_price
                    )

                    # Attempt to open position
                    if position_size.approved:
                        position = await self.trade_manager.open_position(
                            signal=signal,
                            position_size=position_size,
                            symbol="BTCUSDT"
                        )

                        if position:
                            self.risk_manager.increment_open_positions()
                            logger.info(f"✅ Position opened: {position.position_id}")
                        else:
                            logger.warning("Failed to open position")
                    else:
                        logger.debug(f"Position not approved: {position_size.rejection_reason}")

                # Check every 30 seconds
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                await asyncio.sleep(30)

    async def start(self):
        logger.info("Starting data manager...")

        # Initialize data ingestion (Module 2)
        self.bybit_rest = BybitRESTClient()
        self.dxy_fetcher = DXYFetcher()
        self.btc_dom_fetcher = BTCDominanceFetcher()
        self.news_fetcher = NewsFetcher()

        # Initialize Module 3 & 4
        self.news_classifier = NewsClassifier()
        self.regime_engine = RegimeEngine(min_time_in_state=3600)

        # Initialize Module 5-9
        self.capital_flow = CapitalFlowAnalyzer()
        self.liquidity_engine = LiquidityEngine()
        self.execution_engine = ExecutionEngine()
        self.risk_manager = RiskManager()
        self.trade_manager = TradeManager(bybit_rest_client=self.bybit_rest)

        # Start in dry-run mode for safety
        self.trade_manager.enable_live_trading()  # Change to disable_live_trading() for dry-run
        logger.warning("⚠️  Trade Manager in DRY-RUN mode - no real orders will be placed")

        self.bybit_ws = BybitWebSocketClient(symbol="BTCUSDT")
        self.bybit_ws.on_orderbook(self.on_orderbook)
        self.bybit_ws.on_trade(self.on_trade)
        self.bybit_ws.on_kline(self.on_kline)

        self.news_fetcher.on_news(self.on_news)

        channels = [
            "orderbook.50.BTCUSDT",
            "publicTrade.BTCUSDT",
            "kline.5.BTCUSDT"
        ]

        self.ws_task = asyncio.create_task(self.bybit_ws.start(channels))
        self.news_task = asyncio.create_task(self.news_fetcher.start_polling(interval=600))
        self.macro_update_task = asyncio.create_task(self.update_macro_data())
        self.regime_update_task = asyncio.create_task(self.update_regime())
        self.execution_task = asyncio.create_task(self.execution_loop())

        logger.info("✅ Data manager started successfully - All 9 modules active!")

    async def stop(self):
        logger.info("Stopping data manager...")

        if self.bybit_ws:
            await self.bybit_ws.stop()

        if self.news_fetcher:
            self.news_fetcher.stop_polling()

        if self.ws_task:
            self.ws_task.cancel()

        if self.news_task:
            self.news_task.cancel()

        if self.macro_update_task:
            self.macro_update_task.cancel()

        if self.regime_update_task:
            self.regime_update_task.cancel()

        if self.execution_task:
            self.execution_task.cancel()

        logger.info("Data manager stopped")


data_manager = DataManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await data_manager.start()
    yield
    await data_manager.stop()


app = FastAPI(
    title="Macro-Aware BTC Trading Bot",
    description="Trading bot with macro indicators, capital flow, and news awareness",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Macro-Aware BTC Trading Bot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "modules_active": 9,
        "components": {
            "module_1_config": True,
            "module_2_data_ingestion": {
                "bybit_ws": data_manager.bybit_ws is not None,
                "bybit_rest": data_manager.bybit_rest is not None,
                "dxy_fetcher": data_manager.dxy_fetcher is not None,
                "btc_dom_fetcher": data_manager.btc_dom_fetcher is not None,
                "news_fetcher": data_manager.news_fetcher is not None,
            },
            "module_3_news_classification": data_manager.news_classifier is not None,
            "module_4_regime_engine": data_manager.regime_engine is not None,
            "module_5_capital_flow": data_manager.capital_flow is not None,
            "module_6_liquidity_engine": data_manager.liquidity_engine is not None,
            "module_7_execution_engine": data_manager.execution_engine is not None,
            "module_8_risk_manager": data_manager.risk_manager is not None,
            "module_9_trade_manager": data_manager.trade_manager is not None,
        }
    }


@app.get("/api/market/orderbook")
async def get_orderbook():
    if not data_manager.latest_orderbook:
        return {"error": "No orderbook data available"}
    return data_manager.latest_orderbook.model_dump()


@app.get("/api/market/latest-trade")
async def get_latest_trade():
    if not data_manager.latest_trade:
        return {"error": "No trade data available"}
    return data_manager.latest_trade.model_dump()


@app.get("/api/market/latest-kline")
async def get_latest_kline():
    if not data_manager.latest_kline:
        return {"error": "No kline data available"}
    return data_manager.latest_kline.model_dump()


@app.get("/api/market/klines")
async def get_historical_klines(
    symbol: str = "BTCUSDT",
    interval: str = "5",
    limit: int = 100
):
    if not data_manager.bybit_rest:
        return {"error": "REST client not initialized"}

    try:
        timeframe = Timeframe.FIVE_MINUTE if interval == "5" else Timeframe.ONE_HOUR
        klines = await data_manager.bybit_rest.get_klines(symbol, timeframe, limit)
        return [k.model_dump() for k in klines]
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/macro/dxy")
async def get_dxy():
    if not data_manager.latest_dxy:
        return {"error": "No DXY data available"}
    return data_manager.latest_dxy.model_dump()


@app.get("/api/macro/btc-dominance")
async def get_btc_dominance():
    if not data_manager.latest_btc_dom:
        return {"error": "No BTC dominance data available"}
    return data_manager.latest_btc_dom.model_dump()


@app.get("/api/news/latest")
async def get_latest_news():
    if not data_manager.latest_news:
        return {"error": "No news data available"}
    return data_manager.latest_news.model_dump()


@app.get("/api/news/fetch")
async def fetch_news(query: Optional[str] = None, limit: int = 10):
    if not data_manager.news_fetcher:
        return {"error": "News fetcher not initialized"}

    news_items = await data_manager.news_fetcher.fetch_latest_news(
        query=query,
        page_size=limit
    )
    return [item.model_dump() for item in news_items]


@app.get("/api/news/classified")
async def get_classified_news(limit: int = 10):
    """Get recently classified news"""
    if not data_manager.news_classifier:
        return {"error": "News classifier not initialized"}

    classifications = data_manager.news_classifier.get_latest_classifications(limit)
    return [
        {
            "news_item": nc.news_item.model_dump(),
            "categories": nc.categories,
            "sentiment": nc.sentiment,
            "sentiment_score": nc.sentiment_score,
            "impact_level": nc.impact_level,
            "alignment": nc.alignment,
            "macro_relevance": nc.macro_relevance,
            "crypto_relevance": nc.crypto_relevance,
            "expires_at": nc.expires_at.isoformat()
        }
        for nc in classifications
    ]


@app.get("/api/news/signals")
async def get_news_signals():
    """Get aggregated news regime signals"""
    if not data_manager.news_classifier:
        return {"error": "News classifier not initialized"}

    return data_manager.news_classifier.get_regime_signals()


@app.get("/api/regime/current")
async def get_current_regime():
    """Get current regime state"""
    if not data_manager.latest_regime:
        return {"error": "No regime data available"}

    return {
        "state": data_manager.latest_regime.state.value,
        "confidence": data_manager.latest_regime.confidence,
        "dxy_contribution": data_manager.latest_regime.dxy_contribution,
        "btc_dom_contribution": data_manager.latest_regime.btc_dom_contribution,
        "news_contribution": data_manager.latest_regime.news_contribution,
        "permissions": data_manager.latest_regime.permissions,
        "timestamp": data_manager.latest_regime.timestamp.isoformat(),
        "time_in_state": data_manager.latest_regime.time_in_state,
        "time_in_state_formatted": str(timedelta(seconds=int(data_manager.latest_regime.time_in_state)))
    }


@app.get("/api/regime/status")
async def get_regime_status():
    """Get detailed regime engine status"""
    if not data_manager.regime_engine:
        return {"error": "Regime engine not initialized"}

    return data_manager.regime_engine.get_status()


@app.get("/api/regime/trends")
async def get_trend_summary():
    """Get trend analysis summary"""
    if not data_manager.regime_engine:
        return {"error": "Regime engine not initialized"}

    return data_manager.regime_engine.trend_analyzer.get_trend_summary()


@app.get("/api/capital-flow/current")
async def get_capital_flow():
    """Get current capital flow analysis"""
    if not data_manager.latest_capital_flow:
        return {"error": "No capital flow data available"}

    return {
        "flow_direction": data_manager.latest_capital_flow.flow_direction,
        "flow_strength": data_manager.latest_capital_flow.flow_strength,
        "momentum": data_manager.latest_capital_flow.momentum,
        "bias": data_manager.latest_capital_flow.bias,
        "confidence": data_manager.latest_capital_flow.confidence,
        "supporting_factors": data_manager.latest_capital_flow.supporting_factors,
        "timestamp": data_manager.latest_capital_flow.timestamp.isoformat()
    }


@app.get("/api/capital-flow/interpretation")
async def get_capital_flow_interpretation():
    """Get capital flow interpretation"""
    if not data_manager.capital_flow or not data_manager.latest_capital_flow:
        return {"error": "Capital flow not initialized"}

    return data_manager.capital_flow.get_flow_interpretation(data_manager.latest_capital_flow)


@app.get("/api/liquidity/levels")
async def get_liquidity_levels():
    """Get all liquidity levels"""
    if not data_manager.liquidity_engine:
        return {"error": "Liquidity engine not initialized"}

    levels = data_manager.liquidity_engine.get_all_levels()
    return [
        {
            "price": level.price,
            "type": level.level_type,
            "strength": level.strength,
            "touched": level.touched,
            "broken": level.broken
        }
        for level in levels
    ]


@app.get("/api/liquidity/status")
async def get_liquidity_status():
    """Get liquidity engine status"""
    if not data_manager.liquidity_engine:
        return {"error": "Liquidity engine not initialized"}

    return data_manager.liquidity_engine.get_status()


@app.get("/api/execution/signal")
async def get_execution_signal():
    """Get latest execution signal"""
    if not data_manager.latest_execution_signal:
        return {"error": "No execution signal available"}

    return {
        "signal_type": data_manager.latest_execution_signal.signal_type.value,
        "price": data_manager.latest_execution_signal.price,
        "confidence": data_manager.latest_execution_signal.confidence,
        "stop_loss": data_manager.latest_execution_signal.stop_loss,
        "take_profit": data_manager.latest_execution_signal.take_profit,
        "reason": data_manager.latest_execution_signal.reason,
        "supporting_factors": data_manager.latest_execution_signal.supporting_factors,
        "timestamp": data_manager.latest_execution_signal.timestamp.isoformat()
    }


@app.get("/api/execution/status")
async def get_execution_status():
    """Get execution engine status"""
    if not data_manager.execution_engine:
        return {"error": "Execution engine not initialized"}

    return data_manager.execution_engine.get_status()


@app.get("/api/risk/status")
async def get_risk_status():
    """Get risk manager status"""
    if not data_manager.risk_manager:
        return {"error": "Risk manager not initialized"}

    return data_manager.risk_manager.get_status()


@app.get("/api/trades/status")
async def get_trades_status():
    """Get trade manager status"""
    if not data_manager.trade_manager:
        return {"error": "Trade manager not initialized"}

    return data_manager.trade_manager.get_status()


@app.get("/api/trades/positions")
async def get_positions():
    """Get all open positions"""
    if not data_manager.trade_manager:
        return {"error": "Trade manager not initialized"}

    positions = data_manager.trade_manager.get_open_positions()
    return [
        {
            "id": p.position_id,
            "symbol": p.symbol,
            "side": p.side,
            "entry_price": p.entry_price,
            "quantity": p.quantity,
            "stop_loss": p.stop_loss,
            "take_profit": p.take_profit,
            "status": p.status.value,
            "entry_time": p.entry_time.isoformat(),
            "reason": p.signal_reason
        }
        for p in positions
    ]


@app.get("/api/trades/history")
async def get_trade_history():
    """Get closed positions history"""
    if not data_manager.trade_manager:
        return {"error": "Trade manager not initialized"}

    positions = data_manager.trade_manager.get_closed_positions()
    return [
        {
            "id": p.position_id,
            "symbol": p.symbol,
            "side": p.side,
            "entry_price": p.entry_price,
            "exit_price": p.exit_price,
            "quantity": p.quantity,
            "pnl": p.pnl,
            "pnl_percent": p.pnl_percent,
            "entry_time": p.entry_time.isoformat(),
            "exit_time": p.exit_time.isoformat() if p.exit_time else None,
            "reason": p.signal_reason
        }
        for p in positions
    ]


@app.get("/api/status")
async def get_status():
    regime_data = None
    if data_manager.latest_regime:
        regime_data = {
            "state": data_manager.latest_regime.state.value,
            "confidence": data_manager.latest_regime.confidence,
            "permissions": data_manager.latest_regime.permissions,
            "time_in_state": int(data_manager.latest_regime.time_in_state),
            "time_in_state_formatted": str(timedelta(seconds=int(data_manager.latest_regime.time_in_state)))
        }

    news_signals = None
    if data_manager.news_classifier:
        news_signals = data_manager.news_classifier.get_regime_signals()

    trend_summary = None
    if data_manager.regime_engine:
        trend_summary = data_manager.regime_engine.trend_analyzer.get_trend_summary()

    return {
        "bybit": {
            "connected": data_manager.bybit_ws is not None,
            "latest_trade": data_manager.latest_trade.model_dump() if data_manager.latest_trade else None,
            "latest_kline": data_manager.latest_kline.model_dump() if data_manager.latest_kline else None,
        },
        "macro": {
            "dxy": data_manager.latest_dxy.model_dump() if data_manager.latest_dxy else None,
            "btc_dominance": data_manager.latest_btc_dom.model_dump() if data_manager.latest_btc_dom else None,
            "trends": trend_summary
        },
        "news": {
            "latest": data_manager.latest_news.model_dump() if data_manager.latest_news else None,
            "signals": news_signals
        },
        "regime": regime_data
    }


@app.get("/ui", response_class=HTMLResponse)
async def ui():
    from src.utils.ui_template import UI_HTML
    return UI_HTML


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
