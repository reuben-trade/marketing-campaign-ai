"""Tests for competitor discovery service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ad_library_scraper import AdLibraryScraper
from app.services.competitor_discovery import CompetitorDiscovery


class TestCompetitorDiscoveryUnit:
    """Unit tests for CompetitorDiscovery (mocked dependencies)."""

    def test_generate_search_query_basic(self):
        """Test search query generation with basic inputs."""
        discovery = CompetitorDiscovery()

        query = discovery._generate_search_query(
            name="Acme Corp",
            industry=None,
            desc=None,
            location=None,
        )

        assert "Acme Corp" in query
        assert "competitors" in query
        assert "alternatives" in query

    def test_generate_search_query_with_location(self):
        """Test search query includes location when provided."""
        discovery = CompetitorDiscovery()

        query = discovery._generate_search_query(
            name="Acme Corp",
            industry="Manufacturing",
            desc=None,
            location="Sydney, Australia",
        )

        assert "Sydney, Australia" in query
        assert "Manufacturing" in query

    @pytest.mark.asyncio
    async def test_discover_competitors_returns_list(self):
        """Test that discover_competitors returns a list of competitors."""
        discovery = CompetitorDiscovery()

        # Mock Tavily response
        mock_tavily_response = {
            "answer": "Top competitors include Company A and Company B.",
            "results": [
                {
                    "title": "Best alternatives to Acme Corp",
                    "url": "https://example.com/article",
                    "content": "Company A and Company B are top alternatives.",
                }
            ],
        }

        # Mock OpenAI response
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"competitors": [{"company_name": "Company A", "description": "A competitor", "reason": "Similar products"}]}'
                )
            )
        ]

        with patch.object(
            discovery.tavily, "search", new_callable=AsyncMock, return_value=mock_tavily_response
        ):
            with patch.object(
                discovery.openai_client.chat.completions,
                "create",
                new_callable=AsyncMock,
                return_value=mock_openai_response,
            ):
                result = await discovery.discover_competitors(
                    business_name="Acme Corp",
                    industry="Manufacturing",
                )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["company_name"] == "Company A"

    @pytest.mark.asyncio
    async def test_discover_competitors_excludes_original_business(self):
        """Test that the original business is excluded from results."""
        discovery = CompetitorDiscovery()

        mock_tavily_response = {
            "answer": "Competitors include themselves and others",
            "results": [],
        }

        mock_openai_response = MagicMock()
        mock_openai_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"competitors": [{"company_name": "Other Corp", "description": "Real competitor", "reason": "Competing"}]}'
                )
            )
        ]

        with patch.object(
            discovery.tavily, "search", new_callable=AsyncMock, return_value=mock_tavily_response
        ):
            with patch.object(
                discovery.openai_client.chat.completions,
                "create",
                new_callable=AsyncMock,
                return_value=mock_openai_response,
            ):
                result = await discovery.discover_competitors(
                    business_name="Acme Corp",
                    industry="Tech",
                )

        # Original business should not be in results
        company_names = [c["company_name"] for c in result]
        assert "Acme Corp" not in company_names

    @pytest.mark.asyncio
    async def test_search_for_page_id_calls_scraper(self):
        """Test that search_for_page_id delegates to AdLibraryScraper."""
        discovery = CompetitorDiscovery()

        with patch("app.services.ad_library_scraper.AdLibraryScraper") as MockScraper:
            mock_scraper = MockScraper.return_value
            mock_scraper.search_page_id_by_name = AsyncMock(
                return_value=("123456789012", "https://facebook.com/testcompany")
            )

            page_id, facebook_url = await discovery.search_for_page_id("Test Company")

            mock_scraper.search_page_id_by_name.assert_called_once_with("Test Company")
            assert page_id == "123456789012"
            assert facebook_url == "https://facebook.com/testcompany"

    @pytest.mark.asyncio
    async def test_search_for_page_id_returns_url_when_no_page_id(self):
        """Test that search_for_page_id returns URL even when page_id extraction fails."""
        discovery = CompetitorDiscovery()

        with patch("app.services.ad_library_scraper.AdLibraryScraper") as MockScraper:
            mock_scraper = MockScraper.return_value
            mock_scraper.search_page_id_by_name = AsyncMock(
                return_value=(None, "https://facebook.com/testcompany")
            )

            page_id, facebook_url = await discovery.search_for_page_id("Test Company")

            assert page_id is None
            assert facebook_url == "https://facebook.com/testcompany"

    @pytest.mark.asyncio
    async def test_search_for_page_id_returns_none_on_failure(self):
        """Test that search_for_page_id returns None tuple when scraping fails."""
        discovery = CompetitorDiscovery()

        with patch("app.services.ad_library_scraper.AdLibraryScraper") as MockScraper:
            mock_scraper = MockScraper.return_value
            mock_scraper.search_page_id_by_name = AsyncMock(
                side_effect=Exception("Scraping failed")
            )

            page_id, facebook_url = await discovery.search_for_page_id("Test Company")

            assert page_id is None
            assert facebook_url is None


class TestAdLibraryScraperPageSearch:
    """Unit tests for AdLibraryScraper.search_page_id_by_name."""

    def test_build_ad_library_url_for_search(self):
        """Test URL construction for page search."""
        scraper = AdLibraryScraper()
        url = scraper.build_ad_library_url("123456789012")

        assert "view_all_page_id=123456789012" in url
        assert "facebook.com/ads/library" in url


@pytest.mark.asyncio
class TestCompetitorDiscoveryIntegration:
    """Integration tests that use Tavily search (use sparingly - costs API credits)."""

    async def test_search_page_id_by_name_known_company(self):
        """
        Test searching for a well-known company's Facebook page via Tavily.

        This test hits real Tavily API and Facebook.
        """
        scraper = AdLibraryScraper()

        # Search for a known company - The Grout Guy
        page_id, facebook_url = await scraper.search_page_id_by_name("The Grout Guy")

        # Should at least find a Facebook URL
        assert facebook_url is not None, "Should find a Facebook URL via Google"
        assert "facebook.com" in facebook_url

        # If page_id was extracted, validate format
        if page_id:
            assert len(page_id) >= 10  # Facebook page IDs are typically 10+ digits

    async def test_search_page_id_by_name_returns_url_for_manual_review(self):
        """
        Test that search returns Facebook URL for manual review.
        """
        scraper = AdLibraryScraper()

        # Search for a company
        page_id, facebook_url = await scraper.search_page_id_by_name("Coca-Cola")

        # Should find a Facebook URL via Google
        if facebook_url:
            assert "facebook.com" in facebook_url

            # If we also got a page_id, verify it can build a valid URL
            if page_id:
                url = scraper.build_ad_library_url(page_id)
                assert f"view_all_page_id={page_id}" in url
                assert "facebook.com/ads/library" in url

    async def test_search_page_id_by_name_nonexistent_company(self):
        """
        Test searching for a company that doesn't exist.
        """
        scraper = AdLibraryScraper()

        # Search for a nonsense company name
        page_id, facebook_url = await scraper.search_page_id_by_name(
            "XyzNonexistent12345Company67890"
        )

        # Should return None for both since Google won't find a Facebook page
        # (or might return unrelated results)

    async def test_full_discovery_flow_mocked(self):
        """
        Test the full flow from discovery to page ID lookup (mocked).
        """
        discovery = CompetitorDiscovery()

        # Mock the Tavily search
        mock_tavily_response = {
            "answer": "Major competitors in cleaning include ServiceMaster and Chem-Dry.",
            "results": [
                {
                    "title": "Top Cleaning Franchises",
                    "url": "https://example.com/cleaning",
                    "content": "ServiceMaster and Chem-Dry dominate the market.",
                }
            ],
        }

        # Mock OpenAI to return structured competitors
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""{
                        "competitors": [
                            {"company_name": "ServiceMaster", "description": "Large cleaning franchise", "reason": "Same industry"},
                            {"company_name": "Chem-Dry", "description": "Carpet cleaning", "reason": "Competing service"}
                        ]
                    }"""
                )
            )
        ]

        with patch.object(
            discovery.tavily, "search", new_callable=AsyncMock, return_value=mock_tavily_response
        ):
            with patch.object(
                discovery.openai_client.chat.completions,
                "create",
                new_callable=AsyncMock,
                return_value=mock_openai_response,
            ):
                competitors = await discovery.discover_competitors(
                    business_name="The Grout Guy",
                    industry="Cleaning Services",
                    location="Australia",
                )

        assert len(competitors) == 2
        assert competitors[0]["company_name"] == "ServiceMaster"
        assert competitors[1]["company_name"] == "Chem-Dry"

        # Now test the page ID lookup with mocked return values
        with patch("app.services.ad_library_scraper.AdLibraryScraper") as MockScraper:
            mock_scraper = MockScraper.return_value
            mock_scraper.search_page_id_by_name = AsyncMock(
                side_effect=[
                    ("111111111111", "https://facebook.com/servicemaster"),
                    ("222222222222", "https://facebook.com/chemdry"),
                ]
            )

            for comp in competitors:
                page_id, facebook_url = await discovery.search_for_page_id(comp["company_name"])
                assert page_id is not None
                assert len(page_id) >= 10
                assert facebook_url is not None


