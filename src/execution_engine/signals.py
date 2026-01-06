"""
Module 7: Execution Engine
Generates entry and exit signals based on structure, orderflow, and liquidity
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from src.models import OHLCV, Trade, OrderBook, RegimeOutput
from src.liquidity_engine import LiquidityLevel
from src.capital_flow import CapitalFlowSignal

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    ENTRY_LONG = "ENTRY_LONG"
    ENTRY_SHORT = "ENTRY_SHORT"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    NO_SIGNAL = "NO_SIGNAL"


@dataclass
class ExecutionSignal:
    """Trade execution signal"""
    signal_type: SignalType
    timestamp: datetime
    price: float
    confidence: float  # 0.0 to 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    supporting_factors: List[str] = None

    def __post_init__(self):
        if self.supporting_factors is None:
            self.supporting_factors = []


class MarketStructure:
    """Tracks market structure (highs, lows, breaks)"""

    def __init__(self):
        self.swing_highs: List[float] = []
        self.swing_lows: List[float] = []
        self.trend: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL

    def update(self, klines: List[OHLCV]):
        """Update market structure from klines"""
        if len(klines) < 3:
            return

        # Simple swing high/low detection
        for i in range(1, len(klines) - 1):
            current = klines[i]
            prev = klines[i - 1]
            next_candle = klines[i + 1]

            # Swing high: higher than both neighbors
            if current.high > prev.high and current.high > next_candle.high:
                self.swing_highs.append(current.high)
                if len(self.swing_highs) > 10:
                    self.swing_highs.pop(0)

            # Swing low: lower than both neighbors
            if current.low < prev.low and current.low < next_candle.low:
                self.swing_lows.append(current.low)
                if len(self.swing_lows) > 10:
                    self.swing_lows.pop(0)

        # Determine trend
        if len(self.swing_highs) >= 2 and len(self.swing_lows) >= 2:
            recent_highs = self.swing_highs[-2:]
            recent_lows = self.swing_lows[-2:]

            # Higher highs and higher lows = bullish
            if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
                self.trend = "BULLISH"
            # Lower highs and lower lows = bearish
            elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
                self.trend = "BEARISH"
            else:
                self.trend = "NEUTRAL"


class ExecutionEngine:
    """
    Generates trade signals based on:
    - Market structure (CHOCH, BOS)
    - Liquidity sweeps and returns
    - Order flow imbalances
    - Regime permissions
    """

    def __init__(self):
        self.structure = MarketStructure()
        self.kline_history: List[OHLCV] = []
        self.trade_history: List[Trade] = []
        self.max_history = 50

        self.last_signal: Optional[ExecutionSignal] = None

    def add_kline(self, kline: OHLCV):
        """Add kline data"""
        self.kline_history.append(kline)
        if len(self.kline_history) > self.max_history:
            self.kline_history.pop(0)

        # Update structure
        self.structure.update(self.kline_history)

    def add_trade(self, trade: Trade):
        """Add trade data for orderflow analysis"""
        self.trade_history.append(trade)
        if len(self.trade_history) > 1000:
            self.trade_history.pop(0)

    def _check_liquidity_sweep(
        self,
        current_price: float,
        liquidity_levels: List[LiquidityLevel]
    ) -> Optional[Dict[str, Any]]:
        """Check if price swept liquidity and returned"""
        if not liquidity_levels or len(self.kline_history) < 3:
            return None

        recent_klines = self.kline_history[-3:]

        for level in liquidity_levels:
            # Check if we swept above a high
            if level.level_type.endswith("_HIGH"):
                # Did we wick above and close below?
                for kline in recent_klines:
                    if kline.high > level.price and kline.close < level.price:
                        return {
                            "type": "SWEEP_HIGH",
                            "level": level,
                            "signal": "SHORT",
                            "reason": f"Swept {level.level_type} at {level.price:.2f} and returned"
                        }

            # Check if we swept below a low
            if level.level_type.endswith("_LOW"):
                # Did we wick below and close above?
                for kline in recent_klines:
                    if kline.low < level.price and kline.close > level.price:
                        return {
                            "type": "SWEEP_LOW",
                            "level": level,
                            "signal": "LONG",
                            "reason": f"Swept {level.level_type} at {level.price:.2f} and returned"
                        }

        return None

    def _check_structure_break(self, current_price: float) -> Optional[Dict[str, Any]]:
        """Check for break of structure or change of character"""
        if not self.structure.swing_highs or not self.structure.swing_lows:
            return None

        # Break of Structure (BOS) - continuation
        if self.structure.trend == "BULLISH":
            if current_price > max(self.structure.swing_highs[-2:]):
                return {
                    "type": "BOS_LONG",
                    "signal": "LONG",
                    "reason": "Break of structure to upside in bullish trend"
                }

        elif self.structure.trend == "BEARISH":
            if current_price < min(self.structure.swing_lows[-2:]):
                return {
                    "type": "BOS_SHORT",
                    "signal": "SHORT",
                    "reason": "Break of structure to downside in bearish trend"
                }

        # Change of Character (CHOCH) - potential reversal
        if self.structure.trend == "BEARISH":
            if current_price > max(self.structure.swing_highs[-2:]):
                return {
                    "type": "CHOCH_LONG",
                    "signal": "LONG",
                    "reason": "Change of character - bearish structure broken to upside"
                }

        elif self.structure.trend == "BULLISH":
            if current_price < min(self.structure.swing_lows[-2:]):
                return {
                    "type": "CHOCH_SHORT",
                    "signal": "SHORT",
                    "reason": "Change of character - bullish structure broken to downside"
                }

        return None

    def _analyze_orderflow(self) -> Dict[str, Any]:
        """Analyze recent orderflow for imbalances"""
        if len(self.trade_history) < 20:
            return {"imbalance": "NEUTRAL", "ratio": 1.0}

        recent_trades = self.trade_history[-20:]

        buy_volume = sum(t.quantity for t in recent_trades if t.side == "Buy")
        sell_volume = sum(t.quantity for t in recent_trades if t.side == "Sell")

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return {"imbalance": "NEUTRAL", "ratio": 1.0}

        ratio = buy_volume / sell_volume if sell_volume > 0 else 999

        # Strong imbalance threshold
        if ratio > 2.0:
            return {"imbalance": "BULLISH", "ratio": ratio}
        elif ratio < 0.5:
            return {"imbalance": "BEARISH", "ratio": ratio}
        else:
            return {"imbalance": "NEUTRAL", "ratio": ratio}

    def generate_signal(
        self,
        current_price: float,
        regime: Optional[RegimeOutput],
        liquidity_levels: List[LiquidityLevel],
        capital_flow: Optional[CapitalFlowSignal]
    ) -> ExecutionSignal:
        """
        Generate execution signal based on all inputs.

        Trades are allowed ONLY if:
        1. Regime permits trading
        2. Capital flow bias supports trade type
        3. Liquidity target exists
        4. LTF structure confirms
        """

        # Default: no signal
        signal = ExecutionSignal(
            signal_type=SignalType.NO_SIGNAL,
            timestamp=datetime.now(),
            price=current_price,
            confidence=0.0,
            reason="Conditions not met"
        )

        # Check 1: Regime must permit trading
        if not regime or not regime.permissions.get("trading_enabled", False):
            signal.reason = f"Trading disabled by regime: {regime.state if regime else 'Unknown'}"
            return signal

        # Get preferred trade directions
        preferred_trades = regime.permissions.get("preferred_trades", [])

        # Check 2: Analyze structure
        structure_signal = self._check_structure_break(current_price)

        # Check 3: Check liquidity sweeps
        sweep_signal = self._check_liquidity_sweep(current_price, liquidity_levels)

        # Check 4: Analyze orderflow
        orderflow = self._analyze_orderflow()

        # Build signal
        supporting_factors = []
        confidence = 0.0

        # Determine signal direction
        potential_signal = None

        # Liquidity sweep has highest priority
        if sweep_signal:
            potential_signal = sweep_signal["signal"]
            supporting_factors.append(sweep_signal["reason"])
            confidence += 0.4

        # Structure confirmation
        elif structure_signal:
            potential_signal = structure_signal["signal"]
            supporting_factors.append(structure_signal["reason"])
            confidence += 0.3

        # Check if signal aligns with regime
        if potential_signal:
            if potential_signal == "LONG" and "LONG" in preferred_trades:
                confidence += 0.3
                supporting_factors.append(f"Aligned with {regime.state} regime")
            elif potential_signal == "SHORT" and "SHORT" in preferred_trades:
                confidence += 0.3
                supporting_factors.append(f"Aligned with {regime.state} regime")
            else:
                # Signal against regime preference
                confidence *= 0.5
                supporting_factors.append(f"Against {regime.state} regime preference")

        # Orderflow confirmation
        if orderflow["imbalance"] == "BULLISH" and potential_signal == "LONG":
            confidence += 0.2
            supporting_factors.append(f"Bullish orderflow (ratio: {orderflow['ratio']:.2f})")
        elif orderflow["imbalance"] == "BEARISH" and potential_signal == "SHORT":
            confidence += 0.2
            supporting_factors.append(f"Bearish orderflow (ratio: {orderflow['ratio']:.2f})")

        # Capital flow alignment
        if capital_flow:
            if capital_flow.bias == "CONTINUATION":
                if (capital_flow.flow_direction == "BTC_INFLOW" and potential_signal == "LONG") or \
                   (capital_flow.flow_direction == "BTC_OUTFLOW" and potential_signal == "SHORT"):
                    confidence += 0.1
                    supporting_factors.append(f"Capital flow supports {potential_signal}")

        # Need minimum confidence to generate signal
        if confidence < 0.5 or not potential_signal:
            signal.reason = "Insufficient confidence or no clear setup"
            return signal

        # Generate final signal
        if potential_signal == "LONG":
            signal.signal_type = SignalType.ENTRY_LONG
            # Set stop below nearest liquidity
            if liquidity_levels:
                below_levels = [l.price for l in liquidity_levels if l.price < current_price]
                if below_levels:
                    signal.stop_loss = min(below_levels) - (current_price * 0.001)  # 0.1% below

            # Set target at nearest liquidity above
            if liquidity_levels:
                above_levels = [l.price for l in liquidity_levels if l.price > current_price]
                if above_levels:
                    signal.take_profit = min(above_levels)

        elif potential_signal == "SHORT":
            signal.signal_type = SignalType.ENTRY_SHORT
            # Set stop above nearest liquidity
            if liquidity_levels:
                above_levels = [l.price for l in liquidity_levels if l.price > current_price]
                if above_levels:
                    signal.stop_loss = max(above_levels) + (current_price * 0.001)

            # Set target at nearest liquidity below
            if liquidity_levels:
                below_levels = [l.price for l in liquidity_levels if l.price < current_price]
                if below_levels:
                    signal.take_profit = max(below_levels)

        signal.confidence = min(confidence, 1.0)
        signal.supporting_factors = supporting_factors
        signal.reason = " | ".join(supporting_factors[:3])

        self.last_signal = signal

        logger.info(
            f"Signal Generated: {signal.signal_type.value} @ {signal.price:.2f} | "
            f"Confidence: {signal.confidence:.2f} | {signal.reason}"
        )

        return signal

    def get_status(self) -> Dict[str, Any]:
        """Get execution engine status"""
        orderflow = self._analyze_orderflow()

        return {
            "klines_loaded": len(self.kline_history),
            "trades_tracked": len(self.trade_history),
            "market_structure": {
                "trend": self.structure.trend,
                "swing_highs": len(self.structure.swing_highs),
                "swing_lows": len(self.structure.swing_lows)
            },
            "orderflow": orderflow,
            "last_signal": {
                "type": self.last_signal.signal_type.value,
                "price": self.last_signal.price,
                "confidence": self.last_signal.confidence,
                "reason": self.last_signal.reason
            } if self.last_signal else None
        }
