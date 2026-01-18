"""Pydantic schemas for request/response validation."""

from app.schemas.ad import (
    AdAnalysis,
    AdCreate,
    AdListResponse,
    AdResponse,
    AdStats,
    MarketingEffectiveness,
    VideoAnalysis,
)
from app.schemas.business_strategy import (
    BrandVoice,
    BusinessStrategyCreate,
    BusinessStrategyResponse,
    BusinessStrategyUpdate,
    TargetAudience,
)
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorListResponse,
    CompetitorResponse,
    CompetitorUpdate,
)
from app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationListResponse,
    RecommendationResponse,
    TrendAnalysis,
)

__all__ = [
    # Business Strategy
    "BrandVoice",
    "BusinessStrategyCreate",
    "BusinessStrategyResponse",
    "BusinessStrategyUpdate",
    "TargetAudience",
    # Competitor
    "CompetitorCreate",
    "CompetitorListResponse",
    "CompetitorResponse",
    "CompetitorUpdate",
    # Ad
    "AdAnalysis",
    "AdCreate",
    "AdListResponse",
    "AdResponse",
    "AdStats",
    "MarketingEffectiveness",
    "VideoAnalysis",
    # Recommendation
    "RecommendationCreate",
    "RecommendationListResponse",
    "RecommendationResponse",
    "TrendAnalysis",
]
