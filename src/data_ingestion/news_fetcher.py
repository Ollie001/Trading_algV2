"""
News Fetcher - Updated for NewsData.io API
NewsData.io provides news aggregation from multiple sources
"""

import logging
from typing import List, Optional, Callable
from datetime import datetime, timedelta
import asyncio
import httpx
import hashlib

from src.config import settings
from src.models import NewsItem

logger = logging.getLogger(__name__)


class NewsFetcher:
    """
    Fetches news from NewsData.io API
    Free tier: 200 requests/day
    """
    def __init__(self):
        self.api_key = settings.news_api_key
        self.base_url = "https://newsdata.io/api/1"
        self.crypto_keywords = [
            "bitcoin", "BTC", "cryptocurrency", "crypto", "blockchain",
            "federal reserve", "fed", "interest rate", "inflation", "USD"
        ]
        self.news_callback: Optional[Callable] = None
        self.is_running = False
        self.seen_articles = set()
        self.poll_interval = 600  # 10 minutes (to stay within free tier limits)

    def on_news(self, callback: Callable):
        """Register callback for new articles"""
        self.news_callback = callback

    def _generate_article_id(self, title: str, published_at: str) -> str:
        """Generate unique ID for article deduplication"""
        unique_string = f"{title}{published_at}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    async def fetch_latest_news(
        self,
        query: Optional[str] = None,
        language: str = "en",
        page_size: int = 10
    ) -> List[NewsItem]:
        """
        Fetch latest news from NewsData.io
        Note: Free tier limited to 10 results per request
        """
        endpoint = "/news"
        url = f"{self.base_url}{endpoint}"

        # Build search query
        if not query:
            # Use crypto and macro keywords
            query = " OR ".join(self.crypto_keywords[:3])  # Limit to avoid query too long

        params = {
            "apikey": self.api_key,
            "q": query,
            "language": language,
            "size": min(page_size, 10),  # Free tier max is 10
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()

                # Check for API errors
                if data.get("status") == "error":
                    error_msg = data.get("results", {}).get("message", "Unknown error")
                    logger.error(f"NewsData.io API error: {error_msg}")
                    return []

                results = data.get("results", [])
                news_items = []

                for article in results:
                    # NewsData.io format
                    published_at = article.get("pubDate", "")
                    title = article.get("title", "")

                    article_id = self._generate_article_id(title, published_at)

                    # Parse timestamp
                    try:
                        if published_at:
                            # NewsData.io uses format: "2024-01-06 12:30:45"
                            timestamp = datetime.fromisoformat(published_at.replace(" ", "T"))
                        else:
                            timestamp = datetime.now()
                    except Exception:
                        timestamp = datetime.now()

                    news_item = NewsItem(
                        id=article_id,
                        timestamp=timestamp,
                        title=title,
                        description=article.get("description") or article.get("content"),
                        source=article.get("source_id", "Unknown"),
                        url=article.get("link"),
                        category=None,  # Will be set by classifier
                        sentiment_score=None,  # Will be set by classifier
                        impact_level="LOW"  # Will be set by classifier
                    )
                    news_items.append(news_item)

                logger.info(f"Fetched {len(news_items)} news items from NewsData.io")
                return news_items

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("NewsData.io rate limit exceeded - waiting before retry")
            else:
                logger.error(f"HTTP error fetching news: {e}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching news: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    async def fetch_crypto_news(self, page_size: int = 10) -> List[NewsItem]:
        """
        Fetch crypto-specific news
        """
        endpoint = "/news"
        url = f"{self.base_url}{endpoint}"

        params = {
            "apikey": self.api_key,
            "q": "bitcoin OR cryptocurrency OR crypto",
            "language": "en",
            "category": "technology,business",
            "size": min(page_size, 10),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "error":
                    logger.error(f"API error: {data.get('results', {})}")
                    return []

                results = data.get("results", [])
                news_items = []

                for article in results:
                    published_at = article.get("pubDate", "")
                    title = article.get("title", "")
                    article_id = self._generate_article_id(title, published_at)

                    try:
                        timestamp = datetime.fromisoformat(published_at.replace(" ", "T"))
                    except Exception:
                        timestamp = datetime.now()

                    news_item = NewsItem(
                        id=article_id,
                        timestamp=timestamp,
                        title=title,
                        description=article.get("description") or article.get("content"),
                        source=article.get("source_id", "Unknown"),
                        url=article.get("link"),
                        category="crypto",
                        sentiment_score=None,
                        impact_level="MEDIUM"
                    )
                    news_items.append(news_item)

                return news_items

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching crypto news: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching crypto news: {e}")
            return []

    async def fetch_top_headlines(
        self,
        category: str = "business",
        country: str = "us",
        page_size: int = 10
    ) -> List[NewsItem]:
        """
        Fetch top headlines by category
        NewsData.io supports: business, technology, politics, etc.
        """
        endpoint = "/news"
        url = f"{self.base_url}{endpoint}"

        params = {
            "apikey": self.api_key,
            "country": country,
            "category": category,
            "language": "en",
            "size": min(page_size, 10),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "error":
                    logger.error(f"API error: {data.get('results', {})}")
                    return []

                results = data.get("results", [])
                news_items = []

                for article in results:
                    published_at = article.get("pubDate", "")
                    title = article.get("title", "")
                    article_id = self._generate_article_id(title, published_at)

                    try:
                        timestamp = datetime.fromisoformat(published_at.replace(" ", "T"))
                    except Exception:
                        timestamp = datetime.now()

                    news_item = NewsItem(
                        id=article_id,
                        timestamp=timestamp,
                        title=title,
                        description=article.get("description") or article.get("content"),
                        source=article.get("source_id", "Unknown"),
                        url=article.get("link"),
                        category=category,
                        sentiment_score=None,
                        impact_level="MEDIUM"
                    )
                    news_items.append(news_item)

                return news_items

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching headlines: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching headlines: {e}")
            return []

    async def start_polling(self, interval: int = 600):
        """
        Start polling for news
        Default: 600s (10 minutes) to stay within free tier limits (200 req/day)
        """
        self.is_running = True
        self.poll_interval = interval

        logger.info(f"Starting news polling (interval: {interval}s)")

        while self.is_running:
            try:
                news_items = await self.fetch_latest_news()

                # Process new articles
                for item in news_items:
                    if item.id not in self.seen_articles:
                        self.seen_articles.add(item.id)

                        if self.news_callback:
                            await self.news_callback(item)

                # Cleanup old seen articles (keep last 1000)
                if len(self.seen_articles) > 1000:
                    self.seen_articles = set(list(self.seen_articles)[-1000:])

                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in news polling loop: {e}")
                await asyncio.sleep(self.poll_interval)

    def stop_polling(self):
        """Stop the news polling loop"""
        self.is_running = False
        logger.info("Stopping news polling")

    async def search_news(
        self,
        keywords: List[str],
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[NewsItem]:
        """
        Search news by keywords and date range
        Note: NewsData.io free tier doesn't support date range filtering
        """
        query = " OR ".join(keywords[:3])  # Limit to avoid too long query

        endpoint = "/news"
        url = f"{self.base_url}{endpoint}"

        params = {
            "apikey": self.api_key,
            "q": query,
            "language": "en",
            "size": 10,
        }

        # Note: from_date and to_date ignored in free tier
        if from_date or to_date:
            logger.warning("NewsData.io free tier doesn't support date filtering")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "error":
                    logger.error(f"API error: {data.get('results', {})}")
                    return []

                results = data.get("results", [])
                news_items = []

                for article in results:
                    published_at = article.get("pubDate", "")
                    title = article.get("title", "")
                    article_id = self._generate_article_id(title, published_at)

                    try:
                        timestamp = datetime.fromisoformat(published_at.replace(" ", "T"))
                    except Exception:
                        timestamp = datetime.now()

                    news_item = NewsItem(
                        id=article_id,
                        timestamp=timestamp,
                        title=title,
                        description=article.get("description") or article.get("content"),
                        source=article.get("source_id", "Unknown"),
                        url=article.get("link"),
                        category=None,
                        sentiment_score=None,
                        impact_level="LOW"
                    )
                    news_items.append(news_item)

                return news_items

        except httpx.HTTPError as e:
            logger.error(f"HTTP error searching news: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching news: {e}")
            return []
