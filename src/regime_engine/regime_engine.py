import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import deque

from src.config import RegimeState, REGIME_PERMISSIONS
from src.models import RegimeInput, RegimeOutput, RegimeTransition, TrendData
from .trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)


class RegimeEngine:
    """
    Computes market regime state based on macro indicators and news.
    Implements state machine with anti-flipping logic.
    """

    def __init__(self, min_time_in_state: int = 3600):
        """
        Args:
            min_time_in_state: Minimum seconds in a state before allowing transition (default 1 hour)
        """
        self.trend_analyzer = TrendAnalyzer()

        self.current_state = RegimeState.CHOP
        self.state_entered_at = datetime.now()
        self.last_update = datetime.now()

        self.min_time_in_state = min_time_in_state
        self.confidence_threshold = 0.6

        self.state_history: deque = deque(maxlen=50)
        self.transition_history: List[RegimeTransition] = []

        logger.info(f"Regime Engine initialized. Initial state: {self.current_state}")

    def _calculate_regime_scores(self, regime_input: RegimeInput) -> Dict[RegimeState, float]:
        """Calculate scores for each possible regime state"""
        scores = {
            RegimeState.RISK_ON: 0.0,
            RegimeState.RISK_OFF: 0.0,
            RegimeState.DECOUPLED: 0.0,
            RegimeState.CHOP: 0.0
        }

        weights = {
            "dxy": 0.4,
            "btc_dom": 0.3,
            "news": 0.3
        }

        # DXY contribution
        if regime_input.dxy_trend:
            dxy_signal = self._get_dxy_contribution(regime_input.dxy_trend)
            for state, value in dxy_signal.items():
                scores[state] += value * weights["dxy"]

        # BTC Dominance contribution
        if regime_input.btc_dominance_trend:
            btc_dom_signal = self._get_btc_dom_contribution(regime_input.btc_dominance_trend)
            for state, value in btc_dom_signal.items():
                scores[state] += value * weights["btc_dom"]

        # News contribution
        if regime_input.news_signals:
            news_signal = self._get_news_contribution(regime_input.news_signals)
            for state, value in news_signal.items():
                scores[state] += value * weights["news"]

        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores

    def _get_dxy_contribution(self, dxy_trend: TrendData) -> Dict[RegimeState, float]:
        """Calculate DXY contribution to regime scores"""
        contribution = {
            RegimeState.RISK_ON: 0.0,
            RegimeState.RISK_OFF: 0.0,
            RegimeState.DECOUPLED: 0.0,
            RegimeState.CHOP: 0.0
        }

        strength_multiplier = {
            "STRONG": 1.0,
            "WEAK": 0.5,
            "NONE": 0.0
        }

        multiplier = strength_multiplier.get(dxy_trend.strength, 0.0)

        if dxy_trend.direction == "UP":
            # DXY rising = USD strength = RISK_OFF
            contribution[RegimeState.RISK_OFF] = 1.0 * multiplier
        elif dxy_trend.direction == "DOWN":
            # DXY falling = USD weakness = RISK_ON
            contribution[RegimeState.RISK_ON] = 1.0 * multiplier
        else:
            # Flat DXY = CHOP
            contribution[RegimeState.CHOP] = 0.5

        return contribution

    def _get_btc_dom_contribution(self, btc_dom_trend: TrendData) -> Dict[RegimeState, float]:
        """Calculate BTC dominance contribution to regime scores"""
        contribution = {
            RegimeState.RISK_ON: 0.0,
            RegimeState.RISK_OFF: 0.0,
            RegimeState.DECOUPLED: 0.0,
            RegimeState.CHOP: 0.0
        }

        strength_multiplier = {
            "STRONG": 1.0,
            "WEAK": 0.5,
            "NONE": 0.0
        }

        multiplier = strength_multiplier.get(btc_dom_trend.strength, 0.0)

        if btc_dom_trend.direction == "UP":
            # BTC.D rising = BTC outperforming = possible DECOUPLED or RISK_OFF
            contribution[RegimeState.DECOUPLED] = 0.6 * multiplier
            contribution[RegimeState.RISK_OFF] = 0.4 * multiplier
        elif btc_dom_trend.direction == "DOWN":
            # BTC.D falling = Alts outperforming = RISK_ON in crypto
            contribution[RegimeState.RISK_ON] = 0.7 * multiplier
            contribution[RegimeState.DECOUPLED] = 0.3 * multiplier
        else:
            contribution[RegimeState.CHOP] = 0.5

        return contribution

    def _get_news_contribution(self, news_signals: Dict[str, Any]) -> Dict[RegimeState, float]:
        """Calculate news contribution to regime scores"""
        contribution = {
            RegimeState.RISK_ON: 0.0,
            RegimeState.RISK_OFF: 0.0,
            RegimeState.DECOUPLED: 0.0,
            RegimeState.CHOP: 0.0
        }

        if not news_signals or news_signals.get("news_count", 0) == 0:
            contribution[RegimeState.CHOP] = 0.3
            return contribution

        risk_signal = news_signals.get("risk_signal", "NEUTRAL")
        alignment = news_signals.get("alignment", "NEUTRAL")
        high_impact_count = news_signals.get("high_impact_count", 0)

        # Risk signal contribution
        if risk_signal == "RISK_OFF":
            contribution[RegimeState.RISK_OFF] = 0.8
        elif risk_signal == "RISK_ON":
            contribution[RegimeState.RISK_ON] = 0.8
        else:
            contribution[RegimeState.CHOP] = 0.3

        # Alignment contribution
        if alignment == "DECOUPLED":
            contribution[RegimeState.DECOUPLED] += 0.5
        elif alignment == "ALIGNED":
            # Strengthen the risk signal
            if risk_signal == "RISK_OFF":
                contribution[RegimeState.RISK_OFF] += 0.2
            elif risk_signal == "RISK_ON":
                contribution[RegimeState.RISK_ON] += 0.2

        # High impact news reduces CHOP
        if high_impact_count > 0:
            contribution[RegimeState.CHOP] *= 0.5

        return contribution

    def _should_transition(self, new_state: RegimeState, confidence: float) -> bool:
        """Determine if state transition should occur"""
        # Same state, no transition needed
        if new_state == self.current_state:
            return False

        # Check confidence threshold
        if confidence < self.confidence_threshold:
            logger.debug(
                f"Confidence {confidence:.2f} below threshold {self.confidence_threshold}"
            )
            return False

        # Check minimum time in current state
        time_in_state = (datetime.now() - self.state_entered_at).total_seconds()
        if time_in_state < self.min_time_in_state:
            logger.debug(
                f"Time in state {time_in_state}s below minimum {self.min_time_in_state}s"
            )
            return False

        return True

    def update(self, regime_input: RegimeInput) -> RegimeOutput:
        """Update regime state based on new inputs"""
        # Calculate scores for all states
        scores = self._calculate_regime_scores(regime_input)

        # Determine new state (highest score)
        new_state = max(scores, key=scores.get)
        confidence = scores[new_state]

        # Individual contributions for output
        dxy_contrib = 0.0
        btc_dom_contrib = 0.0
        news_contrib = 0.0

        if regime_input.dxy_trend:
            dxy_signal = self._get_dxy_contribution(regime_input.dxy_trend)
            dxy_contrib = dxy_signal.get(new_state, 0.0)

        if regime_input.btc_dominance_trend:
            btc_dom_signal = self._get_btc_dom_contribution(regime_input.btc_dominance_trend)
            btc_dom_contrib = btc_dom_signal.get(new_state, 0.0)

        if regime_input.news_signals:
            news_signal = self._get_news_contribution(regime_input.news_signals)
            news_contrib = news_signal.get(new_state, 0.0)

        # Check if transition should occur
        if self._should_transition(new_state, confidence):
            reason = self._build_transition_reason(scores, regime_input)

            transition = RegimeTransition(
                from_state=self.current_state,
                to_state=new_state,
                reason=reason,
                confidence=confidence,
                timestamp=datetime.now()
            )

            self.transition_history.append(transition)
            self.current_state = new_state
            self.state_entered_at = datetime.now()

            logger.info(
                f"Regime transition: {transition.from_state} -> {transition.to_state} "
                f"(confidence: {confidence:.2f}) | {reason}"
            )

        # Update state history
        self.state_history.append(self.current_state.value)

        # Calculate time in current state
        time_in_state = (datetime.now() - self.state_entered_at).total_seconds()

        # Get permissions for current state
        permissions = REGIME_PERMISSIONS.get(self.current_state, {})

        # Build output
        output = RegimeOutput(
            state=self.current_state,
            confidence=confidence,
            dxy_contribution=dxy_contrib,
            btc_dom_contribution=btc_dom_contrib,
            news_contribution=news_contrib,
            permissions=permissions,
            timestamp=datetime.now(),
            time_in_state=time_in_state,
            state_history=list(self.state_history)
        )

        self.last_update = datetime.now()

        return output

    def _build_transition_reason(self, scores: Dict[RegimeState, float],
                                 regime_input: RegimeInput) -> str:
        """Build human-readable transition reason"""
        reasons = []

        if regime_input.dxy_trend:
            reasons.append(
                f"DXY {regime_input.dxy_trend.direction} "
                f"({regime_input.dxy_trend.strength})"
            )

        if regime_input.btc_dominance_trend:
            reasons.append(
                f"BTC.D {regime_input.btc_dominance_trend.direction} "
                f"({regime_input.btc_dominance_trend.strength})"
            )

        if regime_input.news_signals:
            risk_signal = regime_input.news_signals.get("risk_signal", "NEUTRAL")
            if risk_signal != "NEUTRAL":
                reasons.append(f"News: {risk_signal}")

        return " | ".join(reasons) if reasons else "Low conviction"

    def force_state(self, state: RegimeState, reason: str = "Manual override"):
        """Force regime to a specific state (for testing or manual control)"""
        if state != self.current_state:
            transition = RegimeTransition(
                from_state=self.current_state,
                to_state=state,
                reason=reason,
                confidence=1.0,
                timestamp=datetime.now()
            )

            self.transition_history.append(transition)
            self.current_state = state
            self.state_entered_at = datetime.now()

            logger.warning(f"Forced regime transition: {transition.from_state} -> {state}")

    def get_status(self) -> Dict[str, Any]:
        """Get current regime engine status"""
        time_in_state = (datetime.now() - self.state_entered_at).total_seconds()

        recent_transitions = self.transition_history[-5:]

        return {
            "current_state": self.current_state.value,
            "time_in_state_seconds": time_in_state,
            "time_in_state_formatted": str(timedelta(seconds=int(time_in_state))),
            "last_update": self.last_update.isoformat(),
            "state_entered_at": self.state_entered_at.isoformat(),
            "permissions": REGIME_PERMISSIONS.get(self.current_state, {}),
            "recent_transitions": [
                {
                    "from": t.from_state.value,
                    "to": t.to_state.value,
                    "reason": t.reason,
                    "confidence": t.confidence,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in recent_transitions
            ],
            "state_history": list(self.state_history)
        }
