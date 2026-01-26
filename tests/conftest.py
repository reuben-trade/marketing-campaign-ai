"""Test configuration and fixtures."""

# =============================================================================
# SQLite Type Adapters for PostgreSQL-specific types
# =============================================================================
# IMPORTANT: These MUST be registered BEFORE any app imports to ensure
# the type compilers are in place when SQLAlchemy metadata is created.
#
# This allows tests to use SQLite in-memory database while the models use
# PostgreSQL-specific types (JSONB, ARRAY, pgvector Vector).

from sqlalchemy import ARRAY as SQL_ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


# Map JSONB to JSON for SQLite
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# Map PostgreSQL ARRAY to JSON for SQLite (store as JSON array)
@compiles(PG_ARRAY, "sqlite")
def compile_pg_array_sqlite(type_, compiler, **kw):
    return "JSON"


# Map base SQLAlchemy ARRAY to JSON for SQLite (some models use sqlalchemy.ARRAY)
@compiles(SQL_ARRAY, "sqlite")
def compile_sql_array_sqlite(type_, compiler, **kw):
    return "JSON"


# Map pgvector's Vector type to TEXT for SQLite
try:
    from pgvector.sqlalchemy import Vector

    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(type_, compiler, **kw):
        return "TEXT"
except ImportError:
    pass  # pgvector not installed


# =============================================================================
# Standard imports (AFTER type adapters are registered)
# =============================================================================
# ruff: noqa: E402 - Imports below must be after type adapter registration

import asyncio  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402
from typing import Generator  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create an async test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    from app.api.deps import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sync_client() -> Generator[TestClient, None, None]:
    """Create a synchronous test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch("openai.AsyncOpenAI") as mock:
        mock_instance = MagicMock()
        mock_instance.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"summary": "test", "insights": [], "uvps": [], "ctas": [], "visual_themes": [], "target_audience": "test", "emotional_appeal": "test", "marketing_effectiveness": {"hook_strength": 7, "message_clarity": 8, "visual_impact": 7, "cta_effectiveness": 8, "overall_score": 7}, "strategic_insights": "test", "reasoning": "test"}'
                        )
                    )
                ]
            )
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client."""
    with patch("anthropic.AsyncAnthropic") as mock:
        mock_instance = MagicMock()
        mock_instance.messages.create = AsyncMock(
            return_value=MagicMock(
                content=[
                    MagicMock(
                        text='{"executive_summary": "test", "trend_analysis": {}, "recommendations": [], "implementation_roadmap": {}}'
                    )
                ]
            )
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_supabase_storage():
    """Mock Supabase storage."""
    with patch("app.utils.supabase_storage.create_client") as mock:
        mock_client = MagicMock()
        mock_client.storage.from_.return_value.upload.return_value = None
        mock_client.storage.from_.return_value.download.return_value = b"test content"
        mock_client.storage.from_.return_value.get_public_url.return_value = "https://test.com/file"
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_ad_library_scraper():
    """Mock AdLibraryScraper to avoid Playwright dependency in tests."""
    with patch("app.api.competitors.AdLibraryScraper") as mock:
        mock_instance = MagicMock()

        # Mock extract_page_id_from_profile - extracts page ID from URL
        mock_instance.extract_page_id_from_profile = AsyncMock(return_value="123456789")

        # Mock search_page_id_by_name - searches for page by company name
        mock_instance.search_page_id_by_name = AsyncMock(
            return_value=("123456789", "https://facebook.com/testpage")
        )

        # Mock batch_search_page_ids - batch search for multiple companies
        async def batch_search_side_effect(company_names):
            return {name: (f"{hash(name) % 1000000000}", f"https://facebook.com/{name.lower().replace(' ', '')}") for name in company_names}

        mock_instance.batch_search_page_ids = AsyncMock(side_effect=batch_search_side_effect)

        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_business_strategy():
    """Sample business strategy data."""
    return {
        "business_name": "Test Company",
        "business_description": "A test company for unit testing",
        "industry": "Technology",
        "target_audience": {
            "demographics": "25-45 year old professionals",
            "psychographics": "Tech-savvy, early adopters",
            "pain_points": ["Time management", "Productivity"],
        },
        "brand_voice": {
            "tone": "Professional",
            "personality_traits": ["Innovative", "Trustworthy"],
            "messaging_guidelines": "Clear and concise",
        },
        "market_position": "challenger",
        "price_point": "mid-market",
        "business_life_stage": "growth",
        "unique_selling_points": ["Fast", "Reliable", "Easy to use"],
        "competitive_advantages": ["Best customer support"],
        "marketing_objectives": ["Increase brand awareness"],
    }


@pytest.fixture
def sample_competitor():
    """Sample competitor data for API requests.

    Note: The API derives page_id from facebook_url or company_name via AdLibraryScraper.
    Tests should use mock_ad_library_scraper fixture to avoid real scraper calls.
    """
    return {
        "company_name": "Competitor Inc",
        "facebook_url": "https://www.facebook.com/competitorinc",
        "industry": "Technology",
        "follower_count": 50000,
        "is_market_leader": True,
        "market_position": "leader",
    }


@pytest.fixture
def sample_ad_analysis():
    """Sample ad analysis data."""
    return {
        "summary": "Test ad summary",
        "insights": ["Insight 1", "Insight 2"],
        "uvps": ["UVP 1"],
        "ctas": ["Shop Now"],
        "visual_themes": ["Modern", "Clean"],
        "target_audience": "Young professionals",
        "emotional_appeal": "Aspiration",
        "marketing_effectiveness": {
            "hook_strength": 8,
            "message_clarity": 9,
            "visual_impact": 7,
            "cta_effectiveness": 8,
            "overall_score": 8,
        },
        "strategic_insights": "Uses problem-agitation-solution framework",
        "reasoning": "Strong hook with clear value proposition",
    }
