"""Application configuration using Pydantic Settings."""

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RecommendationModel(str, Enum):
    """Available models for generating recommendations."""

    CLAUDE = "claude"
    OPENAI = "openai"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database (Supabase)
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase service role key")
    database_url: str = Field(..., description="PostgreSQL connection string")

    # AI Services
    openai_api_key: str = Field(..., description="OpenAI API key")
    google_api_key: str = Field(..., description="Google AI (Gemini) API key")
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    tavily_api_key: str = Field(..., description="Tavily API key")

    # Meta Ad Library
    meta_access_token: str = Field(..., description="Meta Graph API access token")
    meta_app_id: str = Field(default="", description="Meta App ID")
    meta_app_secret: str = Field(default="", description="Meta App Secret")

    # Celery / Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # App Configuration
    recommendation_model: Literal["claude", "openai"] = Field(
        default="claude",
        description="Model to use for recommendations",
    )

    # Analysis Configuration
    top_n_ads_for_recommendations: int = Field(
        default=10,
        description="Number of top ads to analyze for recommendations",
    )
    ad_lookback_days: int = Field(
        default=90,
        description="Number of days to look back for ads",
    )
    max_ads_per_competitor: int = Field(
        default=100,
        description="Maximum ads to store per competitor",
    )
    min_engagement_threshold: int = Field(
        default=50,
        description="Minimum engagement (likes + comments + shares) to consider",
    )

    # Rate Limiting
    meta_rate_limit_per_hour: int = Field(
        default=200,
        description="Meta API rate limit per hour",
    )

    # Render Service
    render_callback_secret: str = Field(
        default="",
        description="Secret for authenticating render callback requests",
    )

    # Remotion Lambda (AWS)
    remotion_aws_region: str = Field(
        default="",
        description="AWS region for Remotion Lambda (if empty, uses local rendering)",
    )
    remotion_function_name: str = Field(
        default="",
        description="Name of the deployed Remotion Lambda function",
    )
    remotion_site_name: str = Field(
        default="",
        description="Name of the Remotion site (bundle) in S3",
    )
    remotion_serve_url: str = Field(
        default="",
        description="Full URL to the Remotion bundle (auto-generated if empty)",
    )
    aws_access_key_id: str = Field(
        default="",
        description="AWS access key ID for Remotion Lambda (uses default credentials if empty)",
    )
    aws_secret_access_key: str = Field(
        default="",
        description="AWS secret access key for Remotion Lambda (uses default credentials if empty)",
    )

    @property
    def remotion_lambda_enabled(self) -> bool:
        """Check if Remotion Lambda is configured."""
        return bool(self.remotion_aws_region and self.remotion_function_name)

    # Server Configuration
    port: int = Field(
        default=8000,
        description="Server port for uvicorn",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Server host for uvicorn",
    )

    # Supabase Storage Buckets
    ad_creatives_bucket: str = Field(
        default="ad-creatives",
        description="Bucket for storing ad creatives",
    )
    strategy_documents_bucket: str = Field(
        default="strategy-documents",
        description="Bucket for storing strategy PDFs",
    )
    supabase_screenshots_bucket: str = Field(
        default="screenshots",
        description="Bucket for storing landing page screenshots",
    )
    critique_files_bucket: str = Field(
        default="critique-files",
        description="Bucket for storing user-uploaded critique files (images and videos)",
    )
    user_uploads_bucket: str = Field(
        default="user-uploads",
        description="Bucket for storing user-uploaded project video files",
    )

    @property
    def meta_api_base_url(self) -> str:
        """Meta Graph API base URL."""
        return "https://graph.facebook.com/v18.0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
