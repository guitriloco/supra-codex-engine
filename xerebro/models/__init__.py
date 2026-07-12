"""
Xerebro AI — Request/Response Models

Typed data models for Xerebro brain interactions.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ReasoningTask(str, Enum):
    """Types of reasoning tasks the brain can perform."""
    SCRAPE_STRATEGY = "scrape_strategy"
    DATA_EXTRACTION = "data_extraction"
    DATA_ENRICHMENT = "data_enrichment"
    CONTENT_CLASSIFICATION = "content_classification"
    PIPELINE_DECISION = "pipeline_decision"
    CUSTOM = "custom"


@dataclass
class ScrapeStrategy:
    """LLM-recommended scraping strategy."""
    url: str
    selectors: Dict[str, str] = field(default_factory=dict)
    pagination: Optional[str] = None
    rate_limit_delay_ms: int = 1000
    user_agent: str = "Supra-Codex-Engine/0.1.0"
    notes: str = ""


@dataclass
class EnrichmentResult:
    """LLM-enriched data output."""
    original: Dict[str, Any]
    enriched: Dict[str, Any]
    confidence: float = 0.0
    source: str = "xerebro"