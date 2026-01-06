# Macro-Aware BTC Trading Bot

A sophisticated Bitcoin trading bot that combines macro indicators, crypto capital flow analysis, news awareness, and deterministic execution logic.

## Architecture

The system is built with a layered decision stack:

1. **Macro & News Regime Layer** (slow) - Analyzes DXY, BTC dominance, and news events
2. **Capital Flow Layer** (medium) - Tracks BTC dominance trends
3. **Liquidity / Path Layer** (medium) - Order book analysis and liquidity zones
4. **Execution Layer** (fast) - Trade execution on Bybit
5. **Risk & Trade Management** - Position sizing and risk controls

## Current Implementation Status

### Module 1: Config & Constants ✅
- API key management via `.env`
- Timeframe definitions
- Risk parameters
- Threshold values for all indicators
- Regime state definitions and permissions

### Module 2: Data Ingestion ✅
- **Bybit WebSocket Client** - Real-time orderbook, trades, and klines
- **Bybit REST Client** - Historical data, funding rates, and market info
- **DXY Fetcher** - US Dollar Index from Twelve Data API
- **BTC Dominance Fetcher** - Bitcoin dominance from CoinGecko API
- **News Feed Listener** - Real-time crypto and macro news from NewsAPI

### Module 3: News Classification ✅
- **Keyword-Based Categorization** - Macro and crypto event classification
- **Sentiment Analysis** - Scoring from -1.0 (negative) to +1.0 (positive)
- **Impact Level Detection** - HIGH, MEDIUM, LOW classification
- **Alignment Detection** - ALIGNED, DECOUPLED, or NEUTRAL with broader markets
- **Regime Signal Aggregation** - Combines active news for regime input

### Module 4: Regime Engine ✅
- **Trend Analyzer** - DXY and BTC dominance trend detection with linear regression
- **State Machine** - RISK_ON, RISK_OFF, DECOUPLED, CHOP regime states
- **Anti-Flipping Logic** - Prevents rapid state changes (min 1 hour in state)
- **Multi-Input Scoring** - Weighted DXY (40%), BTC.D (30%), News (30%)
- **Trading Permissions** - Dynamic position sizing and trade type preferences

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Bybit API
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
BYBIT_TESTNET=true

# Twelve Data API (for DXY)
TWELVE_DATA_API_KEY=your_twelve_data_key_here

# CoinGecko API (optional - free tier available)
COINGECKO_API_KEY=your_coingecko_key_here

# News API
NEWS_API_KEY=your_news_api_key_here
```

### 3. Get API Keys

- **Bybit**: [https://www.bybit.com/app/user/api-management](https://www.bybit.com/app/user/api-management)
- **Twelve Data**: [https://twelvedata.com/pricing](https://twelvedata.com/pricing) (Free tier available)
- **CoinGecko**: [https://www.coingecko.com/en/api/pricing](https://www.coingecko.com/en/api/pricing) (Free tier available)
- **NewsAPI**: [https://newsapi.org/pricing](https://newsapi.org/pricing) (Free tier available)

## Running the Application

### Start the FastAPI Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Access the Web UI

Open your browser and navigate to:

- **Dashboard**: [http://localhost:8000/ui](http://localhost:8000/ui)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

## API Endpoints

### Market Data

- `GET /api/market/orderbook` - Latest orderbook snapshot
- `GET /api/market/latest-trade` - Most recent trade
- `GET /api/market/latest-kline` - Latest candlestick data
- `GET /api/market/klines?symbol=BTCUSDT&interval=5&limit=100` - Historical klines

### Macro Data

- `GET /api/macro/dxy` - Current DXY (US Dollar Index) value
- `GET /api/macro/btc-dominance` - Current BTC dominance percentage

### News

- `GET /api/news/latest` - Latest news item received
- `GET /api/news/fetch?query=bitcoin&limit=10` - Fetch news articles

### Status

- `GET /api/status` - Complete system status with all latest data
- `GET /health` - Health check of all components

## Project Structure

```
trading_algV2/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── constants.py      # Enums, constants, thresholds
│   │   └── settings.py       # Environment-based settings
│   ├── data_ingestion/
│   │   ├── __init__.py
│   │   ├── bybit_websocket.py    # Real-time market data
│   │   ├── bybit_rest.py         # Historical data & orders
│   │   ├── dxy_fetcher.py        # DXY macro indicator
│   │   ├── btc_dominance_fetcher.py  # BTC dominance
│   │   └── news_fetcher.py       # News feed
│   ├── models/
│   │   ├── __init__.py
│   │   └── market_data.py    # Pydantic models
│   └── utils/
│       └── __init__.py
├── main.py                   # FastAPI application
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Features

### Real-Time Data Streaming
- WebSocket connections to Bybit for orderbook, trades, and klines
- Automatic reconnection with exponential backoff
- Heartbeat mechanism to keep connections alive

### Macro Indicators
- DXY (US Dollar Index) tracking
- BTC dominance monitoring
- News sentiment analysis (ready for integration)

### Web Dashboard
- Real-time updates every 5 seconds
- Visual representation of all data sources
- Clean, modern UI with gradient design

## Next Steps

The following modules are planned for future implementation:

- **Module 3**: News Classification - Sentiment analysis and impact scoring
- **Module 4**: Regime Engine - Market regime detection (RISK_ON, RISK_OFF, DECOUPLED, CHOP)
- **Module 5**: Capital Flow Analyzer - BTC dominance trend analysis
- **Module 6**: Liquidity Engine - Session highs/lows, order book imbalance
- **Module 7**: Execution Engine - Entry/exit logic with structure detection
- **Module 8**: Risk Manager - Dynamic position sizing
- **Module 9**: Trade Manager - Order placement and tracking
- **Module 10**: Advanced Web UI Backend - WebSocket broadcasting
- **Module 11**: Enhanced Frontend - Interactive charts and controls

## Development

### Running in Debug Mode

Set `DEBUG=true` in your `.env` file for auto-reload on code changes.

### Logging

The application uses Python's built-in logging. Logs are output to console with timestamps.

### Testing Data Ingestion

You can test individual components:

```python
import asyncio
from src.data_ingestion import DXYFetcher, BTCDominanceFetcher

async def test():
    dxy = DXYFetcher()
    data = await dxy.get_current_value()
    print(f"DXY: {data.value}")

asyncio.run(test())
```

## Configuration

### Risk Parameters

Edit `src/config/constants.py` to modify:
- Position size limits
- Risk percentages
- Daily loss limits
- Risk/reward ratios

### Timeframes

The bot supports multiple timeframes defined in `Timeframe` enum:
- 1m, 5m, 15m (execution)
- 1h, 4h, 1d (regime analysis)

### Regime Permissions

Regime states and their trading permissions are configured in `REGIME_PERMISSIONS`:
- `RISK_ON`: Full size, prefer longs
- `RISK_OFF`: Reduced size, prefer shorts
- `DECOUPLED`: 75% size, both directions
- `CHOP`: No trading

## Troubleshooting

### WebSocket Connection Issues
- Verify your internet connection
- Check Bybit API status
- Ensure testnet mode matches your API keys

### API Rate Limits
- Free tier APIs have rate limits
- Consider upgrading to paid tiers for production use
- The app implements automatic retry logic

### Missing Data
- DXY/BTC dominance update every hour
- News updates every 10 minutes
- Ensure API keys are valid

## License

This is a personal trading bot project. Use at your own risk.

## Disclaimer

This software is for educational purposes only. Trading cryptocurrencies carries significant risk. Never trade with money you cannot afford to lose.
#   T r a d i n g _ a l g V 2  
 