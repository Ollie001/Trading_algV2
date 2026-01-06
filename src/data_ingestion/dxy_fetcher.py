import logging
from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from src.config import settings
from src.models import DXYData

logger = logging.getLogger(__name__)


class DXYFetcher:
    def __init__(self):
        self.api_key = settings.twelve_data_api_key
        self.base_url = "https://api.twelvedata.com"
        self.symbol = "DXY"

    async def get_current_value(self) -> Optional[DXYData]:
        endpoint = "/quote"
        url = f"{self.base_url}{endpoint}"

        params = {
            "symbol": self.symbol,
            "apikey": self.api_key
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                if "code" in data and data["code"] != 200:
                    logger.error(f"API error: {data.get('message', 'Unknown error')}")
                    return None

                dxy_data = DXYData(
                    timestamp=datetime.now(),
                    value=float(data.get("close", 0)),
                    change_percent=float(data.get("percent_change", 0)),
                    source="twelve_data"
                )

                return dxy_data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching DXY: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching DXY: {e}")
            return None

    async def get_time_series(
        self,
        interval: str = "4h",
        outputsize: int = 24
    ) -> List[DXYData]:
        endpoint = "/time_series"
        url = f"{self.base_url}{endpoint}"

        params = {
            "symbol": self.symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self.api_key
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                if "code" in data and data["code"] != 200:
                    logger.error(f"API error: {data.get('message', 'Unknown error')}")
                    return []

                values = data.get("values", [])
                dxy_series = []

                for i, item in enumerate(values):
                    prev_close = float(values[i + 1]["close"]) if i + 1 < len(values) else None
                    current_close = float(item["close"])

                    change_percent = None
                    if prev_close:
                        change_percent = ((current_close - prev_close) / prev_close) * 100

                    dxy_data = DXYData(
                        timestamp=datetime.fromisoformat(item["datetime"]),
                        value=current_close,
                        change_percent=change_percent,
                        source="twelve_data"
                    )
                    dxy_series.append(dxy_data)

                dxy_series.reverse()
                return dxy_series

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching DXY time series: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching DXY time series: {e}")
            return []

    async def get_eod(self, days: int = 30) -> List[DXYData]:
        endpoint = "/eod"
        url = f"{self.base_url}{endpoint}"

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        params = {
            "symbol": self.symbol,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "apikey": self.api_key
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                if "code" in data and data["code"] != 200:
                    logger.error(f"API error: {data.get('message', 'Unknown error')}")
                    return []

                values = data.get("values", [])
                dxy_series = []

                for i, item in enumerate(values):
                    prev_close = float(values[i + 1]["close"]) if i + 1 < len(values) else None
                    current_close = float(item["close"])

                    change_percent = None
                    if prev_close:
                        change_percent = ((current_close - prev_close) / prev_close) * 100

                    dxy_data = DXYData(
                        timestamp=datetime.fromisoformat(item["datetime"]),
                        value=current_close,
                        change_percent=change_percent,
                        source="twelve_data"
                    )
                    dxy_series.append(dxy_data)

                dxy_series.reverse()
                return dxy_series

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching DXY EOD: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching DXY EOD: {e}")
            return []
