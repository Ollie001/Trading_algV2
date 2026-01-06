from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class OrderBookLevel(BaseModel):
    price: float
    quantity: float


class OrderBook(BaseModel):
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]


class Trade(BaseModel):
    symbol: str
    timestamp: datetime
    price: float
    quantity: float
    # Enforce a strict enum so upstream parsing bugs are caught early.
    side: Literal["buy", "sell"]


class OHLCV(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str


class FundingRate(BaseModel):
    symbol: str
    timestamp: datetime
    funding_rate: float
    next_funding_time: datetime


class DXYData(BaseModel):
    timestamp: datetime
    value: float
    change_percent: Optional[float] = None
    source: str = "twelve_data"


class BTCDominanceData(BaseModel):
    timestamp: datetime
    value: float
    change_percent: Optional[float] = None
    source: str = "coingecko"


class NewsItem(BaseModel):
    id: str
    timestamp: datetime
    title: str
    description: Optional[str] = None
    source: str
    url: Optional[str] = None
    category: Optional[str] = None
    sentiment_score: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    # Narrow the type to a strict enum for safer downstream logic.
    impact_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(default="LOW")
