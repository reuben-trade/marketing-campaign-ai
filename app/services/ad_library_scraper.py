"""Meta Ad Library browser scraper with scroll-and-scrape pattern."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from openai import AsyncOpenAI
from playwright.async_api import Browser, Page, async_playwright
from tavily import AsyncTavilyClient

from app.config import get_settings

logger = logging.getLogger(__name__)


class AdLibraryScraperError(Exception):
    """Exception raised when Ad Library scraping fails."""

    pass


class AdLibraryScraper:
    """
    Browser-based scraper for Meta Ad Library.

    Uses scroll-and-scrape pattern to handle DOM recycling:
    - Scrape visible ads immediately
    - Track seen ad IDs to avoid duplicates
    - Scroll incrementally to load more
    """

    def __init__(self) -> None:
        """Initialize the Ad Library scraper."""
        settings = get_settings()
        self.base_url = "https://www.facebook.com/ads/library"
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.tavily_api_key = settings.tavily_api_key

    def build_ad_library_url(self, page_id: str, country: str = "AU") -> str:
        """Build direct Ad Library URL from page ID."""
        return (
            f"{self.base_url}/?active_status=active&ad_type=all"
            f"&country={country}&is_targeted_country=false&media_type=all"
            f"&search_type=page&view_all_page_id={page_id}"
        )

    async def scrape_ads_for_page(
        self,
        page_id: str,
        max_ads: int = 100,
        scroll_delay_ms: int = 2000,
        timeout_ms: int = 60000,
        country: str = "AU",
    ) -> list[dict[str, Any]]:
        """
        Scrape ads from Ad Library using scroll-and-scrape pattern.

        Args:
            page_id: Facebook Page ID
            max_ads: Maximum number of ads to scrape
            scroll_delay_ms: Delay between scrolls in milliseconds
            timeout_ms: Overall timeout for scraping
            country: Country code for ad targeting (default: AU)

        Returns:
            List of ad data dictionaries
        """
        url = self.build_ad_library_url(page_id, country)
        seen_ad_ids: set[str] = set()
        ads: list[dict[str, Any]] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                logger.info(f"Navigating to Ad Library for page {page_id}")
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")

                # Wait for content to load
                await asyncio.sleep(3)

                no_new_ads_count = 0
                max_no_new_ads = 3  # Stop after 3 scrolls with no new ads

                while len(ads) < max_ads and no_new_ads_count < max_no_new_ads:
                    # Extract ads from embedded JSON in page content
                    content = await page.content()
                    new_ads = self._extract_ads_from_html(content, seen_ad_ids)

                    if new_ads:
                        ads.extend(new_ads)
                        no_new_ads_count = 0
                        logger.info(f"Scraped {len(new_ads)} new ads (total: {len(ads)})")
                    else:
                        no_new_ads_count += 1

                    if len(ads) >= max_ads:
                        break

                    # Scroll down to load more
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await asyncio.sleep(scroll_delay_ms / 1000)

                    # Check if we've reached the bottom
                    is_at_bottom = await page.evaluate(
                        "window.innerHeight + window.scrollY >= document.body.scrollHeight - 100"
                    )
                    if is_at_bottom:
                        no_new_ads_count += 1

                await context.close()

            finally:
                await browser.close()

        logger.info(f"Finished scraping. Total ads collected: {len(ads)}")
        return ads[:max_ads]

    def _extract_ads_from_html(
        self, html_content: str, seen_ad_ids: set[str]
    ) -> list[dict[str, Any]]:
        """
        Extract ad data from embedded JSON in the HTML.

        Args:
            html_content: Raw HTML content
            seen_ad_ids: Set of already seen ad IDs to avoid duplicates

        Returns:
            List of newly extracted ads
        """
        new_ads = []

        # Find all ad_archive_id occurrences and extract surrounding data
        # Pattern to find ad objects in the JSON data
        ad_pattern = r'"ad_archive_id":"(\d+)"[^}]*"collation_id":"(\d+)"[^}]*"page_id":"(\d+)"'

        for match in re.finditer(ad_pattern, html_content):
            ad_archive_id = match.group(1)

            if ad_archive_id in seen_ad_ids:
                continue

            seen_ad_ids.add(ad_archive_id)

            # Extract ad body text from cards array
            body_text = None
            # Find the snapshot data for this ad and extract body from cards
            snapshot_start = html_content.find(f'"ad_archive_id":"{ad_archive_id}"')
            if snapshot_start != -1:
                # Look for body in the next 3000 chars (within the snapshot)
                snapshot_section = html_content[snapshot_start:snapshot_start + 3000]
                body_pattern = r'"body":"([^"]*)"'
                body_match = re.search(body_pattern, snapshot_section)
                if body_match:
                    try:
                        body_text = body_match.group(1).encode('utf-8').decode('unicode_escape')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        # Fallback: just use the raw text with simple replacements
                        body_text = body_match.group(1).replace("\\n", "\n").replace("\\u2022", "•")

            # Extract start date from the snapshot section
            start_date = None
            if snapshot_start != -1:
                date_pattern = r'"start_date":(\d+)'
                date_match = re.search(date_pattern, snapshot_section)
                if date_match:
                    try:
                        timestamp = int(date_match.group(1))
                        start_date = datetime.fromtimestamp(timestamp)
                    except (ValueError, OSError):
                        pass

            # Extract link URL (landing page) from snapshot section
            link_url = None
            if snapshot_start != -1:
                link_pattern = r'"link_url":"([^"]*)"'
                link_match = re.search(link_pattern, snapshot_section)
                if link_match:
                    link_url = link_match.group(1).replace("\\/", "/")

            # Determine if active (look for is_active or active status)
            is_active = True
            if snapshot_start != -1 and '"is_active":false' in snapshot_section:
                is_active = False

            # Build ad snapshot URL
            snapshot_url = f"https://www.facebook.com/ads/library/?id={ad_archive_id}"

            ad_data = {
                "ad_library_id": ad_archive_id,
                "ad_snapshot_url": snapshot_url,
                "ad_copy": body_text,
                "ad_headline": None,
                "ad_description": None,
                "cta_text": None,
                "publication_date": start_date,
                "is_active": is_active,
                "platforms": ["facebook"],
                "creative_type": "image",  # Will be determined when downloading
                "is_carousel": False,
                "carousel_item_count": None,
                "landing_page_url": link_url,
            }

            new_ads.append(ad_data)

        return new_ads

    async def get_ad_snapshot_details(
        self,
        snapshot_url: str,
        timeout_ms: int = 30000,
    ) -> dict[str, Any]:
        """
        Get detailed information from an ad's snapshot page.

        Args:
            snapshot_url: URL to the ad snapshot page
            timeout_ms: Page load timeout

        Returns:
            Dictionary with detailed ad data
        """
        details = {
            "ad_copy": None,
            "ad_headline": None,
            "ad_description": None,
            "cta_text": None,
            "creative_urls": [],
            "landing_page_url": None,
            "is_carousel": False,
            "carousel_items": [],
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                await page.goto(snapshot_url, timeout=timeout_ms, wait_until="networkidle")

                # Extract primary text
                copy_el = await page.query_selector('[data-testid="ad_creative_text"]')
                if copy_el:
                    details["ad_copy"] = (await copy_el.inner_text()).strip()

                # Extract headline
                headline_el = await page.query_selector('[data-testid="ad_headline"]')
                if headline_el:
                    details["ad_headline"] = (await headline_el.inner_text()).strip()

                # Extract description
                desc_el = await page.query_selector('[data-testid="ad_description"]')
                if desc_el:
                    details["ad_description"] = (await desc_el.inner_text()).strip()

                # Extract CTA
                cta_el = await page.query_selector('[data-testid="ad_cta_button"]')
                if cta_el:
                    details["cta_text"] = (await cta_el.inner_text()).strip()

                # Handle carousel - extract all items without clicking
                carousel_container = await page.query_selector('[data-testid="carousel_container"]')
                if carousel_container:
                    details["is_carousel"] = True

                    # Get all images in carousel
                    images = await carousel_container.query_selector_all("img")
                    for i, img in enumerate(images):
                        src = await img.get_attribute("src")
                        if src and not src.startswith("data:"):
                            details["carousel_items"].append({
                                "index": i,
                                "url": src,
                                "type": "image",
                            })

                    # Get all videos in carousel
                    videos = await carousel_container.query_selector_all("video")
                    for i, video in enumerate(videos):
                        src = await video.get_attribute("src")
                        poster = await video.get_attribute("poster")
                        if src:
                            details["carousel_items"].append({
                                "index": len(details["carousel_items"]),
                                "url": src,
                                "type": "video",
                                "poster": poster,
                            })
                else:
                    # Single creative
                    video = await page.query_selector("video")
                    if video:
                        src = await video.get_attribute("src")
                        if src:
                            details["creative_urls"].append({"url": src, "type": "video"})
                    else:
                        # Look for main image
                        img = await page.query_selector('[data-testid="ad_creative_image"] img')
                        if img:
                            src = await img.get_attribute("src")
                            if src and not src.startswith("data:"):
                                details["creative_urls"].append({"url": src, "type": "image"})

                # Extract landing page URL
                links = await page.query_selector_all("a[href]")
                for link in links:
                    href = await link.get_attribute("href")
                    if href and not any(
                        x in href.lower()
                        for x in ["facebook.com", "instagram.com", "fb.com", "javascript:"]
                    ):
                        details["landing_page_url"] = href
                        break

                await context.close()

            finally:
                await browser.close()

        return details

    async def search_page_id_by_name(
        self,
        company_name: str,
        timeout_ms: int = 30000,
    ) -> tuple[str | None, str | None]:
        """
        Search for a company's Facebook page using Tavily and extract the Page ID.

        Uses Tavily API to search for the Facebook page, then navigates to that page
        with Playwright to extract the Page ID.

        Args:
            company_name: Name of the company to search for
            timeout_ms: Page load timeout

        Returns:
            Tuple of (page_id, facebook_url):
            - page_id: The extracted Page ID if found, None otherwise
            - facebook_url: The Facebook page URL found (for manual review if page_id extraction fails)
        """
        from app.config import get_settings
        from tavily import AsyncTavilyClient

        settings = get_settings()
        if not settings.tavily_api_key:
            logger.warning("TAVILY_API_KEY not set. Cannot search for Facebook pages.")
            return None, None

        logger.info(f"Searching Tavily for Facebook page: {company_name}")

        # Patterns to find page IDs in Facebook page HTML
        # IMPORTANT: Use exact matches to avoid delegate_page_id, etc.
        # Order matters - more specific patterns first
        patterns = [
            # Escaped JSON format (common in embedded scripts): \"page_id\":\"123\"
            r'(?<![a-zA-Z_])\\?"page_id\\?":\\?"(\d+)\\?"',
            # Standard JSON format: "page_id":"123"
            r'(?<![a-zA-Z_])"page_id":"(\d+)"',
            # Without quotes around value
            r'(?<![a-zA-Z_])"page_id":(\d+)(?!\d)',
        ]

        # Step 1: Use Tavily to search for Facebook page
        tavily = AsyncTavilyClient(api_key=settings.tavily_api_key)
        search_query = f'site:facebook.com "{company_name}" page'

        try:
            search_result = await tavily.search(
                query=search_query,
                search_depth="basic",
                max_results=5,
                include_domains=["facebook.com"],
            )

            results = search_result.get("results", [])
            logger.info(f"Tavily returned {len(results)} results for query: {search_query}")

            # Find Facebook URL in results
            facebook_link = None
            skip_patterns = [
                "/login", "/help", "/policies", "/privacy",
                "business.facebook", "developers.facebook",
                "/watch", "/groups", "/events", "/marketplace",
                "/share", "/sharer", "/dialog", "/plugins"
            ]

            for i, result in enumerate(results, 1):
                url = result.get("url", "")
                title = result.get("title", "")[:60]
                logger.debug(f"  Result {i}: {url} - {title}")

                if "facebook.com" in url and not facebook_link:
                    # Skip non-page URLs
                    if any(skip in url.lower() for skip in skip_patterns):
                        logger.debug(f"    -> SKIPPED (matches exclusion pattern)")
                        continue
                    logger.debug(f"    -> SELECTED")
                    facebook_link = url

            if not facebook_link:
                logger.warning(f"No Facebook page found in Tavily results for: {company_name}")
                return None, None

            logger.info(f"Found Facebook link via Tavily: {facebook_link}")

        except Exception as e:
            logger.warning(f"Tavily search failed for {company_name}: {e}")
            return None, None

        # Step 2: Navigate to the Facebook page and extract Page ID
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                try:
                    await page.goto(facebook_link, timeout=timeout_ms, wait_until="networkidle")
                    await asyncio.sleep(2)

                    # Get the final URL (in case of redirects)
                    final_url = page.url
                    logger.info(f"Navigated to: {final_url}")

                    # Method 1: Try meta tags first (fastest & most reliable)
                    page_id = await self._get_page_id_from_meta(page)
                    if page_id:
                        logger.info(f"Found page ID via meta tag: {page_id}")
                        await context.close()
                        return page_id, final_url

                    # Method 2: Try transparency section
                    page_id = await self._get_page_id_from_transparency(
                        page, final_url, timeout_ms
                    )
                    if page_id:
                        logger.info(f"Found page ID via transparency section: {page_id}")
                        await context.close()
                        return page_id, final_url

                    # Method 3: Fallback to regex patterns on page content
                    content = await page.content()
                    page_id_candidates: dict[str, int] = {}

                    for pattern in patterns:
                        for match in re.finditer(pattern, content):
                            pid = match.group(1)
                            if len(pid) >= 10:
                                page_id_candidates[pid] = page_id_candidates.get(pid, 0) + 1

                    if page_id_candidates:
                        best_page_id = max(page_id_candidates, key=page_id_candidates.get)
                        logger.info(
                            f"Found page ID candidates: {page_id_candidates}. "
                            f"Selected: {best_page_id} (appeared {page_id_candidates[best_page_id]} times)"
                        )
                        await context.close()
                        return best_page_id, final_url

                    # If we couldn't extract the page ID, return the URL for manual review
                    logger.warning(
                        f"Could not extract page ID from {final_url}. "
                        "URL will be flagged for manual review."
                    )
                    await context.close()
                    return None, final_url

                except Exception as e:
                    logger.warning(f"Failed to navigate to Facebook page: {e}")
                    await context.close()
                    return None, facebook_link

            finally:
                await browser.close()

        return None, None

    async def _get_page_id_from_meta(self, page: Page) -> str | None:
        """
        Extract Page ID from meta tags.

        Facebook includes Page ID in standard meta tags for mobile app linking.
        These are reliable because external crawlers and the FB mobile app use them.

        Args:
            page: Playwright page object

        Returns:
            Page ID string or None if not found
        """
        try:
            # Primary: al:android:url meta tag used for FB mobile app
            meta_element = page.locator('meta[property="al:android:url"]')
            if await meta_element.count() > 0:
                content = await meta_element.get_attribute("content")
                if content and "fb://page/" in content:
                    page_id = content.replace("fb://page/", "")
                    if page_id.isdigit() and len(page_id) >= 10:
                        return page_id

            # Fallback: legacy fb:page_id meta tag
            meta_id_element = page.locator('meta[property="fb:page_id"]')
            if await meta_id_element.count() > 0:
                content = await meta_id_element.get_attribute("content")
                if content and content.isdigit() and len(content) >= 10:
                    return content

            # Also try al:ios:url as another fallback
            ios_meta = page.locator('meta[property="al:ios:url"]')
            if await ios_meta.count() > 0:
                content = await ios_meta.get_attribute("content")
                if content and "fb://page/" in content:
                    page_id = content.replace("fb://page/", "").split("?")[0]
                    if page_id.isdigit() and len(page_id) >= 10:
                        return page_id

        except Exception as e:
            logger.debug(f"Meta tag extraction failed: {e}")

        return None

    async def _get_page_id_from_transparency(self, page: Page, profile_url: str, timeout_ms: int) -> str | None:
        """
        Extract Page ID from the Page Transparency section.

        Navigates to the transparency URL and finds spans containing the numeric
        Page ID using Facebook's class pattern.

        Args:
            page: Playwright page object
            profile_url: The Facebook page profile URL
            timeout_ms: Page load timeout

        Returns:
            Page ID string or None if not found
        """
        transparency_url = profile_url.rstrip("/") + "/about_profile_transparency"

        try:
            await page.goto(transparency_url, timeout=timeout_ms, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Find spans with Facebook's x193iq5w class that contain only a numeric ID
            id_spans = page.locator('span[class*="x193iq5w"]')
            count = await id_spans.count()

            for i in range(count):
                span_text = await id_spans.nth(i).inner_text()
                if re.match(r'^\d{10,}$', span_text.strip()):
                    logger.debug(f"Found Page ID via transparency: {span_text.strip()}")
                    return span_text.strip()

            logger.warning(f"Could not extract Page ID from transparency page: {transparency_url}")
            return None

        except Exception as e:
            logger.warning(f"Failed to load transparency page: {e}")
            return None

    async def extract_page_id_from_profile(
        self,
        profile_url: str,
        timeout_ms: int = 30000,
    ) -> str | None:
        """
        Extract Page ID from a Facebook profile page.

        WARNING: Only use this once per competitor. Facebook profiles
        have aggressive bot detection. After getting the Page ID,
        always use the direct Ad Library URL.

        Args:
            profile_url: Facebook page profile URL
            timeout_ms: Page load timeout

        Returns:
            Page ID string or None if not found
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                await page.goto(profile_url, timeout=timeout_ms, wait_until="networkidle")

                # Method 1: Meta tags (fastest & most reliable)
                # Facebook includes Page ID in meta tags for mobile app linking
                # page_id = await self._get_page_id_from_meta(page)
                # if page_id:
                #     logger.info(f"Found page ID via meta tag: {page_id}")
                #     await context.close()
                #     return page_id

                # Method 2: Page Transparency section (direct URL)
                # Navigate directly to transparency URL to find the Page ID
                page_id = await self._get_page_id_from_transparency(page, profile_url, timeout_ms)
                if page_id:
                    logger.info(f"Found page ID via transparency section: {page_id}")
                    await context.close()
                    return page_id

                # # Method 3: Fallback - regex patterns on page content
                # content = await page.content()
                # patterns = [
                #     r'(?<![a-zA-Z_])\\?"page_id\\?":\\?"(\d+)\\?"',
                #     r'(?<![a-zA-Z_])"page_id":"(\d+)"',
                #     r'(?<![a-zA-Z_])"page_id":(\d+)(?!\d)',
                # ]

                page_id_candidates: dict[str, int] = {}
                for pattern in patterns:
                    for match in re.finditer(pattern, content):
                        pid = match.group(1)
                        if len(pid) >= 10:
                            page_id_candidates[pid] = page_id_candidates.get(pid, 0) + 1

                if page_id_candidates:
                    best_page_id = max(page_id_candidates, key=page_id_candidates.get)
                    logger.info(
                        f"Found page ID candidates: {page_id_candidates}. "
                        f"Selected: {best_page_id} (appeared {page_id_candidates[best_page_id]} times)"
                    )
                    await context.close()
                    return best_page_id

                # Method 4: Try extracting from Ad Library search
                try:
                    page_name_match = re.search(r'facebook\.com/([^/?]+)', profile_url)
                    if page_name_match:
                        page_name = page_name_match.group(1)
                        ad_library_search_url = (
                            f"https://www.facebook.com/ads/library/?active_status=all"
                            f"&ad_type=all&country=ALL&q={page_name}&search_type=page"
                        )
                        await page.goto(ad_library_search_url, timeout=timeout_ms, wait_until="networkidle")
                        await asyncio.sleep(2)

                        content = await page.content()

                        # Ad Library URLs contain view_all_page_id=XXXXX
                        match = re.search(r'view_all_page_id=(\d+)', content)
                        if match:
                            page_id = match.group(1)
                            logger.info(f"Found page ID via Ad Library search: {page_id}")
                            await context.close()
                            return page_id
                except Exception as e:
                    logger.debug(f"Ad Library search extraction failed: {e}")

                await context.close()

            finally:
                await browser.close()

        logger.warning(f"Could not extract page ID from {profile_url}")
        return None

    async def get_creative_url_from_snapshot(
        self,
        snapshot_url: str,
        timeout_ms: int = 30000,
    ) -> tuple[str | None, str]:
        """
        Extract the actual creative URL from an ad snapshot page using browser.

        Args:
            snapshot_url: The ad snapshot URL

        Returns:
            Tuple of (creative_url, creative_type)
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                await page.goto(snapshot_url, timeout=timeout_ms, wait_until="networkidle")

                # Check for video first
                video_element = await page.query_selector("video")
                if video_element:
                    src = await video_element.get_attribute("src")
                    if src:
                        await context.close()
                        return src, "video"

                    # Try to get src from source element
                    source_element = await video_element.query_selector("source")
                    if source_element:
                        src = await source_element.get_attribute("src")
                        if src:
                            await context.close()
                            return src, "video"

                # Look for main image
                # Try various selectors that Facebook uses
                image_selectors = [
                    'img[data-testid="ad_creative_image"]',
                    'img._8jnf',
                    'div[data-testid="ad_creative"] img',
                    'img[alt*="ad"]',
                ]

                for selector in image_selectors:
                    img_element = await page.query_selector(selector)
                    if img_element:
                        src = await img_element.get_attribute("src")
                        if src and not src.startswith("data:"):
                            await context.close()
                            return src, "image"

                # Fallback: look in page source for URLs
                content = await page.content()

                # Video URL patterns
                video_patterns = [
                    r'"video_url"\s*:\s*"([^"]+)"',
                    r'"playable_url"\s*:\s*"([^"]+)"',
                    r'"playable_url_quality_hd"\s*:\s*"([^"]+)"',
                ]
                for pattern in video_patterns:
                    match = re.search(pattern, content)
                    if match:
                        url = match.group(1).replace("\\u0025", "%").replace("\\/", "/")
                        await context.close()
                        return url, "video"

                # Image URL patterns
                image_patterns = [
                    r'"full_image_url"\s*:\s*"([^"]+)"',
                    r'"image_url"\s*:\s*"([^"]+)"',
                    r'"photo_image"\s*:\{"uri":"([^"]+)"',
                ]
                for pattern in image_patterns:
                    match = re.search(pattern, content)
                    if match:
                        url = match.group(1).replace("\\u0025", "%").replace("\\/", "/")
                        await context.close()
                        return url, "image"

                await context.close()

            except Exception as e:
                logger.error(f"Failed to extract creative URL from snapshot: {e}")

            finally:
                await browser.close()

        return None, "unknown"

    # =========================================================================
    # Batch Page ID Lookup Methods
    # =========================================================================

    async def batch_search_page_ids(
        self,
        competitor_names: list[str],
        timeout_ms: int = 30000,
        max_concurrent_searches: int = 5,
    ) -> dict[str, tuple[str | None, str | None]]:
        """
        Batch search for Facebook page IDs for multiple competitors.

        Uses parallel Tavily searches and GPT-4o-mini to select the best
        Facebook page URL for each competitor, then extracts page IDs.

        Args:
            competitor_names: List of company names to search for
            timeout_ms: Timeout for each Playwright page load
            max_concurrent_searches: Maximum concurrent Tavily searches

        Returns:
            Dict mapping competitor name to (page_id, facebook_url) tuple.
            - page_id may be None if extraction failed (URL flagged for manual review)
            - facebook_url may be None if no valid URL was found
        """
        if not competitor_names:
            return {}

        logger.info(f"Starting batch page ID search for {len(competitor_names)} competitors")

        # Step 1: Parallel Tavily searches
        search_results = await self._parallel_tavily_search(
            competitor_names, max_concurrent_searches
        )

        # Step 2: GPT URL selection
        url_selections = await self._select_urls_with_gpt(search_results)

        # Step 3: Extract page IDs from selected URLs
        results = await self._extract_page_ids_batch(url_selections, timeout_ms)

        logger.info(
            f"Batch search complete: {sum(1 for v in results.values() if v[0])} page IDs found, "
            f"{sum(1 for v in results.values() if v[0] is None and v[1])} flagged for manual review"
        )

        return results

    async def _parallel_tavily_search(
        self,
        competitor_names: list[str],
        max_concurrent: int = 5,
    ) -> dict[str, list[dict[str, str]]]:
        """
        Execute Tavily searches in parallel for multiple competitors.

        Returns:
            Dict mapping competitor name to list of {url, title, content} dicts
        """
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY not set. Cannot perform batch search.")
            return {name: [] for name in competitor_names}

        tavily = AsyncTavilyClient(api_key=self.tavily_api_key)
        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, list[dict[str, str]]] = {}

        async def search_one(name: str) -> tuple[str, list[dict[str, str]]]:
            async with semaphore:
                search_query = f'site:facebook.com "{name}" page'
                logger.debug(f"Tavily search for '{name}': {search_query}")

                try:
                    search_result = await tavily.search(
                        query=search_query,
                        search_depth="basic",
                        max_results=5,
                        include_domains=["facebook.com"],
                    )

                    items = []
                    for result in search_result.get("results", []):
                        items.append({
                            "url": result.get("url", ""),
                            "title": result.get("title", ""),
                            "content": result.get("content", "")[:200],
                        })

                    logger.debug(f"Tavily returned {len(items)} results for '{name}'")
                    return name, items

                except Exception as e:
                    logger.warning(f"Tavily search failed for '{name}': {e}")
                    return name, []

        # Execute all searches in parallel
        tasks = [search_one(name) for name in competitor_names]
        search_results = await asyncio.gather(*tasks)

        for name, items in search_results:
            results[name] = items

        return results

    async def _select_urls_with_gpt(
        self,
        search_results: dict[str, list[dict[str, str]]],
    ) -> list[dict]:
        """
        Use GPT-4o-mini to select the best Facebook page URL for each competitor.

        Returns:
            List of selection dicts with keys: competitor_name, selected_url,
            confidence, needs_manual_review, reason
        """
        # Filter out competitors with no search results
        competitors_with_results = {
            name: results for name, results in search_results.items() if results
        }

        if not competitors_with_results:
            logger.warning("No search results to process with GPT")
            return [
                {
                    "competitor_name": name,
                    "selected_url": None,
                    "confidence": "low",
                    "needs_manual_review": True,
                    "reason": "No search results found",
                }
                for name in search_results.keys()
            ]

        system_prompt = """You are a Facebook Page URL selector. Given search results for each company, select the most likely official Facebook business page URL.

