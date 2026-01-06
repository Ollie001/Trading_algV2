# Quick Start Guide

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Environment

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your API keys:
   - **Bybit** (Required): Get from [Bybit API Management](https://www.bybit.com/app/user/api-management)
   - **Twelve Data** (Optional): Get from [Twelve Data](https://twelvedata.com/pricing)
   - **CoinGecko** (Optional): Works without key (free tier)
   - **NewsAPI** (Optional): Get from [NewsAPI](https://newsapi.org/register)

### Minimal Configuration

For initial testing, you only need Bybit API credentials:

```env
BYBIT_API_KEY=your_key_here
BYBIT_API_SECRET=your_secret_here
BYBIT_TESTNET=true
```

## Step 3: Test the Modules

Run the test script to verify everything works:

```bash
python test_modules.py
```

Expected output:
- Bybit server time
- Recent klines (candlestick data)
- Funding rate
- DXY value (if API key configured)
- BTC dominance (always works)
- Recent news (if API key configured)

## Step 4: Start the Application

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 5: Access the Dashboard

Open your browser to: [http://localhost:8000/ui](http://localhost:8000/ui)

You should see:
- Real-time BTC trades
- Latest 5-minute candle
- DXY value (if configured)
- BTC dominance percentage
- Latest crypto news (if configured)

## Step 6: Explore the API

Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

Try these endpoints:
- `GET /health` - Check system health
- `GET /api/status` - Full system status
- `GET /api/market/latest-trade` - Latest BTC trade
- `GET /api/market/klines?symbol=BTCUSDT&interval=5&limit=10` - Historical data

## Troubleshooting

### "No API key configured"
- Make sure your `.env` file exists
- Verify API keys are correctly copied (no extra spaces)
- Restart the application after editing `.env`

### "WebSocket connection failed"
- Check internet connection
- Verify Bybit API key permissions include "Read" access
- Make sure `BYBIT_TESTNET` matches your API key type

### "No data available"
- Wait 30-60 seconds for initial data to stream
- Check `/health` endpoint to see component status
- Review console logs for errors

### API Rate Limits
- Free tier APIs have limits (e.g., NewsAPI: 100 requests/day)
- DXY updates hourly to conserve API calls
- News polls every 10 minutes by default

## What's Working

✅ **Module 1: Config & Constants**
- Environment-based configuration
- Risk parameters
- Timeframe definitions
- Regime state definitions

✅ **Module 2: Data Ingestion**
- Real-time Bybit WebSocket (orderbook, trades, klines)
- Bybit REST API (historical data)
- DXY macro indicator
- BTC dominance tracking
- News feed integration

## Next Steps

The foundation is ready for:
- Module 3: News sentiment classification
- Module 4: Regime detection engine
- Module 5: Capital flow analyzer
- Module 6: Liquidity engine
- Module 7: Execution logic
- Modules 8-9: Risk and trade management

## Need Help?

Check the logs in your console for detailed error messages. Most issues are related to:
1. Missing or invalid API keys
2. Network connectivity
3. API rate limits

For development, set `DEBUG=true` in `.env` for more verbose logging.
