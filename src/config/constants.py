from enum import Enum


class RegimeState(str, Enum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    DECOUPLED = "DECOUPLED"
    CHOP = "CHOP"


class Timeframe(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTE = "5m"
    FIFTEEN_MINUTE = "15m"
    ONE_HOUR = "1h"
    FOUR_HOUR = "4h"
    ONE_DAY = "1d"


class TradeType(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderSide(str, Enum):
    BUY = "Buy"
    SELL = "Sell"


BYBIT_WS_PUBLIC_URL = "wss://stream.bybit.com/v5/public/linear"
BYBIT_WS_PRIVATE_URL = "wss://stream.bybit.com/v5/private"
BYBIT_REST_URL = "https://api.bybit.com"

BYBIT_WS_TESTNET_PUBLIC_URL = "wss://stream-testnet.bybit.com/v5/public/linear"
BYBIT_WS_TESTNET_PRIVATE_URL = "wss://stream-testnet.bybit.com/v5/private"
BYBIT_REST_TESTNET_URL = "https://api-testnet.bybit.com"

EXECUTION_TIMEFRAMES = [Timeframe.FIVE_MINUTE, Timeframe.ONE_MINUTE]
REGIME_TIMEFRAMES = [Timeframe.FOUR_HOUR, Timeframe.ONE_DAY]

REGIME_PERMISSIONS = {
    RegimeState.RISK_ON: {
        "trading_enabled": True,
        "position_size_multiplier": 1.0,
        "preferred_trades": [TradeType.LONG],
        "allow_runners": True,
    },
    RegimeState.RISK_OFF: {
        "trading_enabled": True,
        "position_size_multiplier": 0.5,
        "preferred_trades": [TradeType.SHORT],
        "allow_runners": False,
    },
    RegimeState.DECOUPLED: {
        "trading_enabled": True,
        "position_size_multiplier": 0.75,
        "preferred_trades": [TradeType.LONG, TradeType.SHORT],
        "allow_runners": True,
    },
    RegimeState.CHOP: {
        "trading_enabled": False,
        "position_size_multiplier": 0.0,
        "preferred_trades": [],
        "allow_runners": False,
    },
}

RISK_THRESHOLDS = {
    "max_position_size_usd": 1000,
    "base_risk_percent": 1.0,
    "max_daily_loss_percent": 5.0,
    "max_open_positions": 3,
    "min_risk_reward_ratio": 1.5,
}

DXY_THRESHOLDS = {
    "strong_trend_slope": 0.5,
    "weak_trend_slope": 0.1,
    "lookback_periods": 24,
}

BTC_DOMINANCE_THRESHOLDS = {
    "rising_threshold": 0.2,
    "falling_threshold": -0.2,
    "lookback_periods": 24,
}

NEWS_IMPACT_WINDOWS = {
    "HIGH": 4,
    "MEDIUM": 2,
    "LOW": 1,
}

LIQUIDITY_LEVELS = {
    "session_hours": {
        "asia": {"start": 0, "end": 8},
        "london": {"start": 8, "end": 16},
        "new_york": {"start": 13, "end": 21},
    },
    "orderbook_depth_levels": 20,
    "imbalance_threshold": 1.5,
}
