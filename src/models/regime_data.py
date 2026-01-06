from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.config import RegimeState


class TrendData(BaseModel):
    """Trend analysis for an indicator"""
    current_value: float
    slope: float
    direction: str
    strength: str
    lookback_periods: int
    timestamp: datetime


class RegimeInput(BaseModel):
    """Inputs for regime calculation"""
    dxy_trend: Optional[TrendData] = None
    btc_dominance_trend: Optional[TrendData] = None
    news_signals: Optional[Dict[str, Any]] = None
    timestamp: datetime


class RegimeOutput(BaseModel):
    """Complete regime state output"""
    state: RegimeState
    confidence: float
    dxy_contribution: float
    btc_dom_contribution: float
    news_contribution: float
    permissions: Dict[str, Any]
    timestamp: datetime
    time_in_state: float
    state_history: List[str]


class RegimeTransition(BaseModel):
    """Record of a regime state transition"""
    from_state: RegimeState
    to_state: RegimeState
    reason: str
    confidence: float
    timestamp: datetime
