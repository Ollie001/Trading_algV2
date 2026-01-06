"""
Module 6: Liquidity Engine
Tracks session levels, prior day levels, and order book liquidity zones
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, time, timedelta
from dataclasses import dataclass
import numpy as np

from src.models import OHLCV, OrderBook
from src.config import LIQUIDITY_LEVELS

logger = logging.getLogger(__name__)


@dataclass
class LiquidityLevel:
    """A single liquidity level"""
    price: float
    level_type: str  # PDH, PDL, ASIA_HIGH, ASIA_LOW, LONDON_HIGH, etc.
    strength: float  # 0.0 to 1.0
    timestamp: datetime
    touched: bool = False
    broken: bool = False


@dataclass
class LiquidityZone:
    """Order book liquidity zone"""
    price_low: float
    price_high: float
    total_size: float
    side: str  # BID or ASK
    imbalance_ratio: float  # >1.5 = strong zone
    timestamp: datetime


class LiquidityEngine:
    """
    Tracks and manages liquidity levels for trading decisions.

    V1 Implementation (no CoinGlass):
    - Session highs/lows (Asia, London, New York)
    - Prior day high/low
    - Order book imbalance zones
    - Visible range high/low
    """

    def __init__(self):
        self.levels: List[LiquidityLevel] = []
        self.zones: List[LiquidityZone] = []

        self.kline_history: List[OHLCV] = []
        self.max_kline_history = 100

        self.prior_day_high: Optional[float] = None
        self.prior_day_low: Optional[float] = None

        self.session_levels = {
            "asia_high": None,
            "asia_low": None,
            "london_high": None,
            "london_low": None,
            "ny_high": None,
            "ny_low": None
        }

        self.visible_range_high: Optional[float] = None
        self.visible_range_low: Optional[float] = None

    def add_kline(self, kline: OHLCV):
        """Add kline data and update levels"""
        self.kline_history.append(kline)
        if len(self.kline_history) > self.max_kline_history:
            self.kline_history.pop(0)

        # Update session levels
        self._update_session_levels(kline)

        # Update prior day levels
        self._update_prior_day_levels()

        # Update visible range
        self._update_visible_range()

    def _get_current_session(self) -> Optional[str]:
        """Determine current trading session based on UTC hour"""
        now = datetime.utcnow()
        hour = now.hour

        sessions = LIQUIDITY_LEVELS["session_hours"]

        # Check which session we're in
        for session_name, hours in sessions.items():
            if hours["start"] <= hour < hours["end"]:
                return session_name

        return None

    def _update_session_levels(self, kline: OHLCV):
        """Update session high/low levels"""
        session = self._get_current_session()
        if not session:
            return

        # Update session high
        high_key = f"{session}_high"
        if (self.session_levels[high_key] is None or
                kline.high > self.session_levels[high_key]):
            self.session_levels[high_key] = kline.high

        # Update session low
        low_key = f"{session}_low"
        if (self.session_levels[low_key] is None or
                kline.low < self.session_levels[low_key]):
            self.session_levels[low_key] = kline.low

    def _update_prior_day_levels(self):
        """Update prior day high and low"""
        if len(self.kline_history) < 24:  # Need at least 24 hours
            return

        # Get yesterday's data (assuming hourly klines)
        yesterday_klines = self.kline_history[-48:-24] if len(self.kline_history) >= 48 else []

        if yesterday_klines:
            self.prior_day_high = max(k.high for k in yesterday_klines)
            self.prior_day_low = min(k.low for k in yesterday_klines)

    def _update_visible_range(self):
        """Update visible range high and low"""
        if len(self.kline_history) < 20:
            return

        recent = self.kline_history[-20:]
        self.visible_range_high = max(k.high for k in recent)
        self.visible_range_low = min(k.low for k in recent)

    def update_orderbook_zones(self, orderbook: OrderBook):
        """Analyze order book for liquidity imbalance zones"""
        if not orderbook.bids or not orderbook.asks:
            return

        # Clear old zones
        self.zones = []

        # Analyze bid side
        bid_zones = self._find_imbalance_zones(orderbook.bids, "BID")
        self.zones.extend(bid_zones)

        # Analyze ask side
        ask_zones = self._find_imbalance_zones(orderbook.asks, "ASK")
        self.zones.extend(ask_zones)

        logger.debug(f"Found {len(self.zones)} liquidity zones in order book")

    def _find_imbalance_zones(
        self,
        levels: List,
        side: str,
        threshold: float = None
    ) -> List[LiquidityZone]:
        """Find zones with significant liquidity imbalance"""
        if threshold is None:
            threshold = LIQUIDITY_LEVELS["imbalance_threshold"]

        zones = []

        if len(levels) < 3:
            return zones

        # Group levels by price proximity (0.1% bands)
        price_bands: Dict[float, List] = {}

        for level in levels[:LIQUIDITY_LEVELS["orderbook_depth_levels"]]:
            band_price = round(level.price / level.price * 0.001) * level.price * 0.001
            if band_price not in price_bands:
                price_bands[band_price] = []
            price_bands[band_price].append(level)

        # Find bands with significant size
        avg_size = np.mean([level.quantity for level in levels])

        for band_price, band_levels in price_bands.items():
            total_size = sum(level.quantity for level in band_levels)

            # Check if this band has significant liquidity
            imbalance_ratio = total_size / avg_size if avg_size > 0 else 0

            if imbalance_ratio >= threshold:
                prices = [level.price for level in band_levels]
                zone = LiquidityZone(
                    price_low=min(prices),
                    price_high=max(prices),
                    total_size=total_size,
                    side=side,
                    imbalance_ratio=imbalance_ratio,
                    timestamp=datetime.now()
                )
                zones.append(zone)

        # Sort by imbalance ratio
        zones.sort(key=lambda z: z.imbalance_ratio, reverse=True)

        return zones[:5]  # Top 5 zones per side

    def get_all_levels(self) -> List[LiquidityLevel]:
        """Get all active liquidity levels"""
        levels = []

        # Prior day levels
        if self.prior_day_high:
            levels.append(LiquidityLevel(
                price=self.prior_day_high,
                level_type="PDH",
                strength=0.9,
                timestamp=datetime.now()
            ))

        if self.prior_day_low:
            levels.append(LiquidityLevel(
                price=self.prior_day_low,
                level_type="PDL",
                strength=0.9,
                timestamp=datetime.now()
            ))

        # Session levels
        for session in ["asia", "london", "ny"]:
            high_key = f"{session}_high"
            low_key = f"{session}_low"

            if self.session_levels[high_key]:
                levels.append(LiquidityLevel(
                    price=self.session_levels[high_key],
                    level_type=f"{session.upper()}_HIGH",
                    strength=0.7,
                    timestamp=datetime.now()
                ))

            if self.session_levels[low_key]:
                levels.append(LiquidityLevel(
                    price=self.session_levels[low_key],
                    level_type=f"{session.upper()}_LOW",
                    strength=0.7,
                    timestamp=datetime.now()
                ))

        # Visible range
        if self.visible_range_high:
            levels.append(LiquidityLevel(
                price=self.visible_range_high,
                level_type="VR_HIGH",
                strength=0.6,
                timestamp=datetime.now()
            ))

        if self.visible_range_low:
            levels.append(LiquidityLevel(
                price=self.visible_range_low,
                level_type="VR_LOW",
                strength=0.6,
                timestamp=datetime.now()
            ))

        return levels

    def find_nearest_liquidity(
        self,
        current_price: float,
        direction: str = "BOTH"
    ) -> Dict[str, Optional[LiquidityLevel]]:
        """Find nearest liquidity levels above and below current price"""
        levels = self.get_all_levels()

        above = [l for l in levels if l.price > current_price]
        below = [l for l in levels if l.price < current_price]

        result = {
            "above": min(above, key=lambda l: l.price - current_price) if above else None,
            "below": max(below, key=lambda l: current_price - l.price) if below else None
        }

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get current liquidity engine status"""
        levels = self.get_all_levels()

        return {
            "total_levels": len(levels),
            "prior_day": {
                "high": self.prior_day_high,
                "low": self.prior_day_low
            },
            "session_levels": {
                k: v for k, v in self.session_levels.items() if v is not None
            },
            "visible_range": {
                "high": self.visible_range_high,
                "low": self.visible_range_low
            },
            "orderbook_zones": len(self.zones),
            "top_zones": [
                {
                    "side": z.side,
                    "price_range": f"{z.price_low:.2f}-{z.price_high:.2f}",
                    "size": z.total_size,
                    "imbalance": z.imbalance_ratio
                }
                for z in self.zones[:3]
            ] if self.zones else []
        }
