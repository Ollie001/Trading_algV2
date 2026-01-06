import asyncio
import logging
from src.config import settings
from src.data_ingestion import (
    BybitRESTClient,
    DXYFetcher,
    BTCDominanceFetcher,
    NewsFetcher
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_bybit_rest():
    logger.info("Testing Bybit REST Client...")
    client = BybitRESTClient()

    server_time = await client.get_server_time()
    logger.info(f"Bybit Server Time: {server_time}")

    from src.config import Timeframe
    klines = await client.get_klines("BTCUSDT", Timeframe.FIVE_MINUTE, limit=5)
    if klines:
        logger.info(f"Fetched {len(klines)} klines")
        logger.info(f"Latest kline: Close=${klines[-1].close}")
    else:
        logger.warning("No klines fetched")

    funding = await client.get_funding_rate("BTCUSDT")
    if funding:
        logger.info(f"Funding Rate: {funding.funding_rate}")
    else:
        logger.warning("No funding rate fetched")


async def test_dxy():
    logger.info("\nTesting DXY Fetcher...")
    fetcher = DXYFetcher()

    if not settings.twelve_data_api_key:
        logger.warning("No Twelve Data API key configured, skipping DXY test")
        return

    current = await fetcher.get_current_value()
    if current:
        logger.info(f"DXY Current Value: {current.value}")
        logger.info(f"DXY Change: {current.change_percent}%")
    else:
        logger.warning("Failed to fetch DXY")


async def test_btc_dominance():
    logger.info("\nTesting BTC Dominance Fetcher...")
    fetcher = BTCDominanceFetcher()

    current = await fetcher.get_current_dominance()
    if current:
        logger.info(f"BTC Dominance: {current.value}%")
    else:
        logger.warning("Failed to fetch BTC dominance")


async def test_news():
    logger.info("\nTesting News Fetcher...")
    fetcher = NewsFetcher()

    if not settings.news_api_key:
        logger.warning("No News API key configured, skipping news test")
        return

    news_items = await fetcher.fetch_latest_news(page_size=5)
    if news_items:
        logger.info(f"Fetched {len(news_items)} news items")
        for item in news_items[:3]:
            logger.info(f"- {item.title} ({item.source})")
    else:
        logger.warning("No news items fetched")


async def main():
    logger.info("=" * 60)
    logger.info("Testing Module 1 & Module 2 Implementation")
    logger.info("=" * 60)

    logger.info("\nConfiguration loaded:")
    logger.info(f"- Bybit Testnet: {settings.bybit_testnet}")
    logger.info(f"- Bybit API Key configured: {bool(settings.bybit_api_key)}")
    logger.info(f"- Twelve Data API Key configured: {bool(settings.twelve_data_api_key)}")
    logger.info(f"- CoinGecko API Key configured: {bool(settings.coingecko_api_key)}")
    logger.info(f"- News API Key configured: {bool(settings.news_api_key)}")

    logger.info("\n" + "=" * 60)

    try:
        await test_bybit_rest()
    except Exception as e:
        logger.error(f"Bybit REST test failed: {e}")

    try:
        await test_dxy()
    except Exception as e:
        logger.error(f"DXY test failed: {e}")

    try:
        await test_btc_dominance()
    except Exception as e:
        logger.error(f"BTC Dominance test failed: {e}")

    try:
        await test_news()
    except Exception as e:
        logger.error(f"News test failed: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("Testing Complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
