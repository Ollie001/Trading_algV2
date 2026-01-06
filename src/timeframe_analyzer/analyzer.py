import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.config import Timeframe
from src.data_ingestion import BybitRESTClient
from src.models import OHLCV, RegimeOutput
from src.capital_flow import CapitalFlowSignal
from src.liquidity_engine import LiquidityLevel

logger = logging.getLogger(__name__)


@dataclass
class TimeframeBias:
    """Represents the market bias for a specific timeframe"""
    timeframe: str
    bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    confidence: float  # 0-1
    current_price: float
    trend_direction: str
    trend_strength: float
    ma_alignment: str
    supporting_factors: List[str]
    conflicting_factors: List[str]
    explanation: str
    timestamp: datetime


class TimeframeAnalyzer:
    """
    Multi-timeframe bias analyzer that determines market direction
    across different timeframes and provides detailed explanations.
    """

    TIMEFRAMES = {
        "15M": (Timeframe.FIFTEEN_MINUTE, 100),
        "1H": (Timeframe.ONE_HOUR, 100),
        "4H": (Timeframe.FOUR_HOUR, 100),
        "Daily": (Timeframe.ONE_DAY, 100),
    }

    def __init__(self, bybit_rest: BybitRESTClient):
        self.bybit_rest = bybit_rest

    async def analyze_all_timeframes(
        self,
        symbol: str = "BTCUSDT",
        regime: Optional[RegimeOutput] = None,
        capital_flow: Optional[CapitalFlowSignal] = None,
        liquidity_levels: Optional[List[LiquidityLevel]] = None,
    ) -> Dict[str, TimeframeBias]:
        """
        Analyze bias across all timeframes with detailed explanations.

        Args:
            symbol: Trading symbol
            regime: Current regime state
            capital_flow: Capital flow analysis
            liquidity_levels: Liquidity levels from liquidity engine

        Returns:
            Dictionary mapping timeframe names to TimeframeBias objects
        """
        results = {}

        for tf_name, (tf_enum, limit) in self.TIMEFRAMES.items():
            try:
                bias = await self._analyze_timeframe(
                    symbol=symbol,
                    timeframe_name=tf_name,
                    timeframe=tf_enum,
                    limit=limit,
                    regime=regime,
                    capital_flow=capital_flow,
                    liquidity_levels=liquidity_levels,
                )
                results[tf_name] = bias
            except Exception as e:
                logger.error(f"Error analyzing {tf_name} timeframe: {e}")
                # Return neutral bias on error
                results[tf_name] = TimeframeBias(
                    timeframe=tf_name,
                    bias="NEUTRAL",
                    confidence=0.0,
                    current_price=0.0,
                    trend_direction="UNKNOWN",
                    trend_strength=0.0,
                    ma_alignment="UNKNOWN",
                    supporting_factors=[],
                    conflicting_factors=[f"Error fetching data: {str(e)}"],
                    explanation="Unable to analyze timeframe due to data unavailability.",
                    timestamp=datetime.now(),
                )

        return results

    async def _analyze_timeframe(
        self,
        symbol: str,
        timeframe_name: str,
        timeframe: Timeframe,
        limit: int,
        regime: Optional[RegimeOutput],
        capital_flow: Optional[CapitalFlowSignal],
        liquidity_levels: Optional[List[LiquidityLevel]],
    ) -> TimeframeBias:
        """Analyze a single timeframe"""
        # Fetch klines
        klines = await self.bybit_rest.get_klines(symbol, timeframe, limit)

        if not klines or len(klines) < 20:
            raise ValueError(f"Insufficient data for {timeframe_name}")

        # Calculate technical indicators
        closes = [k.close for k in klines]
        current_price = closes[-1]

        # Moving averages
        ma_20 = sum(closes[-20:]) / 20
        ma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else ma_20
        ma_100 = sum(closes[-100:]) / 100 if len(closes) >= 100 else ma_50

        # Trend direction and strength
        trend_direction = self._calculate_trend_direction(closes)
        trend_strength = self._calculate_trend_strength(closes)

        # MA alignment
        ma_alignment = self._calculate_ma_alignment(current_price, ma_20, ma_50, ma_100)

        # Momentum
        momentum = self._calculate_momentum(closes)

        # Determine bias
        bias, confidence = self._determine_bias(
            current_price=current_price,
            ma_20=ma_20,
            ma_50=ma_50,
            ma_100=ma_100,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            momentum=momentum,
        )

        # Generate supporting and conflicting factors
        supporting_factors, conflicting_factors = self._generate_factors(
            timeframe_name=timeframe_name,
            bias=bias,
            current_price=current_price,
            ma_20=ma_20,
            ma_50=ma_50,
            ma_100=ma_100,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            momentum=momentum,
            regime=regime,
            capital_flow=capital_flow,
            liquidity_levels=liquidity_levels,
        )

        # Generate explanation
        explanation = self._generate_explanation(
            timeframe_name=timeframe_name,
            bias=bias,
            confidence=confidence,
            supporting_factors=supporting_factors,
            conflicting_factors=conflicting_factors,
        )

        return TimeframeBias(
            timeframe=timeframe_name,
            bias=bias,
            confidence=confidence,
            current_price=current_price,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            ma_alignment=ma_alignment,
            supporting_factors=supporting_factors,
            conflicting_factors=conflicting_factors,
            explanation=explanation,
            timestamp=datetime.now(),
        )

    def _calculate_trend_direction(self, closes: List[float]) -> str:
        """Calculate overall trend direction"""
        if len(closes) < 20:
            return "UNKNOWN"

        # Compare recent price action to older price action
        recent_avg = sum(closes[-10:]) / 10
        older_avg = sum(closes[-20:-10]) / 10

        if recent_avg > older_avg * 1.01:  # 1% threshold
            return "UP"
        elif recent_avg < older_avg * 0.99:
            return "DOWN"
        else:
            return "SIDEWAYS"

    def _calculate_trend_strength(self, closes: List[float]) -> float:
        """Calculate trend strength (0-1)"""
        if len(closes) < 20:
            return 0.0

        # Count higher highs and higher lows for uptrend
        # Count lower highs and lower lows for downtrend
        highs = []
        lows = []

        for i in range(len(closes) - 5):
            window = closes[i : i + 5]
            highs.append(max(window))
            lows.append(min(window))

        if len(highs) < 2:
            return 0.0

        # Check for consistent trend
        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i - 1])
        higher_lows = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i - 1])
        lower_highs = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i - 1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i - 1])

        uptrend_strength = (higher_highs + higher_lows) / (2 * (len(highs) - 1))
        downtrend_strength = (lower_highs + lower_lows) / (2 * (len(highs) - 1))

        return max(uptrend_strength, downtrend_strength)

    def _calculate_ma_alignment(
        self, current_price: float, ma_20: float, ma_50: float, ma_100: float
    ) -> str:
        """Calculate moving average alignment"""
        if current_price > ma_20 > ma_50 > ma_100:
            return "BULLISH_ALIGNED"
        elif current_price < ma_20 < ma_50 < ma_100:
            return "BEARISH_ALIGNED"
        elif current_price > ma_20 and current_price > ma_50:
            return "BULLISH"
        elif current_price < ma_20 and current_price < ma_50:
            return "BEARISH"
        else:
            return "MIXED"

    def _calculate_momentum(self, closes: List[float]) -> float:
        """Calculate price momentum (-1 to 1)"""
        if len(closes) < 20:
            return 0.0

        # Rate of change over last 20 periods
        roc = (closes[-1] - closes[-20]) / closes[-20]

        # Normalize to -1 to 1 range (assuming max 10% move)
        return max(-1.0, min(1.0, roc * 10))

    def _determine_bias(
        self,
        current_price: float,
        ma_20: float,
        ma_50: float,
        ma_100: float,
        trend_direction: str,
        trend_strength: float,
        momentum: float,
    ) -> tuple[str, float]:
        """Determine bias and confidence based on indicators"""
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0

        # Price vs MAs
        if current_price > ma_20:
            bullish_signals += 1
        else:
            bearish_signals += 1
        total_signals += 1

        if current_price > ma_50:
            bullish_signals += 1
        else:
            bearish_signals += 1
        total_signals += 1

        # Trend direction
        if trend_direction == "UP":
            bullish_signals += 2  # Weight trend more heavily
        elif trend_direction == "DOWN":
            bearish_signals += 2
        total_signals += 2

        # Momentum
        if momentum > 0.1:
            bullish_signals += 1
        elif momentum < -0.1:
            bearish_signals += 1
        total_signals += 1

        # MA alignment
        if ma_20 > ma_50 > ma_100:
            bullish_signals += 1
        elif ma_20 < ma_50 < ma_100:
            bearish_signals += 1
        total_signals += 1

        # Determine bias
        if bullish_signals > bearish_signals * 1.5:
            bias = "BULLISH"
            confidence = (bullish_signals / total_signals) * trend_strength
        elif bearish_signals > bullish_signals * 1.5:
            bias = "BEARISH"
            confidence = (bearish_signals / total_signals) * trend_strength
        else:
            bias = "NEUTRAL"
            confidence = 1.0 - abs(bullish_signals - bearish_signals) / total_signals

        return bias, min(1.0, max(0.0, confidence))

    def _generate_factors(
        self,
        timeframe_name: str,
        bias: str,
        current_price: float,
        ma_20: float,
        ma_50: float,
        ma_100: float,
        trend_direction: str,
        trend_strength: float,
        momentum: float,
        regime: Optional[RegimeOutput],
        capital_flow: Optional[CapitalFlowSignal],
        liquidity_levels: Optional[List[LiquidityLevel]],
    ) -> tuple[List[str], List[str]]:
        """Generate supporting and conflicting factors"""
        supporting = []
        conflicting = []

        # Technical factors
        if bias == "BULLISH":
            if current_price > ma_20:
                supporting.append(f"Price (${current_price:,.2f}) above 20-period MA (${ma_20:,.2f})")
            else:
                conflicting.append(f"Price (${current_price:,.2f}) below 20-period MA (${ma_20:,.2f})")

            if current_price > ma_50:
                supporting.append(f"Price above 50-period MA (${ma_50:,.2f})")
            else:
                conflicting.append(f"Price below 50-period MA (${ma_50:,.2f})")

            if trend_direction == "UP":
                supporting.append(f"Clear uptrend with {trend_strength:.1%} strength")
            elif trend_direction == "DOWN":
                conflicting.append("Downtrend conflicts with bullish bias")

            if momentum > 0:
                supporting.append(f"Positive momentum ({momentum:+.2%})")
            else:
                conflicting.append(f"Negative momentum ({momentum:+.2%})")

        elif bias == "BEARISH":
            if current_price < ma_20:
                supporting.append(f"Price (${current_price:,.2f}) below 20-period MA (${ma_20:,.2f})")
            else:
                conflicting.append(f"Price (${current_price:,.2f}) above 20-period MA (${ma_20:,.2f})")

            if current_price < ma_50:
                supporting.append(f"Price below 50-period MA (${ma_50:,.2f})")
            else:
                conflicting.append(f"Price above 50-period MA (${ma_50:,.2f})")

            if trend_direction == "DOWN":
                supporting.append(f"Clear downtrend with {trend_strength:.1%} strength")
            elif trend_direction == "UP":
                conflicting.append("Uptrend conflicts with bearish bias")

            if momentum < 0:
                supporting.append(f"Negative momentum ({momentum:+.2%})")
            else:
                conflicting.append(f"Positive momentum ({momentum:+.2%})")

        # Regime factors
        if regime:
            regime_bias = self._regime_to_bias(regime.state.value)
            if regime_bias == bias:
                supporting.append(f"Regime ({regime.state.value}) aligned with {bias.lower()} bias")
            elif regime_bias != "NEUTRAL" and regime_bias != bias:
                conflicting.append(f"Regime ({regime.state.value}) suggests {regime_bias.lower()} bias")

        # Capital flow factors
        if capital_flow:
            if capital_flow.bias == bias:
                supporting.append(f"Capital flow {capital_flow.flow_direction} supports {bias.lower()} bias")
            elif capital_flow.bias != "NEUTRAL" and capital_flow.bias != bias:
                conflicting.append(f"Capital flow suggests {capital_flow.bias.lower()} bias")

        # Liquidity factors
        if liquidity_levels:
            nearby_levels = self._find_nearby_liquidity(current_price, liquidity_levels)
            if nearby_levels:
                if bias == "BULLISH":
                    resistance = [l for l in nearby_levels if l.price > current_price]
                    support = [l for l in nearby_levels if l.price < current_price]
                    if support:
                        supporting.append(f"Support level at ${support[0].price:,.2f}")
                    if resistance:
                        conflicting.append(f"Resistance level at ${resistance[0].price:,.2f}")
                elif bias == "BEARISH":
                    resistance = [l for l in nearby_levels if l.price > current_price]
                    support = [l for l in nearby_levels if l.price < current_price]
                    if resistance:
                        supporting.append(f"Resistance level at ${resistance[0].price:,.2f}")
                    if support:
                        conflicting.append(f"Support level at ${support[0].price:,.2f}")

        return supporting, conflicting

    def _regime_to_bias(self, regime_state: str) -> str:
        """Convert regime state to bias"""
        if regime_state in ["RISK_ON", "EXPANSION"]:
            return "BULLISH"
        elif regime_state in ["RISK_OFF", "CONTRACTION"]:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _find_nearby_liquidity(
        self, current_price: float, levels: List[LiquidityLevel], threshold: float = 0.02
    ) -> List[LiquidityLevel]:
        """Find liquidity levels within threshold % of current price"""
        nearby = []
        for level in levels:
            if not level.broken:
                distance = abs(level.price - current_price) / current_price
                if distance <= threshold:
                    nearby.append(level)

        # Sort by proximity
        nearby.sort(key=lambda l: abs(l.price - current_price))
        return nearby[:3]  # Return top 3 closest levels

    def _generate_explanation(
        self,
        timeframe_name: str,
        bias: str,
        confidence: float,
        supporting_factors: List[str],
        conflicting_factors: List[str],
    ) -> str:
        """Generate human-readable explanation of the bias"""
        explanation = f"The {timeframe_name} timeframe shows a {bias} bias with {confidence:.0%} confidence. "

        if supporting_factors:
            explanation += "Supporting factors: " + "; ".join(supporting_factors[:3]) + ". "

        if conflicting_factors:
            explanation += "However, " + "; ".join(conflicting_factors[:2]) + "."

        if confidence < 0.4:
            explanation += " Low confidence suggests waiting for clearer signals."
        elif confidence > 0.7:
            explanation += " High confidence supports acting on this bias."

        return explanation