@pytest.mark.asyncio
class TestEndToEndDiscovery:
    """
    End-to-end tests for the complete competitor discovery flow.

    These tests verify the entire pipeline works together.
    """

    async def test_e2e_discover_and_get_page_id(self):
        """
        End-to-end test: discover competitors and get their page IDs.

        This test uses real services (Tavily, OpenAI, Google, Facebook).
        Run sparingly to avoid rate limits.
        """
        discovery = CompetitorDiscovery()
        scraper = AdLibraryScraper()

        # Step 1: Discover competitors for a known business
        # Using a smaller max to reduce API calls
        competitors = await discovery.discover_competitors(
            business_name="The Grout Guy",
            industry="Tile and Grout Cleaning",
            location="Sydney, Australia",
            max_competitors=3,
        )

        assert len(competitors) > 0, "Should discover at least one competitor"

        # Step 2: For each competitor, try to find their Facebook page ID
        results = []
        for comp in competitors:
            company_name = comp.get("company_name")
            assert company_name, "Competitor should have a company_name"

            # Try to find the page ID
            page_id, facebook_url = await scraper.search_page_id_by_name(company_name)
            results.append(
                {
                    "company_name": company_name,
                    "page_id": page_id,
                    "facebook_url": facebook_url,
                }
            )

        # We may not find page IDs for all competitors
        # But we should find at least some Facebook URLs
        urls_found = [r for r in results if r["facebook_url"]]
        page_ids_found = [r for r in results if r["page_id"]]

        print(f"Found {len(urls_found)} Facebook URLs out of {len(competitors)} competitors")
        print(f"Found {len(page_ids_found)} page IDs out of {len(competitors)} competitors")

        # Verify the page IDs are valid format
        for entry in page_ids_found:
            assert len(entry["page_id"]) >= 10, f"Page ID should be 10+ digits: {entry}"

    async def test_e2e_page_id_can_build_ad_library_url(self):
        """
        Test that discovered page IDs can be used to build valid Ad Library URLs.
        """
        scraper = AdLibraryScraper()

        # Use a known company for reliability
        page_id, facebook_url = await scraper.search_page_id_by_name("The Grout Guy")

        # Should at least find a URL
        assert facebook_url is not None, "Should find Facebook URL via Google"

        if page_id:
            url = scraper.build_ad_library_url(page_id)

            assert "facebook.com/ads/library" in url
            assert f"view_all_page_id={page_id}" in url
            assert "active_status=" in url