RULES:
1. Prefer URLs that match the pattern: facebook.com/{PageName} or facebook.com/{PageName}/
2. If you find a posts URL like facebook.com/CompanyName/posts/123, extract the base: facebook.com/CompanyName
3. If you find facebook.com/profile.php?id=12345, keep it as-is (valid page format)
4. SKIP these URL types - they are NOT business pages:
   - facebook.com/groups/...
   - facebook.com/events/...
   - facebook.com/watch/...
   - facebook.com/marketplace/...
   - facebook.com/share/...
   - facebook.com/login/...
   - business.facebook.com/...
   - developers.facebook.com/...
5. If ALL results are noise or you cannot confidently identify an official page, set needs_manual_review=true
6. Always normalize URLs: remove trailing slashes, query params, and path suffixes like /posts/123

Return JSON only."""

        user_prompt = f"""For each company below, I have search results from Tavily. Select the best Facebook page URL.

SEARCH RESULTS:
{json.dumps(competitors_with_results, indent=2)}

Return a JSON object with this exact structure:
{{
    "selections": [
        {{
            "competitor_name": "Company Name",
            "selected_url": "https://www.facebook.com/CompanyPage" or null,
            "confidence": "high" or "medium" or "low",
            "needs_manual_review": true or false,
            "reason": "Brief explanation"
        }}
    ]
}}

