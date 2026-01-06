import hashlib
import hmac
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from src.config import settings, Timeframe
from src.models import OHLCV, FundingRate

logger = logging.getLogger(__name__)


class BybitRESTClient:
    def __init__(self):
        self.base_url = settings.bybit_rest_url
        self.api_key = settings.bybit_api_key
        self.api_secret = settings.bybit_api_secret
        self.recv_window = 5000

    def _generate_signature(self, params: str, timestamp: int) -> str:
        param_str = f"{timestamp}{self.api_key}{self.recv_window}{params}"
        signature = hmac.new(
            bytes(self.api_secret, "utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_headers(self, params: str = "") -> Dict[str, str]:
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(params, timestamp)

        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-RECV-WINDOW": str(self.recv_window),
            "Content-Type": "application/json"
        }

    async def get_klines(
        self,
        symbol: str,
        interval: Timeframe,
        limit: int = 200,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[OHLCV]:
        endpoint = "/v5/market/kline"
        url = f"{self.base_url}{endpoint}"

        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval.value,
            "limit": limit
        }

        if start_time:
            params["start"] = start_time
        if end_time:
            params["end"] = end_time

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("retCode") != 0:
                    logger.error(f"API error: {data.get('retMsg')}")
                    return []

                klines = []
                for item in data.get("result", {}).get("list", []):
                    kline = OHLCV(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(int(item[0]) / 1000),
                        open=float(item[1]),
                        high=float(item[2]),
                        low=float(item[3]),
                        close=float(item[4]),
                        volume=float(item[5]),
                        timeframe=interval.value
                    )
                    klines.append(kline)

                klines.reverse()
                return klines

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching klines: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return []

    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        endpoint = "/v5/market/funding/history"
        url = f"{self.base_url}{endpoint}"

        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": 1
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("retCode") != 0:
                    logger.error(f"API error: {data.get('retMsg')}")
                    return None

                items = data.get("result", {}).get("list", [])
                if not items:
                    return None

                item = items[0]
                funding_rate = FundingRate(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(int(item["fundingRateTimestamp"]) / 1000),
                    funding_rate=float(item["fundingRate"]),
                    next_funding_time=datetime.fromtimestamp(
                        int(item["fundingRateTimestamp"]) / 1000 + 8 * 3600
                    )
                )

                return funding_rate

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching funding rate: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 25) -> Optional[Dict]:
        endpoint = "/v5/market/orderbook"
        url = f"{self.base_url}{endpoint}"

        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": limit
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("retCode") != 0:
                    logger.error(f"API error: {data.get('retMsg')}")
                    return None

                return data.get("result", {})

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching orderbook: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None

    async def get_tickers(self, symbol: str) -> Optional[Dict]:
        endpoint = "/v5/market/tickers"
        url = f"{self.base_url}{endpoint}"

        params = {
            "category": "linear",
            "symbol": symbol
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("retCode") != 0:
                    logger.error(f"API error: {data.get('retMsg')}")
                    return None

                items = data.get("result", {}).get("list", [])
                return items[0] if items else None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching tickers: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return None

    async def get_server_time(self) -> Optional[int]:
        endpoint = "/v5/market/time"
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                if data.get("retCode") != 0:
                    logger.error(f"API error: {data.get('retMsg')}")
                    return None

                return int(data.get("result", {}).get("timeSecond", 0))

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching server time: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching server time: {e}")
            return None
