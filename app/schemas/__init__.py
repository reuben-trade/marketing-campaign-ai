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
from app.schemas.ad_creative_analysis import (
    AdCreativeAnalysisCreate,
    AdCreativeAnalysisResponse,
    AdCreativeAnalysisSummary,
    ArchetypeDistribution,
    CreativeAnalysisRequest,
    CreativeDiversityReport,
    OfferDistribution,
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
from app.schemas.cross_platform_ad import (
    CrossPlatformAdCreate,
    CrossPlatformAdResponse,
    CrossPlatformAdSummary,
    CrossPlatformSearchRequest,
    CrossPlatformSearchResponse,
    TechnicalSophisticationLeaderboard,
    TechnicalSophisticationRanking,
    UniversalWinnerReport,
)
from app.schemas.landing_page import (
    CTAButton,
    HeadingsContent,
    LandingPageCreate,
    LandingPageResponse,
    LandingPageScrapeRequest,
    LandingPageSummary,
    TrackingPixelInfo,
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
    # Ad Creative Analysis
    "AdCreativeAnalysisCreate",
    "AdCreativeAnalysisResponse",
    "AdCreativeAnalysisSummary",
    "ArchetypeDistribution",
    "CreativeAnalysisRequest",
    "CreativeDiversityReport",
    "OfferDistribution",
    # Landing Page
    "CTAButton",
    "HeadingsContent",
    "LandingPageCreate",
    "LandingPageResponse",
    "LandingPageScrapeRequest",
    "LandingPageSummary",
    "TrackingPixelInfo",
    # Cross-Platform Ad
    "CrossPlatformAdCreate",
    "CrossPlatformAdResponse",
    "CrossPlatformAdSummary",
    "CrossPlatformSearchRequest",
    "CrossPlatformSearchResponse",
    "TechnicalSophisticationLeaderboard",
    "TechnicalSophisticationRanking",
    "UniversalWinnerReport",
    # Recommendation
    "RecommendationCreate",
    "RecommendationListResponse",
    "RecommendationResponse",
    "TrendAnalysis",
]
