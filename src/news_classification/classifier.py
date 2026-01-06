import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.models import NewsItem
from .keywords import (
    MACRO_KEYWORDS,
    CRYPTO_KEYWORDS,
    SENTIMENT_KEYWORDS,
    IMPACT_KEYWORDS,
    BTC_ALIGNMENT_KEYWORDS
)

logger = logging.getLogger(__name__)


@dataclass
class NewsClassification:
    """Complete classification of a news item"""
    news_item: NewsItem
    categories: List[str]
    sentiment: str
    sentiment_score: float
    impact_level: str
    alignment: str
    macro_relevance: float
    crypto_relevance: float
    expires_at: datetime


class NewsClassifier:
    def __init__(self):
        self.classified_news: List[NewsClassification] = []
        self.max_history = 100

    def _score_keywords(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword match score for text"""
        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)
        return matches / len(keywords) if keywords else 0.0

    def _categorize_news(self, news_item: NewsItem) -> List[str]:
        """Categorize news into macro and crypto categories"""
        text = f"{news_item.title} {news_item.description or ''}"
        categories = []

        # Check macro categories
        for category, keywords in MACRO_KEYWORDS.items():
            score = self._score_keywords(text, keywords)
            if score > 0:
                categories.append(f"MACRO_{category}")

        # Check crypto categories
        for category, keywords in CRYPTO_KEYWORDS.items():
            score = self._score_keywords(text, keywords)
            if score > 0:
                categories.append(f"CRYPTO_{category}")

        return categories if categories else ["UNCATEGORIZED"]

    def _analyze_sentiment(self, news_item: NewsItem) -> Tuple[str, float]:
        """Analyze sentiment and return sentiment type and score"""
        text = f"{news_item.title} {news_item.description or ''}"

        positive_score = self._score_keywords(text, SENTIMENT_KEYWORDS["POSITIVE"])
        negative_score = self._score_keywords(text, SENTIMENT_KEYWORDS["NEGATIVE"])
        neutral_score = self._score_keywords(text, SENTIMENT_KEYWORDS["NEUTRAL"])

        # Determine dominant sentiment
        max_score = max(positive_score, negative_score, neutral_score)

        if max_score == 0:
            return "NEUTRAL", 0.0

        if positive_score == max_score:
            sentiment = "POSITIVE"
            score = positive_score - negative_score
        elif negative_score == max_score:
            sentiment = "NEGATIVE"
            score = -(negative_score - positive_score)
        else:
            sentiment = "NEUTRAL"
            score = 0.0

        # Normalize score to [-1, 1]
        score = max(-1.0, min(1.0, score * 2))

        return sentiment, score

    def _determine_impact(self, news_item: NewsItem, categories: List[str]) -> str:
        """Determine impact level of news"""
        text = f"{news_item.title} {news_item.description or ''}"

        # Check for high impact keywords
        high_score = self._score_keywords(text, IMPACT_KEYWORDS["HIGH"])
        if high_score > 0.1:
            return "HIGH"

        # Check for medium impact keywords
        medium_score = self._score_keywords(text, IMPACT_KEYWORDS["MEDIUM"])
        if medium_score > 0.05:
            return "MEDIUM"

        # Check category-based impact
        high_impact_categories = [
            "MACRO_MONETARY_POLICY", "MACRO_RISK_OFF",
            "CRYPTO_REGULATORY", "CRYPTO_EXCHANGE"
        ]

        for category in categories:
            if category in high_impact_categories:
                return "MEDIUM"

        return "LOW"

    def _detect_alignment(self, news_item: NewsItem, categories: List[str]) -> str:
        """Detect BTC market alignment type"""
        text = f"{news_item.title} {news_item.description or ''}"

        # Check for explicit alignment keywords
        aligned_score = self._score_keywords(text, BTC_ALIGNMENT_KEYWORDS["ALIGNED"])
        decoupled_score = self._score_keywords(text, BTC_ALIGNMENT_KEYWORDS["DECOUPLED"])
        btc_specific_score = self._score_keywords(text, BTC_ALIGNMENT_KEYWORDS["BTC_SPECIFIC"])

        # BTC-specific news suggests decoupling
        if btc_specific_score > 0.05:
            return "DECOUPLED"

        # Explicit decoupling mentioned
        if decoupled_score > aligned_score:
            return "DECOUPLED"

        # Macro-heavy news suggests alignment
        macro_categories = [cat for cat in categories if cat.startswith("MACRO_")]
        crypto_categories = [cat for cat in categories if cat.startswith("CRYPTO_")]

        if len(macro_categories) > len(crypto_categories):
            return "ALIGNED"

        # Crypto-specific suggests decoupling
        if len(crypto_categories) > len(macro_categories):
            return "DECOUPLED"

        # Default to aligned for risk events
        if "MACRO_RISK_OFF" in categories or "MACRO_RISK_ON" in categories:
            return "ALIGNED"

        return "NEUTRAL"

    def _calculate_relevance(self, categories: List[str]) -> Tuple[float, float]:
        """Calculate macro and crypto relevance scores"""
        macro_score = sum(1 for cat in categories if cat.startswith("MACRO_")) / 4
        crypto_score = sum(1 for cat in categories if cat.startswith("CRYPTO_")) / 5

        return min(1.0, macro_score), min(1.0, crypto_score)

    def _calculate_expiry(self, impact_level: str) -> datetime:
        """Calculate when this news classification expires"""
        from src.config import NEWS_IMPACT_WINDOWS

        hours = NEWS_IMPACT_WINDOWS.get(impact_level, 1)
        return datetime.now() + timedelta(hours=hours)

    def classify(self, news_item: NewsItem) -> NewsClassification:
        """Classify a news item completely"""
        # Categorize
        categories = self._categorize_news(news_item)

        # Analyze sentiment
        sentiment, sentiment_score = self._analyze_sentiment(news_item)

        # Determine impact
        impact_level = self._determine_impact(news_item, categories)

        # Detect alignment
        alignment = self._detect_alignment(news_item, categories)

        # Calculate relevance
        macro_relevance, crypto_relevance = self._calculate_relevance(categories)

        # Calculate expiry
        expires_at = self._calculate_expiry(impact_level)

        classification = NewsClassification(
            news_item=news_item,
            categories=categories,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            impact_level=impact_level,
            alignment=alignment,
            macro_relevance=macro_relevance,
            crypto_relevance=crypto_relevance,
            expires_at=expires_at
        )

        # Update news item with classification
        news_item.sentiment_score = sentiment_score
        news_item.impact_level = impact_level
        news_item.category = ", ".join(categories[:3])

        # Store classification
        self.classified_news.append(classification)
        self._cleanup_old_news()

        logger.info(
            f"Classified: {news_item.title[:50]}... | "
            f"Sentiment: {sentiment} ({sentiment_score:.2f}) | "
            f"Impact: {impact_level} | "
            f"Alignment: {alignment}"
        )

        return classification

    def _cleanup_old_news(self):
        """Remove expired news classifications"""
        now = datetime.now()
        self.classified_news = [
            nc for nc in self.classified_news
            if nc.expires_at > now
        ]

        # Keep max history
        if len(self.classified_news) > self.max_history:
            self.classified_news = self.classified_news[-self.max_history:]

    def get_active_news(self) -> List[NewsClassification]:
        """Get all active (non-expired) news classifications"""
        now = datetime.now()
        return [nc for nc in self.classified_news if nc.expires_at > now]

    def get_regime_signals(self) -> Dict[str, any]:
        """Extract regime signals from active news"""
        active = self.get_active_news()

        if not active:
            return {
                "news_count": 0,
                "avg_sentiment": 0.0,
                "risk_signal": "NEUTRAL",
                "alignment": "NEUTRAL",
                "high_impact_count": 0
            }

        # Calculate aggregate sentiment
        avg_sentiment = sum(nc.sentiment_score for nc in active) / len(active)

        # Count risk signals
        risk_off_count = sum(
            1 for nc in active
            if "MACRO_RISK_OFF" in nc.categories
        )
        risk_on_count = sum(
            1 for nc in active
            if "MACRO_RISK_ON" in nc.categories
        )

        # Determine risk signal
        if risk_off_count > risk_on_count:
            risk_signal = "RISK_OFF"
        elif risk_on_count > risk_off_count:
            risk_signal = "RISK_ON"
        else:
            risk_signal = "NEUTRAL"

        # Determine alignment
        aligned_count = sum(1 for nc in active if nc.alignment == "ALIGNED")
        decoupled_count = sum(1 for nc in active if nc.alignment == "DECOUPLED")

        if aligned_count > decoupled_count:
            alignment = "ALIGNED"
        elif decoupled_count > aligned_count:
            alignment = "DECOUPLED"
        else:
            alignment = "NEUTRAL"

        # Count high impact news
        high_impact_count = sum(1 for nc in active if nc.impact_level == "HIGH")

        return {
            "news_count": len(active),
            "avg_sentiment": avg_sentiment,
            "risk_signal": risk_signal,
            "alignment": alignment,
            "high_impact_count": high_impact_count,
            "risk_off_count": risk_off_count,
            "risk_on_count": risk_on_count
        }

    def get_latest_classifications(self, limit: int = 10) -> List[NewsClassification]:
        """Get most recent news classifications"""
        sorted_news = sorted(
            self.classified_news,
            key=lambda nc: nc.news_item.timestamp,
            reverse=True
        )
        return sorted_news[:limit]
