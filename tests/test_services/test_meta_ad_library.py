"""Tests for Meta Ad Library service."""

import pytest

from app.services.meta_ad_library import MetaAdLibraryClient


class TestMetaAdLibraryClient:
    """Tests for MetaAdLibraryClient."""

    def test_extract_page_id_from_url_view_all(self):
        """Test extracting page ID from view_all_page_id URL."""
        client = MetaAdLibraryClient()
        url = "https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=123456789"

        page_id = client._extract_page_id_from_url(url)

        assert page_id == "123456789"

    def test_extract_page_id_from_url_id_param(self):
        """Test extracting page ID from id parameter."""
        client = MetaAdLibraryClient()
        url = "https://www.facebook.com/ads/library/?id=987654321"

        page_id = client._extract_page_id_from_url(url)

        assert page_id == "987654321"

    def test_extract_page_id_from_invalid_url(self):
        """Test extracting page ID from invalid URL."""
        client = MetaAdLibraryClient()
        url = "https://www.facebook.com/some/other/page"

        page_id = client._extract_page_id_from_url(url)

        assert page_id is None

    def test_parse_ad_data(self):
        """Test parsing raw ad data."""
        client = MetaAdLibraryClient()
        raw_ad = {
            "id": "ad_123",
            "ad_creative_bodies": ["This is the ad body"],
            "ad_creative_link_captions": ["Shop Now"],
            "ad_creative_link_descriptions": ["Great product description"],
            "ad_creative_link_titles": ["Amazing Product"],
            "ad_delivery_start_time": "2024-01-15T00:00:00Z",
            "ad_snapshot_url": "https://facebook.com/ads/snapshot/123",
            "page_id": "page_456",
            "page_name": "Test Company",
            "publisher_platforms": ["facebook", "instagram"],
            "languages": ["en"],
        }

        parsed = client.parse_ad_data(raw_ad)

        assert parsed["ad_library_id"] == "ad_123"
        assert parsed["ad_copy"] == "This is the ad body"
        assert parsed["ad_headline"] == "Amazing Product"
        assert parsed["cta_text"] == "Shop Now"
        assert parsed["page_name"] == "Test Company"

    def test_parse_ad_data_empty_fields(self):
        """Test parsing ad data with empty fields."""
        client = MetaAdLibraryClient()
        raw_ad = {
            "id": "ad_123",
            "ad_creative_bodies": [],
            "ad_creative_link_captions": [],
            "ad_creative_link_descriptions": [],
            "ad_creative_link_titles": [],
        }

        parsed = client.parse_ad_data(raw_ad)

        assert parsed["ad_library_id"] == "ad_123"
        assert parsed["ad_copy"] is None
        assert parsed["ad_headline"] is None
        assert parsed["cta_text"] is None
