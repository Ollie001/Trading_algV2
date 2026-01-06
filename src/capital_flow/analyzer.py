"""
Module 5: Capital Flow Analyzer
Analyzes BTC dominance trends to detect capital rotation between BTC and altcoins
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np

from src.models import BTCDominanceData

logger = logging.getLogger(__name__)


@dataclass
class CapitalFlowSignal:
    """Capital flow signal output"""
    timestamp: datetime
    flow_direction: str  # BTC_INFLOW, BTC_OUTFLOW, NEUTRAL
    flow_strength: float  # 0.0 to 1.0
    momentum: float  # Rate of change
    bias: str  # CONTINUATION, MEAN_REVERSION, NEUTRAL
    confidence: float  # 0.0 to 1.0
    supporting_factors: List[str]


class CapitalFlowAnalyzer:
    """
    Analyzes BTC dominance to determine capital flow patterns.

    Key Insights:
    - Rising BTC.D = Capital flowing from alts to BTC (flight to quality or BTC rally)
    - Falling BTC.D = Capital flowing from BTC to alts (risk-on in crypto)
    - Momentum matters: Fast changes suggest stronger conviction
    """

    def __init__(self, lookback_periods: int = 24):
        self.lookback_periods = lookback_periods
        self.dominance_history: List[BTCDominanceData] = []
        self.max_history = 200

        # Thresholds
        self.strong_flow_threshold = 0.5  # % change in dominance
        self.weak_flow_threshold = 0.2
        self.momentum_threshold = 0.1  # Rate of change threshold

    def add_data(self, data: BTCDominanceData):
        """Add new BTC dominance data point"""
        self.dominance_history.append(data)
        if len(self.dominance_history) > self.max_history:
            self.dominance_history.pop(0)

    def _calculate_momentum(self, values: List[float], periods: int = 5) -> float:
        """Calculate momentum (rate of change)"""
        if len(values) < periods:
            return 0.0

        recent = values[-periods:]
        if len(recent) < 2:
            return 0.0

        # Simple momentum: (current - previous) / previous
        momentum = (recent[-1] - recent[0]) / recent[0] * 100
        return float(momentum)

    def _detect_divergence(self, values: List[float]) -> bool:
        """Detect if dominance is diverging from its trend"""
        if len(values) < self.lookback_periods:
            return False

        recent = values[-self.lookback_periods:]

        # Calculate linear trend
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]

        # Check if recent price action diverges from trend
        recent_slope = (recent[-1] - recent[-5]) / 5 if len(recent) >= 5 else 0

        # Divergence: trend and recent action in opposite directions
        return (slope > 0 and recent_slope < 0) or (slope < 0 and recent_slope > 0)

    def _calculate_flow_strength(self, change_pct: float, momentum: float) -> float:
        """Calculate overall flow strength"""
        # Combine absolute change and momentum
        change_strength = min(abs(change_pct) / self.strong_flow_threshold, 1.0)
        momentum_strength = min(abs(momentum) / self.momentum_threshold, 1.0)

        # Weighted average
        strength = (change_strength * 0.6) + (momentum_strength * 0.4)
        return min(strength, 1.0)

    def _determine_bias(
        self,
        flow_direction: str,
        momentum: float,
        has_divergence: bool
    ) -> str:
        """Determine if we should trade continuation or mean reversion"""

        # Strong momentum = continuation
        if abs(momentum) > self.momentum_threshold * 2:
            return "CONTINUATION"

        # Divergence = potential mean reversion
        if has_divergence:
            return "MEAN_REVERSION"

        # Weak momentum = neutral
        if abs(momentum) < self.weak_flow_threshold:
            return "NEUTRAL"

        # Default to continuation for moderate momentum
        return "CONTINUATION"

    def analyze(self) -> Optional[CapitalFlowSignal]:
        """Analyze capital flow based on BTC dominance"""
        if len(self.dominance_history) < 2:
            logger.debug("Insufficient data for capital flow analysis")
            return None

        values = [d.value for d in self.dominance_history]
        current = values[-1]

        # Get change over lookback period
        lookback_idx = max(0, len(values) - self.lookback_periods)
        previous = values[lookback_idx]
        change_pct = ((current - previous) / previous) * 100

        # Calculate momentum
        momentum = self._calculate_momentum(values)

        # Detect divergence
        has_divergence = self._detect_divergence(values)

        # Determine flow direction
        if change_pct > self.weak_flow_threshold:
            flow_direction = "BTC_INFLOW"
        elif change_pct < -self.weak_flow_threshold:
            flow_direction = "BTC_OUTFLOW"
        else:
            flow_direction = "NEUTRAL"

        # Calculate flow strength
        flow_strength = self._calculate_flow_strength(change_pct, momentum)

        # Determine bias
        bias = self._determine_bias(flow_direction, momentum, has_divergence)

        # Build supporting factors
        supporting_factors = []

        if abs(change_pct) > self.strong_flow_threshold:
            supporting_factors.append(f"Strong dominance change: {change_pct:.2f}%")

        if abs(momentum) > self.momentum_threshold:
            direction = "accelerating" if momentum > 0 else "decelerating"
            supporting_factors.append(f"Momentum {direction}: {momentum:.2f}%")

        if has_divergence:
            supporting_factors.append("Divergence detected - potential reversal")

        # Calculate confidence
        confidence = flow_strength
        if has_divergence:
            confidence *= 0.8  # Reduce confidence during divergence

        signal = CapitalFlowSignal(
            timestamp=datetime.now(),
            flow_direction=flow_direction,
            flow_strength=flow_strength,
            momentum=momentum,
            bias=bias,
            confidence=confidence,
            supporting_factors=supporting_factors
        )

        logger.info(
            f"Capital Flow: {signal.flow_direction} | "
            f"Strength: {signal.flow_strength:.2f} | "
            f"Bias: {signal.bias} | "
            f"Momentum: {signal.momentum:.2f}%"
        )

        return signal

    def get_flow_interpretation(self, signal: CapitalFlowSignal) -> Dict[str, Any]:
        """Get human-readable interpretation of capital flow"""
        interpretations = {
            "BTC_INFLOW": {
                "CONTINUATION": "Capital flowing into BTC. Consider BTC longs, avoid alt longs.",
                "MEAN_REVERSION": "BTC dominance rising but may reverse. Cautious on BTC longs.",
                "NEUTRAL": "Slow capital flow to BTC. Monitor for acceleration."
            },
            "BTC_OUTFLOW": {
                "CONTINUATION": "Capital flowing to alts. BTC may underperform, alts bullish.",
                "MEAN_REVERSION": "BTC dominance falling but may reverse. Cautious on alt longs.",
                "NEUTRAL": "Slow capital flow to alts. Monitor for acceleration."
            },
            "NEUTRAL": {
                "CONTINUATION": "Balanced flow. No strong directional bias.",
                "MEAN_REVERSION": "Balanced flow with potential reversal setup.",
                "NEUTRAL": "Sideways market. Low conviction trades only."
            }
        }

        interpretation = interpretations.get(
            signal.flow_direction, {}
        ).get(signal.bias, "No clear interpretation")

        return {
            "flow_direction": signal.flow_direction,
            "bias": signal.bias,
            "strength": signal.flow_strength,
            "confidence": signal.confidence,
            "interpretation": interpretation,
            "supporting_factors": signal.supporting_factors,
            "btc_trade_preference": self._get_btc_trade_preference(signal),
            "alt_implication": self._get_alt_implication(signal)
        }

    def _get_btc_trade_preference(self, signal: CapitalFlowSignal) -> str:
        """Get BTC trading preference based on flow"""
        if signal.flow_direction == "BTC_INFLOW":
            if signal.bias == "CONTINUATION":
                return "FAVOR_LONGS"
            elif signal.bias == "MEAN_REVERSION":
                return "CAUTIOUS_SHORTS"
            else:
                return "NEUTRAL"
        elif signal.flow_direction == "BTC_OUTFLOW":
            if signal.bias == "CONTINUATION":
                return "FAVOR_SHORTS"
            elif signal.bias == "MEAN_REVERSION":
                return "CAUTIOUS_LONGS"
            else:
                return "NEUTRAL"
        else:
            return "NEUTRAL"

    def _get_alt_implication(self, signal: CapitalFlowSignal) -> str:
        """Get altcoin market implication"""
        if signal.flow_direction == "BTC_OUTFLOW":
            return "BULLISH_FOR_ALTS"
        elif signal.flow_direction == "BTC_INFLOW":
            return "BEARISH_FOR_ALTS"
        else:
            return "NEUTRAL"

    def get_status(self) -> Dict[str, Any]:
        """Get current analyzer status"""
        signal = self.analyze()

        if not signal:
            return {"error": "Insufficient data"}

        interpretation = self.get_flow_interpretation(signal)

        return {
            "data_points": len(self.dominance_history),
            "current_dominance": self.dominance_history[-1].value if self.dominance_history else None,
            "signal": {
                "flow_direction": signal.flow_direction,
                "flow_strength": signal.flow_strength,
                "momentum": signal.momentum,
                "bias": signal.bias,
                "confidence": signal.confidence,
                "supporting_factors": signal.supporting_factors
            },
            "interpretation": interpretation
        }
