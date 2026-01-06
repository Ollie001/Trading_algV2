"""
DXY Fetcher - Updated to use Yahoo Finance (free, no API key needed)
Falls back to EUR/USD inverse as DXY proxy
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
import httpx
import asyncio

from src.config import settings
from src.models import DXYData

logger = logging.getLogger(__name__)


class DXYFetcher:
    """
    Fetches US Dollar Index (DXY) data
    Primary: Alpha Vantage (more reliable, requires API key)
    Fallback: Yahoo Finance (free, no API key)
    """
    def __init__(self):
        self.alpha_vantage_api_key = settings.alpha_vantage_api_key
        self.alpha_vantage_base_url = "https://www.alphavantage.co/query"

        # Yahoo Finance fallback
        self.yahoo_base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
        self.symbol = "DX-Y.NYB"  # Yahoo Finance symbol for DXY futures

        self.max_retries = 3
        self.base_delay = 2  # Base delay in seconds for exponential backoff

    async def _retry_request(self, client: httpx.AsyncClient, url: str, params: dict, max_retries: int = 3):
        """
        Make HTTP request with exponential backoff retry logic
        """
        for attempt in range(max_retries):
            try:
                # Add a small delay before request to avoid rate limiting
                if attempt > 0:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(delay)

                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        delay = self.base_delay * (2 ** (attempt + 1))
                        logger.warning(f"Rate limited (429). Waiting {delay}s before retry...")
                        await asyncio.sleep(delay)
                        continue
                raise
            except httpx.HTTPError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
                    continue
                raise

        raise Exception(f"Failed after {max_retries} retries")

    async def _get_alpha_vantage_dxy(self) -> Optional[DXYData]:
        """
        Get DXY approximation from Alpha Vantage using EUR/USD
        DXY is heavily weighted by EUR, so we use EUR/USD inverse as proxy
        Formula: DXY ≈ 120 / EURUSD
        """
        if not self.alpha_vantage_api_key:
            logger.debug("Alpha Vantage API key not configured, skipping...")
            return None

        params = {
            "function": "FX_DAILY",
            "from_symbol": "EUR",
            "to_symbol": "USD",
            "apikey": self.alpha_vantage_api_key,
            "outputsize": "compact"  # Last 100 data points
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await self._retry_request(
                    client,
                    self.alpha_vantage_base_url,
                    params,
                    self.max_retries
                )
                data = response.json()

                # Check for API error
                if "Error Message" in data:
                    logger.error(f"Alpha Vantage error: {data['Error Message']}")
                    return None

                if "Note" in data:
                    logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                    return None

                time_series = data.get("Time Series FX (Daily)", {})
                if not time_series:
                    logger.error("No forex data returned from Alpha Vantage")
                    return None

                # Get most recent two days for change calculation
                sorted_dates = sorted(time_series.keys(), reverse=True)
                if len(sorted_dates) < 1:
                    logger.error("Insufficient data from Alpha Vantage")
                    return None

                latest_date = sorted_dates[0]
                latest_data = time_series[latest_date]
                current_eurusd = float(latest_data.get("4. close", 0))

                if current_eurusd == 0:
                    logger.error("Invalid EUR/USD value from Alpha Vantage")
                    return None

                # Convert EUR/USD to DXY approximation
                dxy_value = 120 / current_eurusd

                # Calculate change if we have previous day
                change_percent = None
                if len(sorted_dates) >= 2:
                    prev_date = sorted_dates[1]
                    prev_data = time_series[prev_date]
                    prev_eurusd = float(prev_data.get("4. close", 0))
                    if prev_eurusd > 0:
                        prev_dxy = 120 / prev_eurusd
                        change_percent = ((dxy_value - prev_dxy) / prev_dxy) * 100

                dxy_data = DXYData(
                    timestamp=datetime.now(),
                    value=float(dxy_value),
                    change_percent=change_percent,
                    source="alpha_vantage"
                )

                logger.info(f"DXY (Alpha Vantage) updated: {dxy_value:.2f} (change: {change_percent:.2f}%)")
                return dxy_data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching from Alpha Vantage: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage: {e}")
            return None

    async def get_current_value(self) -> Optional[DXYData]:
        """
        Get current DXY value
        Priority: Alpha Vantage -> Yahoo Finance -> EUR/USD proxy
        """
        # Try Alpha Vantage first (most reliable if API key is configured)
        if self.alpha_vantage_api_key:
            alpha_data = await self._get_alpha_vantage_dxy()
            if alpha_data:
                return alpha_data
            logger.warning("Alpha Vantage failed, falling back to Yahoo Finance...")

        # Try Yahoo Finance
        url = f"{self.yahoo_base_url}/{self.symbol}"

        params = {
            "interval": "1d",
            "range": "5d"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await self._retry_request(client, url, params, self.max_retries)
                data = response.json()

                chart = data.get("chart", {})
                result = chart.get("result", [])

                if not result:
                    logger.error("No data returned from Yahoo Finance for DXY")
                    return await self._get_eurusd_proxy()

                quote = result[0].get("meta", {})
                indicators = result[0].get("indicators", {}).get("quote", [{}])[0]

                # Get latest close price
                close_prices = indicators.get("close", [])
                if not close_prices or not any(close_prices):
                    return await self._get_eurusd_proxy()

                # Get last non-null close price
                current_close = None
                previous_close = None
                for price in reversed(close_prices):
                    if price is not None:
                        if current_close is None:
                            current_close = price
                        elif previous_close is None:
                            previous_close = price
                            break

                if current_close is None:
                    return await self._get_eurusd_proxy()

                # Calculate change
                change_percent = None
                if previous_close:
                    change_percent = ((current_close - previous_close) / previous_close) * 100

                dxy_data = DXYData(
                    timestamp=datetime.now(),
                    value=float(current_close),
                    change_percent=change_percent,
                    source="yahoo_finance"
                )

                logger.info(f"DXY updated: {dxy_data.value:.2f} (change: {change_percent:.2f}%)")
                return dxy_data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching DXY from Yahoo: {e}")
            return await self._get_eurusd_proxy()
        except Exception as e:
            logger.error(f"Error fetching DXY from Yahoo: {e}")
            return await self._get_eurusd_proxy()

    async def _get_eurusd_proxy(self) -> Optional[DXYData]:
        """
        Fallback: Use EUR/USD inverse as DXY proxy
        DXY and EUR/USD are highly negatively correlated
        Approximate DXY = 100 / EUR/USD
        """
        url = f"{self.yahoo_base_url}/EURUSD=X"

        params = {
            "interval": "1d",
            "range": "5d"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await self._retry_request(client, url, params, self.max_retries)
                data = response.json()

                result = data.get("chart", {}).get("result", [])
                if not result:
                    logger.error("Failed to get EUR/USD proxy data")
                    return None

                indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
                close_prices = indicators.get("close", [])

                if not close_prices:
                    return None

                # Get last non-null prices
                current_close = None
                previous_close = None
                for price in reversed(close_prices):
                    if price is not None:
                        if current_close is None:
                            current_close = price
                        elif previous_close is None:
                            previous_close = price
                            break

                if not current_close:
                    return None

                # Convert EUR/USD to DXY approximation
                # Typical DXY range: 90-110, EUR/USD range: 1.05-1.20
                # Approximate conversion: DXY ≈ 120 / EURUSD
                dxy_approx = 120 / current_close

                change_percent = None
                if previous_close:
                    prev_dxy = 120 / previous_close
                    change_percent = ((dxy_approx - prev_dxy) / prev_dxy) * 100

                dxy_data = DXYData(
                    timestamp=datetime.now(),
                    value=float(dxy_approx),
                    change_percent=change_percent,
                    source="eurusd_proxy"
                )

                logger.info(f"DXY (EUR/USD proxy) updated: {dxy_data.value:.2f}")
                return dxy_data

        except Exception as e:
            logger.error(f"Error fetching EUR/USD proxy: {e}")
            return None

    async def get_time_series(
        self,
        interval: str = "4h",
        outputsize: int = 24
    ) -> List[DXYData]:
        """Get historical DXY time series"""
        url = f"{self.yahoo_base_url}/{self.symbol}"

        params = {
            "interval": "1h" if interval in ["1h", "4h"] else "1d",
            "range": "1mo"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await self._retry_request(client, url, params, self.max_retries)
                data = response.json()

                result = data.get("chart", {}).get("result", [])
                if not result:
                    return []

                timestamps = result[0].get("timestamp", [])
                indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
                close_prices = indicators.get("close", [])

                dxy_series = []
                for i, (ts, close) in enumerate(zip(timestamps, close_prices)):
                    if close is None:
                        continue

                    change_percent = None
                    if i > 0 and close_prices[i-1] is not None:
                        prev_close = close_prices[i-1]
                        change_percent = ((close - prev_close) / prev_close) * 100

                    dxy_data = DXYData(
                        timestamp=datetime.fromtimestamp(ts),
                        value=float(close),
                        change_percent=change_percent,
                        source="yahoo_finance"
                    )
                    dxy_series.append(dxy_data)

                return dxy_series[-outputsize:]

        except Exception as e:
            logger.error(f"Error fetching DXY time series: {e}")
            return []

    async def get_eod(self, days: int = 30) -> List[DXYData]:
        """Get end-of-day DXY data"""
        return await self.get_time_series(interval="1d", outputsize=days)
