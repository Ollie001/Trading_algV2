"""
Keyword dictionaries for news classification
"""

# Macro events that affect risk sentiment
MACRO_KEYWORDS = {
    "RISK_OFF": [
        "recession", "crisis", "crash", "collapse", "default", "bankruptcy",
        "war", "conflict", "tension", "sanctions", "invasion",
        "unemployment", "layoffs", "inflation surge", "rate hike",
        "emergency", "panic", "sell-off", "selloff", "plunge", "tumble",
        "fears", "concerns", "worried", "anxiety", "uncertainty",
        "tightening", "hawkish", "restrictive", "contagion",
        "bank failure", "liquidity crisis", "margin call"
    ],
    "RISK_ON": [
        "recovery", "growth", "stimulus", "easing", "rally", "surge",
        "bullish", "optimism", "confidence", "expansion", "boom",
        "rate cut", "dovish", "accommodative", "support", "positive",
        "breakthrough", "resolution", "agreement", "deal", "progress",
        "strong economy", "job growth", "earnings beat", "profit",
        "upgrade", "investment", "buying opportunity"
    ],
    "INFLATION": [
        "inflation", "CPI", "consumer price", "PCE", "price index",
        "cost of living", "purchasing power", "hyperinflation",
        "deflationary", "disinflation"
    ],
    "MONETARY_POLICY": [
        "federal reserve", "fed", "FOMC", "central bank", "ECB", "BOJ",
        "interest rate", "rate decision", "monetary policy", "quantitative easing",
        "QE", "QT", "quantitative tightening", "balance sheet",
        "Powell", "Yellen", "Lagarde"
    ]
}

# Crypto-specific events
CRYPTO_KEYWORDS = {
    "REGULATORY": [
        "SEC", "regulation", "lawsuit", "ban", "legal", "compliance",
        "Gensler", "regulatory", "crackdown", "enforcement", "probe",
        "investigation", "fine", "penalty", "settlement", "court"
    ],
    "ADOPTION": [
        "adoption", "institutional", "ETF", "approval", "accepted",
        "mainstream", "integration", "partnership", "payment",
        "legal tender", "reserve asset", "treasury", "corporate"
    ],
    "TECHNICAL": [
        "halving", "halvening", "upgrade", "fork", "network", "hash rate",
        "mining", "difficulty", "protocol", "blockchain", "scalability",
        "layer 2", "lightning network", "taproot", "segwit"
    ],
    "EXCHANGE": [
        "exchange", "Coinbase", "Binance", "FTX", "Kraken", "listing",
        "delisting", "trading volume", "liquidity", "outflow", "inflow",
        "wallet", "custody", "reserves", "proof of reserves"
    ],
    "DEFI": [
        "DeFi", "decentralized finance", "smart contract", "protocol",
        "yield", "staking", "lending", "TVL", "total value locked"
    ]
}

# Sentiment keywords
SENTIMENT_KEYWORDS = {
    "POSITIVE": [
        "bullish", "optimistic", "positive", "surge", "rally", "gain",
        "growth", "increase", "rise", "upward", "strong", "robust",
        "breakthrough", "success", "win", "profit", "beat", "outperform",
        "upgrade", "boost", "support", "confidence", "opportunity"
    ],
    "NEGATIVE": [
        "bearish", "pessimistic", "negative", "crash", "plunge", "fall",
        "decline", "decrease", "drop", "downward", "weak", "poor",
        "failure", "loss", "miss", "underperform", "downgrade",
        "concern", "worry", "fear", "risk", "threat", "crisis"
    ],
    "NEUTRAL": [
        "stable", "unchanged", "flat", "steady", "maintain", "hold",
        "sideways", "range-bound", "consolidate", "await", "watch"
    ]
}

# Impact level keywords
IMPACT_KEYWORDS = {
    "HIGH": [
        "breaking", "urgent", "major", "significant", "critical",
        "emergency", "federal reserve", "FOMC", "rate decision",
        "war", "crisis", "crash", "halving", "ETF approval",
        "regulation", "ban", "SEC lawsuit", "exchange hack",
        "default", "bankruptcy", "collapse"
    ],
    "MEDIUM": [
        "update", "announcement", "report", "data", "earnings",
        "inflation", "CPI", "GDP", "employment", "jobs",
        "upgrade", "partnership", "integration", "adoption",
        "institutional", "whale", "large transaction"
    ],
    "LOW": [
        "rumor", "speculation", "opinion", "analysis", "forecast",
        "prediction", "expects", "anticipates", "could", "may",
        "might", "suggests", "indicates"
    ]
}

# Bitcoin-specific alignment keywords
BTC_ALIGNMENT_KEYWORDS = {
    "ALIGNED": [
        "bitcoin follows", "correlated", "tracking", "mirroring",
        "risk asset", "tech stocks", "nasdaq", "equity", "stocks",
        "macro driven", "fed sensitive"
    ],
    "DECOUPLED": [
        "bitcoin decouples", "diverges", "independent", "safe haven",
        "digital gold", "alternative", "uncorrelated", "contrary",
        "opposite direction", "breaks correlation"
    ],
    "BTC_SPECIFIC": [
        "bitcoin only", "crypto specific", "blockchain", "mining",
        "halving", "on-chain", "whale", "exchange flow",
        "BTC dominance", "altcoin", "ordinals", "inscription"
    ]
}


def get_all_keywords():
    """Flatten all keywords for quick lookup"""
    all_keywords = set()

    for category_dict in [MACRO_KEYWORDS, CRYPTO_KEYWORDS, SENTIMENT_KEYWORDS,
                          IMPACT_KEYWORDS, BTC_ALIGNMENT_KEYWORDS]:
        for keyword_list in category_dict.values():
            all_keywords.update([k.lower() for k in keyword_list])

    return all_keywords
