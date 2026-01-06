from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


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
    side: str


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
    impact_level: Optional[str] = Field(default="LOW", pattern="^(HIGH|MEDIUM|LOW)$")
