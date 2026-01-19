"""SQLAlchemy models."""

from app.models.ad import Ad
from app.models.ad_creative_analysis import AdCreativeAnalysis
from app.models.analysis_run import AnalysisRun
from app.models.business_strategy import BusinessStrategy
from app.models.competitor import Competitor
from app.models.cross_platform_ad import CrossPlatformAd
from app.models.landing_page import LandingPage
from app.models.recommendation import Recommendation

__all__ = [
    "Ad",
    "AdCreativeAnalysis",
    "AnalysisRun",
    "BusinessStrategy",
    "Competitor",
    "CrossPlatformAd",
    "LandingPage",
    "Recommendation",
]
