"""Competitor discovery service using AI-powered web research."""

import json
import logging
import re
from typing import Any

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import get_settings
from app.utils.prompts import COMPETITOR_DISCOVERY_PROMPT

logger = logging.getLogger(__name__)


class CompetitorDiscoveryError(Exception):
    """Exception raised when competitor discovery fails."""

    pass


class CompetitorDiscovery:
    """Discovers competitors using AI-powered research."""

    def __init__(self) -> None:
        """Initialize the competitor discovery service."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def discover_competitors(
        self,
        business_name: str,
        industry: str | None = None,
        business_description: str | None = None,
        market_position: str | None = None,
        max_competitors: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Discover potential competitors based on business information.

        Args:
            business_name: Name of the business
            industry: Industry/sector
            business_description: Description of the business
            market_position: Current market position
            max_competitors: Maximum number of competitors to find

        Returns:
            List of competitor dictionaries
        """
        prompt = COMPETITOR_DISCOVERY_PROMPT.format(
            business_name=business_name,
            industry=industry or "Unknown",
            business_description=business_description or "Not provided",
            market_position=market_position or "Unknown",
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a market research expert with deep knowledge of various "
                            "industries and their competitive landscapes. Provide accurate, "
                            "actionable competitor intelligence. Always respond with valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=2000,
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise CompetitorDiscoveryError("Empty response from AI")

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())
            competitors = result.get("competitors", [])[:max_competitors]

            return competitors

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse competitor discovery response: {e}")
            raise CompetitorDiscoveryError(f"Failed to parse response: {e}") from e
        except Exception as e:
            logger.error(f"Competitor discovery failed: {e}")
            raise CompetitorDiscoveryError(f"Discovery failed: {e}") from e

    def extract_page_id_from_url(self, url: str) -> str | None:
        """
        Extract Facebook Page ID from various URL formats.

        Supports:
        - https://www.facebook.com/ads/library/?view_all_page_id=123456789
        - Direct numeric IDs

        Args:
            url: Facebook URL or page ID

        Returns:
            Page ID if extractable, None otherwise
        """
        if not url:
            return None

        # Already a numeric ID
        if url.isdigit():
            return url

        # Try to extract from Ad Library URL
        patterns = [
            r"view_all_page_id=(\d+)",
            r"[?&]id=(\d+)",
            r"page_id=(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    async def lookup_page_id_from_facebook_url(self, facebook_url: str) -> str | None:
        """
        Use browser scraping to extract Page ID from a Facebook page URL.

        Args:
            facebook_url: Facebook page URL (e.g., https://facebook.com/CompanyName)

        Returns:
            Page ID if found, None otherwise
        """
        from app.services.ad_library_scraper import AdLibraryScraper

        # First try to extract from URL directly
        page_id = self.extract_page_id_from_url(facebook_url)
        if page_id:
            return page_id

        # Use browser scraping to extract from page
        try:
            scraper = AdLibraryScraper()
            page_id = await scraper.extract_page_id_from_profile(facebook_url)
            if page_id:
                logger.info(f"Found Page ID {page_id} for {facebook_url}")
                return page_id
        except Exception as e:
            logger.warning(f"Failed to extract Page ID from {facebook_url}: {e}")

        return None

    def build_ad_library_url(self, page_id: str) -> str:
        """
        Build a Meta Ad Library URL from a page ID.

        Args:
            page_id: Facebook Page ID

        Returns:
            Complete Ad Library URL
        """
        return f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id={page_id}"

    async def enrich_competitor_data(
        self,
        company_name: str,
        industry: str | None = None,
    ) -> dict[str, Any]:
        """
        Enrich competitor data with additional information.

        Args:
            company_name: Name of the company
            industry: Industry/sector

        Returns:
            Enriched data dictionary
        """
        prompt = f"""
        Provide information about the company "{company_name}" in the {industry or 'business'} industry.

        Return JSON with:
        {{
            "company_name": "official name",
            "industry": "specific industry",
            "market_position": "leader/challenger/niche",
            "estimated_size": "small/medium/large/enterprise",
            "key_products": ["product 1", "product 2"],
            "target_market": "description of target market",
            "headquarters": "location if known"
        }}

        Return ONLY valid JSON.
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a business research expert. Respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result_text = response.choices[0].message.content
            if not result_text:
                return {}

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            return json.loads(result_text.strip())

        except Exception as e:
            logger.warning(f"Failed to enrich competitor data: {e}")
            return {}
