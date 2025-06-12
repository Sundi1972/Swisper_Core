"""Temporal cue detection module for intent classification."""
from typing import Dict, Any
from swisper_core import get_logger

logger = get_logger(__name__)


def has_temporal_cue(text: str) -> bool:
    """Detect temporal cues indicating time-sensitive information needs."""
    temporal_keywords = [
        "today", "now", "currently", "latest", "new", "as of", "2025", "2024",
        "recent", "current", "breaking", "this year", "this month", "right now"
    ]

    lower_text = text.lower()
    detected_cues = [kw for kw in temporal_keywords if kw in lower_text]

    has_cue = len(detected_cues) > 0
    logger.info("Temporal cue detection for '%s': %s (detected: %s)", text, has_cue, detected_cues)

    return has_cue


def extract_temporal_context(text: str) -> Dict[str, Any]:
    """Extract temporal context information from text."""
    temporal_indicators = [
        "today", "now", "currently", "latest", "new", "as of", "2025", "2024",
        "recent", "current", "breaking"
    ]
    return {
        "has_temporal_cue": has_temporal_cue(text),
        "temporal_indicators": [kw for kw in temporal_indicators if kw in text.lower()]
    }
