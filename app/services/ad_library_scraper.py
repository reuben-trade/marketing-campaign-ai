"""Meta Ad Library browser scraper with scroll-and-scrape pattern."""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from playwright.async_api import Browser, Page, async_playwright

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

                # Method 1: Look in page source for page_id
                content = await page.content()

                # Facebook stores the page ID in various places in the HTML/JS
                patterns = [
                    r'"pageID":"(\d+)"',
                    r'"page_id":"(\d+)"',
                    r'"pageId":"(\d+)"',
                    r'"page_id":(\d+)',
                    r'"pageID":(\d+)',
                    r'pageID=(\d+)',
                    r'/pages/(\d+)',
                    r'"id":"(\d+)".*?"__typename":"Page"',
                    # Common patterns in Facebook's data layers
                    r'entity_id["\s:]+(\d{10,})',
                    r'"actorID":"(\d+)"',
                    r'"owningProfile":\{"__typename":"Page","id":"(\d+)"',
                    r'"profile_id":"(\d+)"',
                    r'"target":\{"__typename":"Page","id":"(\d+)"',
                    # userID is used for Facebook Pages in newer layouts
                    r'"userID":"(\d+)"',
                    r'"userId":"(\d+)"',
                    r'"user_id":"(\d+)"',
                ]

                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        page_id = match.group(1)
                        # Validate it looks like a Facebook Page ID (typically 10-20 digits)
                        if len(page_id) >= 10:
                            logger.info(f"Found page ID via pattern '{pattern}': {page_id}")
                            await context.close()
                            return page_id

                # Method 2: Check the "About" section URL
                about_link = await page.query_selector('a[href*="/about"]')
                if about_link:
                    href = await about_link.get_attribute("href")
                    match = re.search(r'/(\d+)/', href)
                    if match:
                        await context.close()
                        return match.group(1)

                # Method 3: Try to extract from the page transparency section
                # Navigate to the transparency section which shows the Page ID
                try:
                    # Look for "Page transparency" or "About this Page" section
                    transparency_link = await page.query_selector(
                        'a[href*="transparency"], a[href*="about_profile_transparency"]'
                    )
                    if transparency_link:
                        await transparency_link.click()
                        await asyncio.sleep(2)

                        # Re-fetch content after clicking
                        content = await page.content()
                        for pattern in patterns:
                            match = re.search(pattern, content)
                            if match and len(match.group(1)) >= 10:
                                page_id = match.group(1)
                                logger.info(f"Found page ID via transparency section: {page_id}")
                                await context.close()
                                return page_id
                except Exception as e:
                    logger.debug(f"Transparency section extraction failed: {e}")

                # Method 4: Try extracting from Ad Library redirect
                # Going to Ad Library search might reveal the page ID
                try:
                    # Extract page name from URL
                    page_name_match = re.search(r'facebook\.com/([^/?]+)', profile_url)
                    if page_name_match:
                        page_name = page_name_match.group(1)
                        ad_library_search_url = (
                            f"https://www.facebook.com/ads/library/?active_status=all"
                            f"&ad_type=all&country=ALL&q={page_name}&search_type=page"
                        )
                        await page.goto(ad_library_search_url, timeout=timeout_ms, wait_until="networkidle")
                        await asyncio.sleep(2)

                        # Look for the page in search results
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
