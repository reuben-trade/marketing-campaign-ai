"""Meta Ad Library API integration."""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class MetaAdLibraryError(Exception):
    """Exception raised for Meta Ad Library API errors."""

    pass


class RateLimitError(MetaAdLibraryError):
    """Exception raised when rate limit is exceeded."""

    pass


class MetaAdLibraryClient:
    """Client for the Meta Ad Library API."""

    def __init__(self) -> None:
        """Initialize the Meta Ad Library client."""
        settings = get_settings()
        self.access_token = settings.meta_access_token
        self.base_url = settings.meta_api_base_url
        self.rate_limit = settings.meta_rate_limit_per_hour
        self._request_count = 0
        self._request_window_start = datetime.utcnow()

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        now = datetime.utcnow()
        window_elapsed = (now - self._request_window_start).total_seconds()

        if window_elapsed >= 3600:
            self._request_count = 0
            self._request_window_start = now
        elif self._request_count >= self.rate_limit:
            wait_time = 3600 - window_elapsed
            logger.warning(f"Rate limit reached, waiting {wait_time:.0f} seconds")
            raise RateLimitError(f"Rate limit exceeded. Wait {wait_time:.0f} seconds.")

        self._request_count += 1

    def _extract_page_id_from_url(self, ad_library_url: str) -> str | None:
        """
        Extract page ID from a Meta Ad Library URL.

        Supports formats:
        - https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id=123456789
        - https://www.facebook.com/ads/library/?id=123456789
        """
        try:
            parsed = urlparse(ad_library_url)
            params = parse_qs(parsed.query)

            if "view_all_page_id" in params:
                return params["view_all_page_id"][0]
            if "id" in params:
                return params["id"][0]

            match = re.search(r"page[_-]?id[=:](\d+)", ad_library_url, re.IGNORECASE)
            if match:
                return match.group(1)

            return None
        except Exception as e:
            logger.error(f"Failed to extract page ID from URL: {e}")
            return None

    async def get_ads_for_page(
        self,
        page_id: str,
        since_date: datetime | None = None,
        limit: int = 100,
        ad_active_status: str = "ALL",
    ) -> list[dict[str, Any]]:
        """
        Retrieve ads from Meta Ad Library for a specific page.

        Args:
            page_id: Facebook Page ID
            since_date: Only get ads published after this date
            limit: Maximum number of ads to retrieve
            ad_active_status: "ACTIVE", "INACTIVE", or "ALL"

        Returns:
            List of ad data dictionaries
        """
        await self._check_rate_limit()

        params = {
            "access_token": self.access_token,
            "search_page_ids": page_id,
            "ad_reached_countries": "ALL",
            "ad_active_status": ad_active_status,
            "fields": ",".join(
                [
                    "id",
                    "ad_creative_bodies",
                    "ad_creative_link_captions",
                    "ad_creative_link_descriptions",
                    "ad_creative_link_titles",
                    "ad_delivery_start_time",
                    "ad_delivery_stop_time",
                    "ad_snapshot_url",
                    "page_id",
                    "page_name",
                    "publisher_platforms",
                    "languages",
                ]
            ),
            "limit": min(limit, 100),
        }

        if since_date:
            params["ad_delivery_date_min"] = since_date.strftime("%Y-%m-%d")

        all_ads = []
        url = f"{self.base_url}/ads_archive"

        async with httpx.AsyncClient(timeout=60) as client:
            while url and len(all_ads) < limit:
                try:
                    response = await client.get(url, params=params if url.endswith("/ads_archive") else None)
                    response.raise_for_status()
                    data = response.json()

                    if "error" in data:
                        error_msg = data["error"].get("message", "Unknown error")
                        raise MetaAdLibraryError(f"API error: {error_msg}")

                    ads = data.get("data", [])
                    all_ads.extend(ads)

                    paging = data.get("paging", {})
                    url = paging.get("next")
                    params = None

                    if url:
                        await self._check_rate_limit()

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        raise RateLimitError("Rate limit exceeded") from e
                    raise MetaAdLibraryError(f"HTTP error: {e}") from e

        return all_ads[:limit]

    async def get_ads_for_competitor(
        self,
        ad_library_url: str,
        since_date: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get ads for a competitor using their Ad Library URL.

        Args:
            ad_library_url: Meta Ad Library URL for the competitor
            since_date: Only get ads published after this date
            limit: Maximum number of ads to retrieve

        Returns:
            List of ad data dictionaries
        """
        page_id = self._extract_page_id_from_url(ad_library_url)
        if not page_id:
            raise MetaAdLibraryError(f"Could not extract page ID from URL: {ad_library_url}")

        return await self.get_ads_for_page(page_id, since_date, limit)

    def parse_ad_data(self, raw_ad: dict[str, Any]) -> dict[str, Any]:
        """
        Parse raw ad data from the API into a structured format.

        Args:
            raw_ad: Raw ad data from the API

        Returns:
            Parsed ad data dictionary
        """
        bodies = raw_ad.get("ad_creative_bodies", [])
        captions = raw_ad.get("ad_creative_link_captions", [])
        descriptions = raw_ad.get("ad_creative_link_descriptions", [])
        titles = raw_ad.get("ad_creative_link_titles", [])

        start_time = raw_ad.get("ad_delivery_start_time")
        if start_time:
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

        return {
            "ad_library_id": raw_ad.get("id"),
            "ad_snapshot_url": raw_ad.get("ad_snapshot_url"),
            "ad_copy": bodies[0] if bodies else None,
            "ad_headline": titles[0] if titles else None,
            "ad_description": descriptions[0] if descriptions else None,
            "cta_text": captions[0] if captions else None,
            "publication_date": start_time,
            "page_id": raw_ad.get("page_id"),
            "page_name": raw_ad.get("page_name"),
            "platforms": raw_ad.get("publisher_platforms", []),
            "languages": raw_ad.get("languages", []),
        }

    async def get_creative_url_from_snapshot(self, snapshot_url: str) -> tuple[str | None, str]:
        """
        Extract the actual creative URL from an ad snapshot page.

        Note: This requires scraping the snapshot page as Meta doesn't
        provide direct media URLs via the API.

        Args:
            snapshot_url: The ad_snapshot_url from the API

        Returns:
            Tuple of (creative_url, creative_type)
        """
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(snapshot_url)
                response.raise_for_status()
                html = response.text

                video_patterns = [
                    r'<video[^>]+src="([^"]+)"',
                    r'"video_url"\s*:\s*"([^"]+)"',
                    r'<source[^>]+src="([^"]+)"[^>]+type="video',
                ]
                for pattern in video_patterns:
                    match = re.search(pattern, html)
                    if match:
                        url = match.group(1).replace("\\u0025", "%").replace("\\", "")
                        return url, "video"

                image_patterns = [
                    r'<img[^>]+class="[^"]*_8jnf[^"]*"[^>]+src="([^"]+)"',
                    r'"full_image_url"\s*:\s*"([^"]+)"',
                    r'<img[^>]+src="([^"]+)"[^>]+alt="[^"]*ad[^"]*"',
                ]
                for pattern in image_patterns:
                    match = re.search(pattern, html, re.IGNORECASE)
                    if match:
                        url = match.group(1).replace("\\u0025", "%").replace("\\", "")
                        return url, "image"

                return None, "unknown"

        except Exception as e:
            logger.error(f"Failed to extract creative URL from snapshot: {e}")
            return None, "unknown"
