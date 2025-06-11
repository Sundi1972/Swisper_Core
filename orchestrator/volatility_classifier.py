"""Volatility classification module for intent detection."""
from typing import Literal, Dict, Any
from swisper_core import get_logger

logger = get_logger(__name__)

VolatilityLevel = Literal["static", "semi_static", "volatile", "unknown"]

DEFAULT_VOLATILITY_KEYWORDS = {
    "volatile_keywords": [
        "latest", "current", "recent", "today", "now", "currently", "breaking", "news",
        "2025", "2024", "ministers", "government", "cabinet", "officials", "CEO",
        "president", "price", "stock", "exchange rate", "developments", "events",
        "updates", "who is the", "chief executive", "director", "chairman", "leader",
        "head of", "prime minister"
    ],
    "semi_static_keywords": [
        "specs", "specifications", "features", "iPhone", "model", "version", "release",
        "company", "headquarters", "founded", "employees", "established"
    ],
    "static_keywords": [
        "history", "biography", "born", "died", "capital", "population", "geography",
        "definition", "explain", "what is", "how does", "theory", "concept",
        "mathematics", "who was", "historical", "ancient", "classical", "traditional",
        "fundamental"
    ]
}

def get_volatility_settings() -> Dict[str, Any]:
    """Get volatility keyword settings - for now return defaults, later integrate with settings API."""
    return DEFAULT_VOLATILITY_KEYWORDS


def classify_entity_category(text: str) -> Dict[str, Any]:
    """Classify text based on volatility keywords."""
    lower = text.lower()
    settings = get_volatility_settings()

    logger.info("Classifying volatility for: '%s'", text)

    score = {
        "volatile": any(kw in lower for kw in settings["volatile_keywords"]),
        "semi_static": any(kw in lower for kw in settings["semi_static_keywords"]),
        "static": any(kw in lower for kw in settings["static_keywords"]),
    }

    if score["volatile"]:
        result = {"volatility": "volatile", "reason": "Matched volatile keywords"}
    elif score["semi_static"]:
        result = {"volatility": "semi_static", "reason": "Matched semi-static keywords"}
    elif score["static"]:
        result = {"volatility": "static", "reason": "Matched static keywords"}
    else:
        result = {"volatility": "unknown", "reason": "No keyword match"}

    logger.info("Volatility classification result: %s", result)
    return result