IMPORTANT:
- Include ALL competitors from the search results
- If you see facebook.com/McDonalds/posts/12345, return https://www.facebook.com/McDonalds
- If you see facebook.com/Nike/videos/12345, return https://www.facebook.com/Nike
- If results only contain groups, events, or unrelated profiles, set selected_url=null and needs_manual_review=true"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            result_text = response.choices[0].message.content.strip()
            data = json.loads(result_text)
            selections = data.get("selections", [])

            logger.info(f"GPT selected URLs for {len(selections)} competitors")
            for sel in selections:
                logger.debug(
                    f"  {sel['competitor_name']}: {sel.get('selected_url', 'None')} "
                    f"(confidence: {sel.get('confidence')}, manual_review: {sel.get('needs_manual_review')})"
                )

            # Add entries for competitors that had no results (not sent to GPT)
            selected_names = {s["competitor_name"] for s in selections}
            for name in search_results.keys():
                if name not in selected_names:
                    selections.append({
                        "competitor_name": name,
                        "selected_url": None,
                        "confidence": "low",
                        "needs_manual_review": True,
                        "reason": "No search results found",
                    })

            return selections

        except Exception as e:
            logger.error(f"GPT URL selection failed: {e}")
            # Fallback: use first valid URL from each competitor's results
            return self._fallback_url_selection(search_results)

    def _fallback_url_selection(
        self, search_results: dict[str, list[dict[str, str]]]
    ) -> list[dict]:
        """Fallback URL selection when GPT fails."""
        skip_patterns = [
            "/login", "/help", "/policies", "/privacy",
            "business.facebook", "developers.facebook",
            "/watch", "/groups", "/events", "/marketplace",
            "/share", "/sharer", "/dialog", "/plugins"
        ]

        selections = []
        for name, results in search_results.items():
            selected_url = None
            for result in results:
                url = result.get("url", "")
                if "facebook.com" in url:
                    if not any(skip in url.lower() for skip in skip_patterns):
                        selected_url = self._normalize_facebook_url(url)
                        break

            selections.append({
                "competitor_name": name,
                "selected_url": selected_url,
                "confidence": "low",
                "needs_manual_review": selected_url is None,
                "reason": "Fallback selection (GPT unavailable)",
            })

        return selections

    def _normalize_facebook_url(self, url: str) -> str:
        """
        Normalize a Facebook URL to its canonical page form.

        Examples:
            facebook.com/Nike/posts/123 -> https://www.facebook.com/Nike
            facebook.com/Nike/videos/456 -> https://www.facebook.com/Nike
            facebook.com/Nike/ -> https://www.facebook.com/Nike
            m.facebook.com/Nike -> https://www.facebook.com/Nike
        """
        # Ensure URL has scheme
        if not url.startswith("http"):
            url = f"https://{url}"

        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        # Remove common suffixes
        path = re.sub(r"/(posts|videos|photos|events|reviews|about|shop)/.*$", "", path)

        return f"https://www.facebook.com{path}"

    async def _extract_page_ids_batch(
        self,
        url_selections: list[dict],
        timeout_ms: int = 30000,
        max_concurrent: int = 3,
    ) -> dict[str, tuple[str | None, str | None]]:
        """
        Extract page IDs from selected URLs using shared browser context.

        Reuses a single browser instance with multiple pages for efficiency.
        """
        results: dict[str, tuple[str | None, str | None]] = {}

        # Separate URLs that need extraction from manual review cases
        to_extract = [
            sel for sel in url_selections
            if sel.get("selected_url") and not sel.get("needs_manual_review")
        ]
        manual_review = [
            sel for sel in url_selections
            if not sel.get("selected_url") or sel.get("needs_manual_review")
        ]

        # Add manual review cases to results
        for sel in manual_review:
            results[sel["competitor_name"]] = (None, sel.get("selected_url"))

        if not to_extract:
            return results

        logger.info(f"Extracting page IDs for {len(to_extract)} URLs")

        # Use existing page ID extraction logic with shared browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                semaphore = asyncio.Semaphore(max_concurrent)

                async def extract_one(sel: dict) -> tuple[str, str | None, str | None]:
                    async with semaphore:
                        name = sel["competitor_name"]
                        url = sel["selected_url"]

                        try:
                            context = await browser.new_context(
                                viewport={"width": 1920, "height": 1080},
                                user_agent=(
                                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/120.0.0.0 Safari/537.36"
                                ),
                            )
                            page = await context.new_page()

                            await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                            await asyncio.sleep(2)

                            final_url = page.url

                            # Try meta tags first
                            page_id = await self._get_page_id_from_meta(page)
                            if page_id:
                                logger.debug(f"Found page ID via meta for '{name}': {page_id}")
                                await context.close()
                                return name, page_id, final_url

                            # Try transparency section
                            page_id = await self._get_page_id_from_transparency(
                                page, final_url, timeout_ms
                            )
                            if page_id:
                                logger.debug(f"Found page ID via transparency for '{name}': {page_id}")
                                await context.close()
                                return name, page_id, final_url

                            # Fallback to regex patterns
                            await page.goto(final_url, timeout=timeout_ms, wait_until="networkidle")
                            content = await page.content()

                            patterns = [
                                r'(?<![a-zA-Z_])\\?"page_id\\?":\\?"(\d+)\\?"',
                                r'(?<![a-zA-Z_])"page_id":"(\d+)"',
                                r'(?<![a-zA-Z_])"page_id":(\d+)(?!\d)',
                            ]

                            page_id_candidates: dict[str, int] = {}
                            for pattern in patterns:
                                for match in re.finditer(pattern, content):
                                    pid = match.group(1)
                                    if len(pid) >= 10:
                                        page_id_candidates[pid] = page_id_candidates.get(pid, 0) + 1

                            if page_id_candidates:
                                best_page_id = max(page_id_candidates, key=page_id_candidates.get)
                                logger.debug(f"Found page ID via regex for '{name}': {best_page_id}")
                                await context.close()
                                return name, best_page_id, final_url

                            logger.warning(f"Could not extract page ID for '{name}' from {final_url}")
                            await context.close()
                            return name, None, final_url

                        except Exception as e:
                            logger.warning(f"Page ID extraction failed for '{name}': {e}")
                            return name, None, url

                tasks = [extract_one(sel) for sel in to_extract]
                extraction_results = await asyncio.gather(*tasks)

                for name, page_id, facebook_url in extraction_results:
                    results[name] = (page_id, facebook_url)

            finally:
                await browser.close()

        return results
