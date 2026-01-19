"""Landing page scraper service using Playwright."""

import asyncio
import hashlib
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, async_playwright

from app.config import get_settings
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


class LandingPageScraperError(Exception):
    """Exception raised when landing page scraping fails."""

    pass


class LandingPageScraper:
    """Scrapes landing pages and extracts content, screenshots, and tracking pixels."""

    def __init__(self) -> None:
        """Initialize the landing page scraper."""
        settings = get_settings()
        self.storage = SupabaseStorage()
        self.screenshot_bucket = settings.supabase_screenshots_bucket

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """Generate SHA256 hash of URL for deduplication."""
        return hashlib.sha256(url.encode()).hexdigest()

    async def scrape_landing_page(
        self,
        url: str,
        capture_screenshots: bool = True,
        detect_pixels: bool = True,
        timeout_ms: int = 30000,
    ) -> dict[str, Any]:
        """
        Scrape a landing page and extract all relevant data.

        Args:
            url: Landing page URL to scrape
            capture_screenshots: Whether to capture desktop/mobile screenshots
            detect_pixels: Whether to detect tracking pixels
            timeout_ms: Page load timeout in milliseconds

        Returns:
            Dictionary containing all scraped data
        """
        result = {
            "url": url,
            "url_hash": self.generate_url_hash(url),
            "final_url": None,
            "page_title": None,
            "meta_description": None,
            "meta_keywords": None,
            "headings": {"h1": [], "h2": [], "h3": []},
            "content_preview": None,
            "cta_buttons": [],
            "http_status_code": None,
            "load_time_ms": None,
            "desktop_screenshot_path": None,
            "mobile_screenshot_path": None,
            "meta_pixel_id": None,
            "has_capi": False,
            "google_ads_tag_id": None,
            "tiktok_pixel_id": None,
            "technical_sophistication_score": 0,
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                # Create context with desktop viewport
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )

                page = await context.new_page()

                # Track network requests for pixel detection
                pixel_data = {
                    "meta_pixel_id": None,
                    "has_capi": False,
                    "google_ads_tag_id": None,
                    "tiktok_pixel_id": None,
                }

                if detect_pixels:
                    page.on("request", lambda req: self._detect_pixels_from_request(req, pixel_data))

                # Navigate to page and measure load time
                start_time = time.time()
                try:
                    response = await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                    load_time_ms = int((time.time() - start_time) * 1000)

                    if response:
                        result["http_status_code"] = response.status
                        result["final_url"] = page.url
                    result["load_time_ms"] = load_time_ms

                except Exception as e:
                    logger.warning(f"Page load issue for {url}: {e}")
                    # Try to continue with partial data
                    result["load_time_ms"] = int((time.time() - start_time) * 1000)

                # Extract page content
                await self._extract_page_content(page, result)

                # Capture screenshots
                if capture_screenshots:
                    await self._capture_screenshots(browser, url, result)

                # Apply pixel detection results
                if detect_pixels:
                    result.update(pixel_data)

                # Calculate technical sophistication score
                result["technical_sophistication_score"] = self._calculate_sophistication_score(
                    result
                )

                await context.close()

            finally:
                await browser.close()

        return result

    async def _extract_page_content(self, page: Page, result: dict[str, Any]) -> None:
        """Extract content from the page."""
        try:
            # Page title
            result["page_title"] = await page.title()

            # Meta description
            meta_desc = await page.query_selector('meta[name="description"]')
            if meta_desc:
                result["meta_description"] = await meta_desc.get_attribute("content")

            # Meta keywords
            meta_keywords = await page.query_selector('meta[name="keywords"]')
            if meta_keywords:
                result["meta_keywords"] = await meta_keywords.get_attribute("content")

            # Headings
            for level in ["h1", "h2", "h3"]:
                elements = await page.query_selector_all(level)
                result["headings"][level] = [
                    (await el.inner_text()).strip()
                    for el in elements[:10]  # Limit to first 10
                ]

            # Content preview (first 500 chars of body text)
            body = await page.query_selector("body")
            if body:
                text = await body.inner_text()
                # Clean up whitespace
                text = re.sub(r"\s+", " ", text).strip()
                result["content_preview"] = text[:500] if text else None

            # CTA buttons
            result["cta_buttons"] = await self._extract_cta_buttons(page)

        except Exception as e:
            logger.warning(f"Error extracting page content: {e}")

    async def _extract_cta_buttons(self, page: Page) -> list[dict[str, str]]:
        """Extract call-to-action buttons from the page."""
        cta_buttons = []

        # Common CTA selectors
        selectors = [
            'a[class*="cta"]',
            'button[class*="cta"]',
            'a[class*="btn"]',
            'button[class*="btn"]',
            'a[href*="signup"]',
            'a[href*="register"]',
            'a[href*="get-started"]',
            'a[href*="free-trial"]',
            'a[href*="demo"]',
            'a[href*="contact"]',
            'a[href*="quote"]',
            "[data-cta]",
            "[data-action]",
        ]

        try:
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                for el in elements[:5]:  # Limit per selector
                    text = (await el.inner_text()).strip()
                    href = await el.get_attribute("href")
                    if text and len(text) < 100:  # Reasonable button text length
                        cta_buttons.append({"text": text, "href": href or ""})

            # Deduplicate by text
            seen = set()
            unique_buttons = []
            for btn in cta_buttons:
                if btn["text"] not in seen:
                    seen.add(btn["text"])
                    unique_buttons.append(btn)

            return unique_buttons[:10]  # Return max 10 CTAs

        except Exception as e:
            logger.warning(f"Error extracting CTA buttons: {e}")
            return []

    async def _capture_screenshots(
        self, browser: Browser, url: str, result: dict[str, Any]
    ) -> None:
        """Capture desktop and mobile screenshots."""
        url_hash = result["url_hash"][:16]  # Use first 16 chars for filename

        # Desktop screenshot
        try:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            await page.goto(url, timeout=30000, wait_until="networkidle")
            desktop_bytes = await page.screenshot(full_page=False)
            await context.close()

            # Upload to Supabase
            desktop_path = f"landing_pages/{url_hash}_desktop.png"
            await self.storage.upload_bytes(
                desktop_bytes, desktop_path, self.screenshot_bucket, "image/png"
            )
            result["desktop_screenshot_path"] = desktop_path

        except Exception as e:
            logger.warning(f"Failed to capture desktop screenshot: {e}")

        # Mobile screenshot
        try:
            context = await browser.new_context(
                viewport={"width": 390, "height": 844},  # iPhone 14 Pro
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                ),
            )
            page = await context.new_page()
            await page.goto(url, timeout=30000, wait_until="networkidle")
            mobile_bytes = await page.screenshot(full_page=False)
            await context.close()

            # Upload to Supabase
            mobile_path = f"landing_pages/{url_hash}_mobile.png"
            await self.storage.upload_bytes(
                mobile_bytes, mobile_path, self.screenshot_bucket, "image/png"
            )
            result["mobile_screenshot_path"] = mobile_path

        except Exception as e:
            logger.warning(f"Failed to capture mobile screenshot: {e}")

    def _detect_pixels_from_request(self, request: Any, pixel_data: dict[str, Any]) -> None:
        """Detect tracking pixels from network requests."""
        url = request.url.lower()

        # Meta Pixel detection
        if "facebook.com/tr" in url or "connect.facebook.net" in url:
            # Extract pixel ID from URL
            match = re.search(r"[?&]id=(\d+)", url)
            if match:
                pixel_data["meta_pixel_id"] = match.group(1)

        # CAPI detection (server-side events)
        if "graph.facebook.com" in url and "/events" in url:
            pixel_data["has_capi"] = True

        # Google Ads / GTM detection
        if "googletagmanager.com" in url or "google-analytics.com" in url:
            # Extract GTM ID
            match = re.search(r"GTM-([A-Z0-9]+)", url)
            if match:
                pixel_data["google_ads_tag_id"] = f"GTM-{match.group(1)}"
            # Extract GA ID
            match = re.search(r"[?&]id=(G-[A-Z0-9]+|UA-\d+-\d+)", url)
            if match:
                pixel_data["google_ads_tag_id"] = match.group(1)

        if "googleadservices.com" in url or "googlesyndication.com" in url:
            # Extract conversion ID
            match = re.search(r"AW-(\d+)", url)
            if match:
                pixel_data["google_ads_tag_id"] = f"AW-{match.group(1)}"

        # TikTok Pixel detection
        if "analytics.tiktok.com" in url:
            match = re.search(r"[?&]sdkid=([A-Z0-9]+)", url, re.IGNORECASE)
            if match:
                pixel_data["tiktok_pixel_id"] = match.group(1)

    def _calculate_sophistication_score(self, result: dict[str, Any]) -> int:
        """Calculate technical sophistication score (0-100)."""
        score = 0

        if result.get("meta_pixel_id"):
            score += 20
        if result.get("has_capi"):
            score += 30
        if result.get("google_ads_tag_id"):
            score += 20
        if result.get("tiktok_pixel_id"):
            score += 20
        if result.get("load_time_ms") and result["load_time_ms"] < 3000:
            score += 10

        return min(score, 100)

    async def scrape_multiple(
        self,
        urls: list[str],
        concurrency: int = 3,
        capture_screenshots: bool = True,
        detect_pixels: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Scrape multiple landing pages concurrently.

        Args:
            urls: List of URLs to scrape
            concurrency: Number of concurrent scrapes
            capture_screenshots: Whether to capture screenshots
            detect_pixels: Whether to detect tracking pixels

        Returns:
            List of scrape results
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_semaphore(url: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self.scrape_landing_page(
                        url,
                        capture_screenshots=capture_screenshots,
                        detect_pixels=detect_pixels,
                    )
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {e}")
                    return {
                        "url": url,
                        "url_hash": self.generate_url_hash(url),
                        "error": str(e),
                    }

        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)

    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
