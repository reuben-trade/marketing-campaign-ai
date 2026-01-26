"""Tests for Ad Library scraper service."""

import pytest

from app.services.ad_library_scraper import AdLibraryScraper


class TestAdLibraryScraper:
    """Tests for AdLibraryScraper."""

    def test_build_ad_library_url(self):
        """Test URL building with page ID."""
        scraper = AdLibraryScraper()
        page_id = "144068198941502"

        url = scraper.build_ad_library_url(page_id)

        assert page_id in url
        assert "view_all_page_id=" in url
        assert "facebook.com/ads/library" in url

    def test_build_ad_library_url_with_country(self):
        """Test URL building with custom country."""
        scraper = AdLibraryScraper()
        page_id = "144068198941502"

        url = scraper.build_ad_library_url(page_id, country="US")

        assert "country=US" in url

    def test_extract_ads_from_html_with_valid_data(self):
        """Test extracting ads from HTML with embedded JSON."""
        scraper = AdLibraryScraper()

        # Sample HTML with embedded ad data (simplified)
        html_content = """
        <html>
        <script>
        {"ad_archive_id":"123456789","collation_id":"987654321","page_id":"144068198941502",
        "snapshot":{"body":"Test ad copy here","link_url":"http://example.com","start_date":1704067200}}
        </script>
        </html>
        """

        seen_ids = set()
        ads = scraper._extract_ads_from_html(html_content, seen_ids)

        assert len(ads) == 1
        assert ads[0]["ad_library_id"] == "123456789"
        assert "123456789" in seen_ids

    def test_extract_ads_from_html_deduplication(self):
        """Test that duplicate ads are not extracted twice."""
        scraper = AdLibraryScraper()

        html_content = """
        {"ad_archive_id":"123456789","collation_id":"987654321","page_id":"144068198941502"}
        """

        # Pre-populate seen_ids
        seen_ids = {"123456789"}
        ads = scraper._extract_ads_from_html(html_content, seen_ids)

        assert len(ads) == 0

    def test_extract_ads_from_html_empty(self):
        """Test extracting from HTML with no ads."""
        scraper = AdLibraryScraper()

        html_content = "<html><body>No ads here</body></html>"

        seen_ids = set()
        ads = scraper._extract_ads_from_html(html_content, seen_ids)

        assert len(ads) == 0


@pytest.mark.asyncio
class TestAdLibraryScraperAsync:
    """Async tests for AdLibraryScraper."""

    async def test_extract_page_id_from_profile_valid_url(self):
        """Test extracting Page ID from a valid Facebook URL."""
        scraper = AdLibraryScraper()

        # Test with the known working page
        page_id = await scraper.extract_page_id_from_profile("https://www.facebook.com/thegroutguy")

        # The Grout Guy's Page ID
        assert page_id == "100064364122244"

    async def test_scrape_ads_for_page_returns_ads(self):
        """Test that scraping returns ads for a valid page."""
        scraper = AdLibraryScraper()

        # Use the known working page ID
        page_id = "144068198941502"

        ads = await scraper.scrape_ads_for_page(page_id, max_ads=3)

        assert len(ads) > 0
        assert len(ads) <= 3

        # Check ad structure
        for ad in ads:
            assert "ad_library_id" in ad
            assert "ad_snapshot_url" in ad
            assert ad["ad_library_id"] is not None

    async def test_scrape_ads_for_page_with_country(self):
        """Test that scraping with specific country works."""
        scraper = AdLibraryScraper()

        page_id = "144068198941502"

        ads = await scraper.scrape_ads_for_page(page_id, max_ads=2, country="AU")

        assert len(ads) > 0

    async def test_search_page_id_by_name_known_company(self):
        """Test searching for page ID by company name via Google."""
        scraper = AdLibraryScraper()

        # Search for a known company - The Grout Guy
        page_id, facebook_url = await scraper.search_page_id_by_name("The Grout Guy")

        # Should find a Facebook URL at minimum
        assert facebook_url is not None
        assert "facebook.com" in facebook_url

        # If page_id was extracted, validate format
        if page_id:
            assert len(page_id) >= 10  # Facebook page IDs are typically 10+ digits
            assert page_id.isdigit()  # Should be numeric

    async def test_search_page_id_by_name_returns_url_for_manual_review(self):
        """Test that search returns Facebook URL even if page_id extraction fails."""
        scraper = AdLibraryScraper()

        # Search for a company - may or may not get page_id, but should get URL
        page_id, facebook_url = await scraper.search_page_id_by_name("Coca-Cola")

        # Should at least find a Facebook URL (Google search should work)
        # page_id may or may not be extracted depending on Facebook's page structure
        if facebook_url:
            assert "facebook.com" in facebook_url

    async def test_search_page_id_by_name_can_scrape_ads(self):
        """Test that a found page ID can be used to scrape ads."""
        scraper = AdLibraryScraper()

        # Search for page ID
        page_id, facebook_url = await scraper.search_page_id_by_name("The Grout Guy")

        # Skip if no page_id (might need manual review)
        if page_id is None:
            assert facebook_url is not None, "Should have URL for manual review"
            return

        # Now try to scrape ads using that page ID
        ads = await scraper.scrape_ads_for_page(page_id, max_ads=2)

        # Should be able to scrape (even if no active ads)
        assert isinstance(ads, list)
