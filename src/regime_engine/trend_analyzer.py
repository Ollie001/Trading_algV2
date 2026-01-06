import logging
from typing import List, Optional
from datetime import datetime
import numpy as np

from src.models import DXYData, BTCDominanceData, TrendData
from src.config import DXY_THRESHOLDS, BTC_DOMINANCE_THRESHOLDS

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends for macro indicators"""

    def __init__(self):
        self.dxy_history: List[DXYData] = []
        self.btc_dom_history: List[BTCDominanceData] = []
        self.max_history = 100

    def add_dxy_data(self, data: DXYData):
        """Add DXY data point"""
        self.dxy_history.append(data)
        if len(self.dxy_history) > self.max_history:
            self.dxy_history.pop(0)

    def add_btc_dominance_data(self, data: BTCDominanceData):
        """Add BTC dominance data point"""
        self.btc_dom_history.append(data)
        if len(self.btc_dom_history) > self.max_history:
            self.btc_dom_history.pop(0)

    def _calculate_slope(self, values: List[float], periods: int) -> float:
        """Calculate linear regression slope"""
        if len(values) < 2:
            return 0.0

        recent = values[-periods:]
        if len(recent) < 2:
            return 0.0

        x = np.arange(len(recent))
        y = np.array(recent)

        # Linear regression
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            # Normalize slope relative to mean value
            mean_val = np.mean(y)
            if mean_val != 0:
                slope = (slope / mean_val) * 100
            return float(slope)

        return 0.0

    def _determine_direction(self, slope: float, threshold: float) -> str:
        """Determine trend direction based on slope"""
        if slope > threshold:
            return "UP"
        elif slope < -threshold:
            return "DOWN"
        else:
            return "FLAT"

    def _determine_strength(self, slope: float, weak_threshold: float,
                           strong_threshold: float) -> str:
        """Determine trend strength"""
        abs_slope = abs(slope)

        if abs_slope >= strong_threshold:
            return "STRONG"
        elif abs_slope >= weak_threshold:
            return "WEAK"
        else:
            return "NONE"

    def analyze_dxy_trend(self, lookback: Optional[int] = None) -> Optional[TrendData]:
        """Analyze DXY trend"""
        if not self.dxy_history:
            return None

        lookback = lookback or DXY_THRESHOLDS["lookback_periods"]

        values = [d.value for d in self.dxy_history]
        slope = self._calculate_slope(values, lookback)

        direction = self._determine_direction(
            slope,
            DXY_THRESHOLDS["weak_trend_slope"]
        )

        strength = self._determine_strength(
            slope,
            DXY_THRESHOLDS["weak_trend_slope"],
            DXY_THRESHOLDS["strong_trend_slope"]
        )

        return TrendData(
            current_value=self.dxy_history[-1].value,
            slope=slope,
            direction=direction,
            strength=strength,
            lookback_periods=min(lookback, len(self.dxy_history)),
            timestamp=datetime.now()
        )

    def analyze_btc_dominance_trend(self, lookback: Optional[int] = None) -> Optional[TrendData]:
        """Analyze BTC dominance trend"""
        if not self.btc_dom_history:
            return None

        lookback = lookback or BTC_DOMINANCE_THRESHOLDS["lookback_periods"]

        values = [d.value for d in self.btc_dom_history]
        slope = self._calculate_slope(values, lookback)

        direction = self._determine_direction(
            slope,
            abs(BTC_DOMINANCE_THRESHOLDS["falling_threshold"])
        )

        strength = self._determine_strength(
            slope,
            abs(BTC_DOMINANCE_THRESHOLDS["falling_threshold"]),
            abs(BTC_DOMINANCE_THRESHOLDS["rising_threshold"])
        )

        return TrendData(
            current_value=self.btc_dom_history[-1].value,
            slope=slope,
            direction=direction,
            strength=strength,
            lookback_periods=min(lookback, len(self.btc_dom_history)),
            timestamp=datetime.now()
        )

    def get_dxy_signal(self) -> str:
        """Get DXY signal for regime classification"""
        trend = self.analyze_dxy_trend()
        if not trend:
            return "NEUTRAL"

        # DXY up = USD strength = RISK_OFF
        # DXY down = USD weakness = RISK_ON
        if trend.direction == "UP" and trend.strength in ["STRONG", "WEAK"]:
            return "RISK_OFF"
        elif trend.direction == "DOWN" and trend.strength in ["STRONG", "WEAK"]:
            return "RISK_ON"
        else:
            return "NEUTRAL"

    def get_btc_dominance_signal(self) -> str:
        """Get BTC dominance signal for regime classification"""
        trend = self.analyze_btc_dominance_trend()
        if not trend:
            return "NEUTRAL"

        # BTC.D rising = BTC outperforming alts = could be flight to safety or BTC strength
        # BTC.D falling = Alts outperforming = RISK_ON for crypto
        if trend.direction == "UP" and trend.strength in ["STRONG", "WEAK"]:
            return "BTC_STRENGTH"
        elif trend.direction == "DOWN" and trend.strength in ["STRONG", "WEAK"]:
            return "ALTCOIN_STRENGTH"
        else:
            return "NEUTRAL"

    def get_trend_summary(self) -> dict:
        """Get summary of all trends"""
        dxy_trend = self.analyze_dxy_trend()
        btc_dom_trend = self.analyze_btc_dominance_trend()

        return {
            "dxy": {
                "value": dxy_trend.current_value if dxy_trend else None,
                "slope": dxy_trend.slope if dxy_trend else None,
                "direction": dxy_trend.direction if dxy_trend else None,
                "strength": dxy_trend.strength if dxy_trend else None,
                "signal": self.get_dxy_signal()
            },
            "btc_dominance": {
                "value": btc_dom_trend.current_value if btc_dom_trend else None,
                "slope": btc_dom_trend.slope if btc_dom_trend else None,
                "direction": btc_dom_trend.direction if btc_dom_trend else None,
                "strength": btc_dom_trend.strength if btc_dom_trend else None,
                "signal": self.get_btc_dominance_signal()
            }
        }
