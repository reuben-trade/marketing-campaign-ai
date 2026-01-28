"""Competitor discovery service using Tavily AI research and LLM extraction."""

import json
import logging
from typing import Any, List

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from tavily import AsyncTavilyClient

from app.config import get_settings

logger = logging.getLogger(__name__)


class CompetitorDiscoveryError(Exception):
    """Exception raised when competitor discovery fails."""

    pass


class CompetitorDiscovery:
    """Discovers competitors using Tavily search and AI analysis."""

    def __init__(self) -> None:
        """Initialize the competitor discovery service."""
        settings = get_settings()

        # We need LLMs for structuring the data, but Tavily for finding it
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        # Initialize Tavily for live web research
        if not settings.tavily_api_key:
            logger.warning("TAVILY_API_KEY not set. Competitor discovery will fail.")

        self.tavily = AsyncTavilyClient(api_key=settings.tavily_api_key)

    async def discover_competitors(
        self,
        business_name: str,
        industry: str | None = None,
        business_description: str | None = None,
        location: str | None = None,  # Added useful parameter
        max_competitors: int = 10,
    ) -> List[dict[str, Any]]:
        """
        Discover potential competitors using live web research.

        Flow:
        1. Generate targeted search queries based on inputs.
        2. Use Tavily to scrape search results (URLs, snippets, content).
        3. Use LLM to extract structured competitor data from the search context.
        """
        try:
            # 1. Construct a high-intent search query
            # We combine specific terms to find "listicle" style articles or map packs
            search_query = self._generate_search_query(
                business_name, industry, business_description, location
            )

            logger.info(f"Searching Tavily for: {search_query}")

            # 2. Perform AI Search
            # 'search_depth="advanced"' allows Tavily to scrape deeper into pages
            search_result = await self.tavily.search(
                query=search_query,
                search_depth="advanced",
                max_results=15,
                include_answer=True,
                include_raw_content=False,
                include_domains=[],  # Can limit to linkedin, yelp, etc if needed
                exclude_domains=["reddit.com", "quora.com"],  # Filter noise
            )

            # Combine the 'answer' (Tavily's AI summary) and the 'results' (snippets)
            context_data = {
                "summary": search_result.get("answer", ""),
                "sources": [
                    {"title": res["title"], "url": res["url"], "content": res["content"]}
                    for res in search_result.get("results", [])
                ],
            }

            # 3. Synthesize structured data using LLM
            competitors = await self._extract_competitors_from_context(
                context_data, max_competitors, business_name
            )

            return competitors

        except Exception as e:
            logger.error(f"Competitor discovery failed: {e}")
            raise CompetitorDiscoveryError(f"Discovery failed: {e}") from e

    def _generate_search_query(
        self, name: str, industry: str | None, desc: str | None, location: str | None
    ) -> str:
        """Constructs a search query optimized for finding competitors."""
        base = f"top competitors and alternatives to {name}"

        if location:
            base += f" in {location}"

        if industry:
            base += f" for {industry}"

        # Add intent keywords that trigger comparison articles or listings
        base += " reviews pricing features vs"
        return base

    async def _extract_competitors_from_context(
        self, context_data: dict, max_count: int, original_business: str
    ) -> List[dict]:
        """Uses LLM to parse messy search results into clean JSON."""

        system_prompt = (
            "You are a Market Research Analyst. "
            "Your goal is to extract a structured list of competitors from the provided search results. "
            "Return ONLY valid JSON."
        )

        user_prompt = f"""
        I have performed a web search for competitors of "{original_business}".

        SEARCH SUMMARY:
        {context_data["summary"]}

        SEARCH RESULTS:
        {json.dumps(context_data["sources"], indent=2)}

        TASK:
        Identify up to {max_count} distinct competitors mentioned in these results.
        Do not include "{original_business}" itself in the list.

        Return a JSON object with this exact structure:
        {{
            "competitors": [
                {{
                    "company_name": "Competitor Name (as it would appear on Facebook)",
                    "description": "Brief description based on snippets",
                    "reason": "Why is this a competitor? (e.g. 'Offers similar pricing', 'Located nearby')"
                }}
            ]
        }}

        IMPORTANT: Return only the company_name, description, and reason fields.
        Do NOT try to find or include Facebook URLs, page IDs, or website URLs.
        """

        response = await self.openai_client.chat.completions.create(
            model="gpt-4.1-nano",  # Fast and cheap, good at instruction following
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,  # Low temperature for factual extraction
        )

        try:
            data = json.loads(response.choices[0].message.content)
            return data.get("competitors", [])
        except json.JSONDecodeError:
            logger.error("LLM failed to return valid JSON")
            return []

    async def enrich_competitor_data(
        self,
        company_name: str,
        industry: str | None = None,
    ) -> dict[str, Any]:
        """
        Enrich competitor data using a targeted Tavily search.
        """
        search_query = f"{company_name} {industry or ''} headquarters revenue products key features"

        try:
            # Quick basic search for specific details
            search_result = await self.tavily.search(
                query=search_query, search_depth="basic", max_results=5, include_answer=True
            )

            context = (
                search_result.get("answer", "")
                + "\n"
                + "\n".join([r["content"] for r in search_result.get("results", [])])
            )

            prompt = f"""
            Based on the search results below, build a profile for "{company_name}".

            SEARCH CONTEXT:
            {context[:4000]} # Truncate to avoid context limits if needed

            Return JSON:
            {{
                "company_name": "{company_name}",
                "industry": "{industry or "Unknown"}",
                "market_position": "Analyze from context (e.g. Leader, Budget option)",
                "key_products": ["List products found"],
                "headquarters": "City, Country (if found)",
                "estimated_revenue": "Estimate or 'Unknown'",
                "strengths": ["List 2-3 strengths found in reviews/text"]
            }}
            """

            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo-0125",  # Faster/cheaper model is fine for this
                messages=[
                    {"role": "system", "content": "Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.warning(f"Failed to enrich data for {company_name}: {e}")
            return {"company_name": company_name, "error": "Enrichment failed"}

    async def search_for_page_id(self, company_name: str) -> tuple[str | None, str | None]:
        """
        Search for a company's Facebook page using Google and extract the Page ID.

        Uses Google search with site:facebook.com to find the company's Facebook page,
        then navigates to that page to extract the Page ID.

        Args:
            company_name: Name of the company to search for

        Returns:
            Tuple of (page_id, facebook_url):
            - page_id: The extracted Page ID if found, None otherwise
            - facebook_url: The Facebook page URL found (for manual review if page_id extraction fails)
        """
        from app.services.ad_library_scraper import AdLibraryScraper

        try:
            scraper = AdLibraryScraper()
            page_id, facebook_url = await scraper.search_page_id_by_name(company_name)
            if page_id:
                logger.info(f"Found Page ID {page_id} for company '{company_name}'")
            return page_id, facebook_url
        except Exception as e:
            logger.warning(f"Failed to search for Page ID for '{company_name}': {e}")

        return None, None

    def build_ad_library_url(self, page_id: str) -> str:
        """
        Build a Meta Ad Library URL from a page ID.

        Args:
            page_id: Facebook Page ID

        Returns:
            Complete Ad Library URL
        """
        return f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id={page_id}"
