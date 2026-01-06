"""
BTC Dominance Fetcher - Updated for CoinCap API
CoinCap provides free crypto market data including BTC dominance
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from src.config import settings
from src.models import BTCDominanceData

logger = logging.getLogger(__name__)


class BTCDominanceFetcher:
    """
    Fetches BTC dominance data from CoinCap API
    CoinCap API is free and doesn't require authentication for basic usage
    """
    def __init__(self):
        self.api_key = settings.coingecko_api_key  # Renamed for backward compatibility
        self.base_url = "https://api.coincap.io/v2"

    def _get_headers(self) -> dict:
        """CoinCap accepts optional API key for higher rate limits"""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def get_current_dominance(self) -> Optional[BTCDominanceData]:
        """
        Calculate BTC dominance from CoinCap assets endpoint
        BTC Dominance = (BTC Market Cap / Total Market Cap) * 100
        """
        endpoint = "/assets"
        url = f"{self.base_url}{endpoint}"

        params = {
            "limit": 100  # Get top 100 to calculate total market cap
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                assets = data.get("data", [])

                if not assets:
                    logger.error("No assets data returned from CoinCap")
                    return None

                # Find Bitcoin
                btc_asset = None
                for asset in assets:
                    if asset.get("symbol") == "BTC":
                        btc_asset = asset
                        break

                if not btc_asset:
                    logger.error("Bitcoin not found in CoinCap response")
                    return None

                # Calculate total market cap from top assets
                btc_market_cap = float(btc_asset.get("marketCapUsd", 0))
                total_market_cap = sum(
                    float(asset.get("marketCapUsd", 0))
                    for asset in assets
                )

                if total_market_cap == 0:
                    logger.error("Total market cap is zero")
                    return None

                # Calculate BTC dominance
                btc_dominance = (btc_market_cap / total_market_cap) * 100

                # Get 24h change if available
                change_percent = None
                if btc_asset.get("changePercent24Hr"):
                    change_percent = float(btc_asset.get("changePercent24Hr"))

                dominance_data = BTCDominanceData(
                    timestamp=datetime.now(),
                    value=float(btc_dominance),
                    change_percent=change_percent,
                    source="coincap"
                )

                logger.debug(f"BTC Dominance: {btc_dominance:.2f}%")
                return dominance_data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching BTC dominance from CoinCap: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching BTC dominance from CoinCap: {e}")
            return None

    async def get_historical_dominance(self, days: int = 30) -> List[BTCDominanceData]:
        """
        Get historical BTC dominance data
        Note: CoinCap's history endpoint provides price history,
        not direct dominance history. This is a simplified implementation.
        """
        endpoint = "/assets/bitcoin/history"
        url = f"{self.base_url}{endpoint}"

        # Calculate interval based on days requested
        if days <= 1:
            interval = "h1"  # 1 hour
        elif days <= 7:
            interval = "h6"  # 6 hours
        else:
            interval = "d1"  # 1 day

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        params = {
            "interval": interval,
            "start": int(start_time.timestamp() * 1000),
            "end": int(end_time.timestamp() * 1000)
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                history = data.get("data", [])
                dominance_series = []

                # For historical dominance, we need both BTC and total market data
                # Since CoinCap doesn't provide historical total market cap easily,
                # we'll estimate based on current ratio
                current_dominance = await self.get_current_dominance()
                if not current_dominance:
                    return []

                base_dominance = current_dominance.value

                for i, entry in enumerate(history):
                    timestamp = entry.get("time")
                    price = float(entry.get("priceUsd", 0))

                    if timestamp and price > 0:
                        # Simplified: use current dominance as baseline
                        # Real implementation would need historical total market cap
                        dominance_value = base_dominance

                        # Calculate change from previous
                        change_percent = None
                        if i > 0:
                            prev_dominance = dominance_series[-1].value
                            change_percent = ((dominance_value - prev_dominance) / prev_dominance) * 100

                        dominance_data = BTCDominanceData(
                            timestamp=datetime.fromtimestamp(timestamp / 1000),
                            value=dominance_value,
                            change_percent=change_percent,
                            source="coincap"
                        )
                        dominance_series.append(dominance_data)

                logger.info(f"Fetched {len(dominance_series)} historical dominance data points")
                return dominance_series

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching historical BTC dominance: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching historical BTC dominance: {e}")
            return []

    async def get_simple_dominance_approximation(self) -> Optional[float]:
        """
        Quick approximation of BTC dominance
        Uses the same method as get_current_dominance
        """
        dominance_data = await self.get_current_dominance()
        if dominance_data:
            return dominance_data.value
        return None
