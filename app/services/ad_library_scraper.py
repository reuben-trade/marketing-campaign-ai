"""Meta Ad Library browser scraper with scroll-and-scrape pattern."""

import asyncio
import json
import logging
import random
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from openai import AsyncOpenAI
from playwright.async_api import Page, async_playwright
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

    def build_ad_details_url(self, ad_library_id: str, page_id: str, country: str = "AU") -> str:
        """Build direct URL to an ad's detail view in Ad Library."""
        return (
            f"{self.base_url}/?active_status=active&ad_type=all"
            f"&country={country}&id={ad_library_id}&is_targeted_country=false"
            f"&media_type=all&search_type=page&view_all_page_id={page_id}"
        )

    async def scrape_ad_details(
        self,
        ad_library_id: str,
        page_id: str,
        country: str = "AU",
        timeout_ms: int = 30000,
    ) -> dict[str, Any]:
        """
        Scrape detailed information from an ad's modal view.

        Opens the ad in Meta Ad Library, clicks "See ad details", and extracts:
        - Started running date and total active time
        - Platforms (Facebook, Instagram, Messenger)
        - Primary text/description
        - Link headline and description
        - CTA button text
        - Additional links
        - Form fields (for lead gen ads)

        Args:
            ad_library_id: The Meta Ad Library ID for the ad
            page_id: The Facebook Page ID
            country: Country code (default: AU)
            timeout_ms: Page load timeout in milliseconds

        Returns:
            Dictionary with all extracted ad details
        """
        result: dict[str, Any] = {
            "started_running_date": None,
            "total_active_time": None,
            "platforms": [],
            "primary_text": None,
            "link_headline": None,
            "link_description": None,
            "cta_text": None,
            "additional_links": [],
            "form_fields": None,
        }

        url = self.build_ad_details_url(ad_library_id, page_id, country)

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

                logger.info(f"Navigating to ad details for {ad_library_id}")
                await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                await asyncio.sleep(3)

                # Step 1: Find the modal that contains our ad (opened by id= param)
                # The URL with id=xxx opens a "Link to ad" modal showing that specific ad
                target_modal = None
                modals = await page.query_selector_all('div[role="dialog"]')

                for modal in modals:
                    modal_text = await modal.inner_text()
                    if ad_library_id in modal_text:
                        target_modal = modal
                        logger.debug(f"Found modal containing ad {ad_library_id}")
                        break

                # Step 2: Extract data from the modal (basic info is already visible)
                if target_modal:
                    # Extract from the modal content directly
                    modal_text = await target_modal.inner_text()
                    result.update(await self._extract_timing_info_from_text(modal_text))
                    result.update(await self._extract_ad_content_from_modal(target_modal))
                    result["platforms"] = await self._extract_platforms_from_modal(target_modal)

                    # Step 3: Click "See ad details" within this modal to expand/open full details
                    see_details = await target_modal.query_selector(
                        'span:has-text("See ad details")'
                    )
                    if see_details:
                        logger.debug("Clicking 'See ad details' in modal")
                        await see_details.evaluate("el => el.click()")
                        await asyncio.sleep(2)

                        # Find the modal containing "Additional assets from this ad"
                        # This might be a new modal or the expanded target_modal
                        details_modal = None
                        modals_after = await page.query_selector_all('div[role="dialog"]')

                        for modal in modals_after:
                            modal_text = await modal.inner_text()
                            if "additional assets from this ad" in modal_text.lower():
                                details_modal = modal
                                logger.debug("Found modal with 'Additional assets from this ad'")
                                break

                        if details_modal:
                            # Expand the "Additional assets" dropdown within the details modal
                            add_assets = await details_modal.query_selector(
                                ':has-text("Additional assets from this ad")'
                            )
                            if add_assets:
                                logger.debug("Clicking 'Additional assets from this ad' dropdown")
                                await add_assets.evaluate("el => el.click()")
                                await asyncio.sleep(1.5)

                            # Extract additional links ONLY from within this modal
                            result[
                                "additional_links"
                            ] = await self._extract_additional_links_from_modal(details_modal)
                            result["form_fields"] = await self._extract_form_fields_from_modal(
                                details_modal
                            )
                else:
                    # Fallback: No modal found, try the original approach
                    logger.debug("No modal with ad ID found, using fallback extraction")

                    # Click "See ad details" link
                    see_details_clicked = False
                    see_details_selectors = [
                        'text="See ad details"',
                        'span:has-text("See ad details")',
                    ]

                    for selector in see_details_selectors:
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0:
                                await element.evaluate("el => el.click()")
                                logger.debug(f"Clicked 'See ad details' using selector: {selector}")
                                see_details_clicked = True
                                break
                        except Exception as e:
                            logger.debug(f"Selector {selector} failed: {e}")
                            continue

                    if see_details_clicked:
                        await asyncio.sleep(2)

                    # Extract using page-wide selectors
                    result.update(await self._extract_timing_info(page))
                    result["platforms"] = await self._extract_platforms(page)
                    result.update(await self._extract_ad_content(page))
                    await self._expand_additional_assets(page)
                    result["additional_links"] = await self._extract_additional_links(page)
                    result["form_fields"] = await self._extract_form_fields(page)

                await context.close()

            except Exception as e:
                logger.error(f"Failed to scrape ad details for {ad_library_id}: {e}")

            finally:
                await browser.close()

        # Add rate limiting delay
        await asyncio.sleep(random.uniform(1.0, 2.0))

        return result

    async def _extract_timing_info_from_text(self, text: str) -> dict[str, Any]:
        """Extract timing info from text content."""
        result: dict[str, Any] = {
            "started_running_date": None,
            "total_active_time": None,
        }

        # Parse "Started running on" date
        date_match = re.search(r"Started running on (\d{1,2} \w+ \d{4})", text)
        if date_match:
            date_str = date_match.group(1)
            try:
                parsed_date = datetime.strptime(date_str, "%d %b %Y")
                result["started_running_date"] = parsed_date.date()
            except ValueError:
                logger.debug(f"Could not parse date: {date_str}")

        # Extract "Total active time"
        time_match = re.search(r"Total active time[:\s·]+([^\n]+)", text)
        if time_match:
            result["total_active_time"] = time_match.group(1).strip()

        return result

    async def _extract_ad_content_from_modal(self, modal) -> dict[str, Any]:
        """Extract ad content from modal element."""
        result: dict[str, Any] = {
            "primary_text": None,
            "link_headline": None,
            "link_description": None,
            "cta_text": None,
        }

        try:
            # The modal structure (from debug output):
            # - Primary text: "Protect your home and the planet..."
            # - Domain: "FB.ME"
            # - Link headline: "💰Save Money, Enjoy Clean Water"
            # - Link description: "Fresh, filtered water for Australian homes."
            # - CTA: "Get offer"

            # Extract primary text - look for the main description
            # It's typically in a div with white-space: pre-wrap or line-clamp
            primary_selectors = [
                'div[style*="white-space: pre-wrap"]',
                'div[style*="-webkit-line-clamp: 7"]',
                'div[style*="line-height: 16px"][style*="max-height: 112px"]',
            ]

            for selector in primary_selectors:
                els = await modal.query_selector_all(selector)
                for el in els:
                    text = await el.inner_text()
                    text = text.strip()
                    # Primary text should be substantive and not a navigation item
                    if (
                        text
                        and len(text) > 40
                        and not text.lower().startswith(("sponsored", "fb.me", "http"))
                    ):
                        # Skip if it looks like a CTA or short label
                        if text.lower() not in ["get offer", "learn more", "shop now", "sign up"]:
                            result["primary_text"] = text
                            break
                if result["primary_text"]:
                    break

            # Extract link headline and description
            # These are in elements with -webkit-line-clamp: 2 and line-height: 14px
            link_elements = await modal.query_selector_all('div[style*="-webkit-line-clamp: 2"]')
            link_texts = []

            for el in link_elements:
                text = await el.inner_text()
                text = text.strip()
                # Skip empty, primary text, "Sponsored", and domain labels
                if (
                    text
                    and len(text) > 3
                    and text.lower() not in ["sponsored", "fb.me", ""]
                    and text != result.get("primary_text")
                    and not text.startswith("http")
                    and not text.startswith("www.")
                ):
                    link_texts.append(text)

            # Assign headline and description based on order and characteristics
            for text in link_texts:
                if not result["link_headline"]:
                    result["link_headline"] = text
                elif not result["link_description"] and text != result["link_headline"]:
                    result["link_description"] = text
                    break

            # Extract CTA button text
            cta_keywords = {
                "get offer",
                "learn more",
                "shop now",
                "sign up",
                "get quote",
                "book now",
                "contact us",
                "apply now",
                "download",
                "subscribe",
                "get started",
                "see more",
                "buy now",
                "order now",
                "call now",
            }

            # Look in the modal for CTA elements
            all_text_in_modal = await modal.inner_text()
            for keyword in cta_keywords:
                if keyword in all_text_in_modal.lower():
                    # Find the exact casing from the modal
                    idx = all_text_in_modal.lower().find(keyword)
                    result["cta_text"] = all_text_in_modal[idx : idx + len(keyword)].strip()
                    # Capitalize properly
                    result["cta_text"] = result["cta_text"].title()
                    break

        except Exception as e:
            logger.debug(f"Error extracting ad content from modal: {e}")

        return result

    async def _extract_platforms_from_modal(self, modal) -> list[str]:
        """Extract platforms from modal element."""
        platforms = []

        try:
            modal_html = await modal.inner_html()
            modal_text = await modal.inner_text()

            # Check for platform indicators
            # Facebook is almost always present
            if "facebook" in modal_html.lower() or "Platforms" in modal_text:
                platforms.append("facebook")

            # Check for Instagram
            if "instagram" in modal_html.lower():
                platforms.append("instagram")

            # Check for Messenger
            if "messenger" in modal_html.lower():
                platforms.append("messenger")

            # Default to facebook if we couldn't detect any
            if not platforms:
                platforms.append("facebook")

        except Exception as e:
            logger.debug(f"Error extracting platforms from modal: {e}")
            platforms.append("facebook")

        return platforms

    async def _extract_timing_info(self, page: Page) -> dict[str, Any]:
        """Extract 'Started running on' date and 'Total active time' from ad details."""
        result: dict[str, Any] = {
            "started_running_date": None,
            "total_active_time": None,
        }

        try:
            # Look for timing text - typically in format:
            # "Started running on 19 Jan 2026 · Total active time 4 hrs"
            timing_elements = await page.query_selector_all("span")

            for element in timing_elements:
                text = await element.inner_text()
                text = text.strip()

                # Parse "Started running on" date
                if "Started running on" in text:
                    # Extract date portion
                    date_match = re.search(
                        r"Started running on (\d{1,2} \w+ \d{4})",
                        text,
                    )
                    if date_match:
                        date_str = date_match.group(1)
                        try:
                            parsed_date = datetime.strptime(date_str, "%d %b %Y")
                            result["started_running_date"] = parsed_date.date()
                        except ValueError:
                            logger.debug(f"Could not parse date: {date_str}")

                    # Extract "Total active time" if in same element
                    time_match = re.search(
                        r"Total active time[:\s]+([^·\n]+)",
                        text,
                    )
                    if time_match:
                        result["total_active_time"] = time_match.group(1).strip()
                    break

            # If total active time not found, look separately
            if not result["total_active_time"]:
                for element in timing_elements:
                    text = await element.inner_text()
                    if "Total active time" in text:
                        time_match = re.search(r"Total active time[:\s]+(.+)", text)
                        if time_match:
                            result["total_active_time"] = time_match.group(1).strip()
                        break

        except Exception as e:
            logger.debug(f"Error extracting timing info: {e}")

        return result

    async def _extract_platforms(self, page: Page) -> list[str]:
        """Extract platforms where the ad runs (Facebook, Instagram, Messenger)."""
        platforms = []

        try:
            # Look for platform indicator text
            platform_text = await page.query_selector('span:has-text("Platforms")')
            if platform_text:
                parent = await platform_text.evaluate_handle("el => el.parentElement")
                if parent:
                    parent_text = await parent.inner_text()

                    # Check for each platform
                    if "facebook" in parent_text.lower() or await page.query_selector(
                        'a[href*="facebook.com/ads/library"]'
                    ):
                        platforms.append("facebook")

            # Check for platform icons/links
            fb_icon = await page.query_selector(
                'a[aria-label*="Facebook"], svg[aria-label*="Facebook"]'
            )
            if fb_icon and "facebook" not in platforms:
                platforms.append("facebook")

            ig_icon = await page.query_selector(
                'a[aria-label*="Instagram"], svg[aria-label*="Instagram"]'
            )
            if ig_icon:
                platforms.append("instagram")

            messenger_icon = await page.query_selector(
                'a[aria-label*="Messenger"], svg[aria-label*="Messenger"]'
            )
            if messenger_icon:
                platforms.append("messenger")

            # Fallback: check for platform letters/icons in Platforms section
            # Facebook uses F, Instagram uses camera icon, Messenger uses lightning
            if not platforms:
                platforms_section = await page.query_selector(
                    'div:has(> span:has-text("Platforms"))'
                )
                if platforms_section:
                    section_html = await platforms_section.inner_html()
                    # Simple heuristic based on common patterns
                    if "facebook" in section_html.lower():
                        platforms.append("facebook")
                    if "instagram" in section_html.lower():
                        platforms.append("instagram")
                    if "messenger" in section_html.lower():
                        platforms.append("messenger")

            # Default to facebook if we couldn't detect any
            if not platforms:
                platforms.append("facebook")

        except Exception as e:
            logger.debug(f"Error extracting platforms: {e}")
            platforms.append("facebook")  # Default fallback

        return platforms

    async def _extract_ad_content(self, page: Page) -> dict[str, Any]:
        """Extract primary text, link headline, link description, and CTA."""
        result: dict[str, Any] = {
            "primary_text": None,
            "link_headline": None,
            "link_description": None,
            "cta_text": None,
        }

        try:
            # Look for the modal/ad details panel
            # Based on screenshots, the structure is:
            # - Primary text (description) is in a div with line-clamp style
            # - Below the media is the link preview section with:
            #   - Domain label (FB.ME)
            #   - Link headline (emoji + text like "Save Money, Enjoy Clean Water")
            #   - Link description ("Fresh, filtered water for Australian homes.")
            #   - CTA button (Get offer)

            # Get all text content from the modal to understand structure
            _modal = page.locator('div[role="dialog"]').first  # noqa: F841

            # Primary text - the ad copy/description shown above the media
            # Look for the specific style pattern from screenshots
            primary_selectors = [
                'div[style*="white-space: pre-wrap"]',
                'div[style*="-webkit-line-clamp: 7"]',
                'div[style*="line-height: 20px"][style*="max-height: 140px"]',
            ]

            for selector in primary_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        text = await el.inner_text()
                        text = text.strip()
                        # Primary text is usually longer and contains the main message
                        if text and len(text) > 30 and not text.startswith("http"):
                            result["primary_text"] = text
                            break
                    if result["primary_text"]:
                        break
                except Exception:
                    continue

            # Link preview section - find the section with the domain label (FB.ME)
            # and extract headline + description from there
            # Based on screenshot: link headline has emoji like "💰Save Money..."
            # Description is "Fresh, filtered water for Australian homes."

            # Look for divs that contain the link preview structure
            # The headline usually has emoji and is styled differently
            link_elements = await page.query_selector_all('div[style*="-webkit-line-clamp: 2"]')
            link_texts = []
            for el in link_elements:
                text = await el.inner_text()
                text = text.strip()
                if text and len(text) > 5:
                    link_texts.append(text)

            # Filter out primary text from link texts if it was captured
            if result["primary_text"]:
                link_texts = [t for t in link_texts if t != result["primary_text"]]

            # Typically: headline has emoji or is shorter, description is longer
            for text in link_texts:
                if not result["link_headline"]:
                    result["link_headline"] = text
                elif not result["link_description"] and text != result["link_headline"]:
                    result["link_description"] = text
                    break

            # CTA button text - look for common CTA button patterns
            cta_keywords = [
                "get offer",
                "learn more",
                "shop now",
                "sign up",
                "get quote",
                "book now",
                "contact us",
                "apply now",
                "download",
                "subscribe",
                "get started",
                "see more",
                "get offer",
                "buy now",
                "order now",
                "call now",
            ]

            # Look in buttons and clickable divs
            buttons = await page.query_selector_all('div[role="button"], button')
            for btn in buttons:
                text = await btn.inner_text()
                text = text.strip()
                if text and text.lower() in cta_keywords:
                    result["cta_text"] = text
                    break

            # If no CTA found, try looking for span with CTA text
            if not result["cta_text"]:
                spans = await page.query_selector_all("span")
                for span in spans:
                    text = await span.inner_text()
                    text = text.strip()
                    if text and text.lower() in cta_keywords:
                        result["cta_text"] = text
                        break

        except Exception as e:
            logger.debug(f"Error extracting ad content: {e}")

        return result

    async def _expand_additional_assets(self, page: Page) -> None:
        """Click the 'Additional assets from this ad' dropdown to expand it."""
        try:
            # Look for the dropdown trigger - it's a clickable div with heading role
            dropdown_selectors = [
                'div[role="heading"]:has-text("Additional assets from this ad")',
                'text="Additional assets from this ad"',
                'span:has-text("Additional assets from this ad")',
                'div:has-text("Additional assets from this ad"):not(:has(div:has-text("Additional assets")))',
            ]

            for selector in dropdown_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        # Use JavaScript click to bypass overlay issues
                        await element.evaluate("el => el.click()")
                        logger.debug(
                            f"Clicked 'Additional assets' dropdown using selector: {selector}"
                        )
                        await asyncio.sleep(1.5)  # Wait for content to expand
                        return
                except Exception as e:
                    logger.debug(f"Dropdown selector {selector} failed: {e}")
                    continue

            logger.debug("Could not find 'Additional assets from this ad' dropdown")

        except Exception as e:
            logger.debug(f"Error expanding additional assets: {e}")

    async def _extract_additional_links(self, page: Page) -> list[str]:
        """Extract additional URLs from the 'Additional assets' section."""
        links: list[str] = []

        try:
            # Based on screenshots, links are in a ul after "Links" heading
            # Look for the Links section specifically within the modal
            seen_urls: set[str] = set()

            # First, try to find links within the "Links" section of Additional assets
            # The structure is: heading "Links" followed by ul with li containing a tags
            link_headings = await page.query_selector_all('span:has-text("Links")')

            for heading in link_headings:
                # Get the parent container and look for links within it
                parent = await heading.evaluate_handle("el => el.closest('div')")
                if parent:
                    # Find the next ul sibling or links in the same container
                    _parent_html = await parent.inner_html()  # noqa: F841
                    # Look for anchor tags in nearby elements
                    sibling_links = await page.query_selector_all('ul li a[href^="http"]')
                    for link_el in sibling_links:
                        href = await link_el.get_attribute("href")
                        if href and href.startswith("http"):
                            # Skip Meta/Facebook internal URLs and status pages
                            if not any(
                                domain in href.lower()
                                for domain in [
                                    "facebook.com",
                                    "fb.com",
                                    "instagram.com",
                                    "meta.com",
                                    "metastatus.com",
                                    "/ads/library",
                                    "/policies",
                                    "/privacy",
                                ]
                            ):
                                if href not in seen_urls:
                                    seen_urls.add(href)
                                    links.append(href)

            # If no links found, try broader search for external URLs in the modal
            if not links:
                all_links = await page.query_selector_all('div[role="dialog"] a[href^="http"]')
                for link_el in all_links:
                    href = await link_el.get_attribute("href")
                    _link_text = await link_el.inner_text()  # noqa: F841
                    if href and href.startswith("http"):
                        # Skip internal Facebook URLs and navigation links
                        if not any(
                            domain in href.lower()
                            for domain in [
                                "facebook.com",
                                "fb.com",
                                "instagram.com",
                                "meta.com",
                                "metastatus.com",
                                "/ads/",
                                "/policies",
                                "/privacy",
                            ]
                        ):
                            if href not in seen_urls:
                                seen_urls.add(href)
                                links.append(href)

        except Exception as e:
            logger.debug(f"Error extracting additional links: {e}")

        return links

    async def _extract_form_fields(self, page: Page) -> dict[str, Any] | None:
        """Extract lead gen form fields from the 'Additional assets' section."""
        form_data: dict[str, Any] = {
            "intro_text": None,
            "questions": [],
            "fields": [],
            "terms_links": [],
            "thank_you_text": None,
        }

        has_form_content = False

        try:
            # Look for the "Text" section within "Additional assets from this ad"
            # This is where form field information appears for lead gen ads
            # Based on screenshots, the structure has a "Text" heading followed by a ul

            # First, find the "Text" heading within the modal
            text_heading = await page.query_selector('div[role="dialog"] span:has-text("Text")')

            if not text_heading:
                # No Text section means this is not a lead gen ad
                return None

            # Find the ul that follows the Text heading (contains form field info)
            # The ul should be within the same container section
            _text_container = await text_heading.evaluate_handle("el => el.closest('div[class]')")  # noqa: F841

            # Look for list items specifically within the Additional assets section
            # We need to find the ul that's part of the "Text" subsection
            form_list_items = []

            # Try to find the ul following the Text heading
            all_uls = await page.query_selector_all('div[role="dialog"] ul')
            for ul in all_uls:
                # Get the list items from this ul
                items = await ul.query_selector_all("li")
                for item in items:
                    text = await item.inner_text()
                    text = text.strip()

                    # Skip empty items and global navigation items
                    if not text:
                        continue

                    # Skip items that are clearly site navigation (Ad Library API, Privacy, Terms, Cookies)
                    skip_patterns = [
                        "ad library api",
                        "about ads",
                        "privacy",
                        "terms",
                        "cookies",
                        "report ad",
                        "why am i seeing",
                    ]
                    if any(skip in text.lower() for skip in skip_patterns):
                        continue

                    form_list_items.append((item, text))

            current_question = None
            current_options: list[str] = []

            for item, text in form_list_items:
                # Check if this is a link (Terms and Conditions for the advertiser, not Facebook)
                link_el = await item.query_selector('a[href^="http"]')
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href and not any(
                        domain in href.lower()
                        for domain in ["facebook.com", "fb.com", "instagram.com", "meta.com"]
                    ):
                        form_data["terms_links"].append(
                            {
                                "text": text,
                                "url": href,
                            }
                        )
                        has_form_content = True
                        continue

                # Detect question patterns (ends with ?)
                if text.endswith("?"):
                    # Save previous question if exists
                    if current_question:
                        form_data["questions"].append(
                            {
                                "question": current_question,
                                "options": current_options,
                            }
                        )
                        has_form_content = True

                    current_question = text
                    current_options = []
                    continue

                # Detect Yes/No options (must follow a question)
                if text.lower() in ["yes", "no"] and current_question:
                    current_options.append(text)
                    continue

                # Detect form field names (common patterns)
                field_patterns = [
                    "full name",
                    "email",
                    "phone",
                    "phone number",
                    "post code",
                    "postcode",
                    "zip",
                    "address",
                    "city",
                    "state",
                    "country",
                    "company",
                    "job title",
                    "website",
                ]
                # Match exact field names or field names at start of text
                if any(
                    text.lower() == pattern or text.lower().startswith(pattern)
                    for pattern in field_patterns
                ):
                    form_data["fields"].append(text)
                    has_form_content = True
                    continue

                # Detect intro text (usually first substantial text, often starts with "Fill in")
                if not form_data["intro_text"] and len(text) > 30 and "?" not in text:
                    # Check for common intro patterns
                    intro_patterns = [
                        "fill in",
                        "complete",
                        "enter your",
                        "provide your",
                        "get in touch",
                    ]
                    if any(pattern in text.lower() for pattern in intro_patterns):
                        form_data["intro_text"] = text
                        has_form_content = True
                        continue

                # Detect thank you message
                thank_patterns = ["thank", "done", "submitted", "all done", "we'll be in touch"]
                if any(pattern in text.lower() for pattern in thank_patterns):
                    form_data["thank_you_text"] = text
                    has_form_content = True
                    continue

            # Save last question if exists
            if current_question:
                form_data["questions"].append(
                    {
                        "question": current_question,
                        "options": current_options,
                    }
                )
                has_form_content = True

        except Exception as e:
            logger.debug(f"Error extracting form fields: {e}")

        return form_data if has_form_content else None

    async def _extract_additional_links_from_modal(self, modal) -> list[str]:
        """Extract additional URLs from within a specific modal element."""
        links: list[str] = []
        seen_urls: set[str] = set()

        try:
            # Look for links within the modal that are advertiser URLs
            # These appear after expanding "Additional assets from this ad"
            all_links = await modal.query_selector_all('a[href^="http"]')

            for link_el in all_links:
                href = await link_el.get_attribute("href")
                if not href:
                    continue

                # Skip Meta/Facebook internal URLs
                skip_domains = [
                    "facebook.com",
                    "fb.com",
                    "fb.me",
                    "instagram.com",
                    "meta.com",
                    "metastatus.com",
                    "l.facebook.com",
                    "/ads/",
                    "/policies",
                    "/privacy",
                ]
                if any(domain in href.lower() for domain in skip_domains):
                    continue

                # Parse Facebook redirect URLs to get actual destination
                if "l.facebook.com/l.php" in href:
                    # Extract the actual URL from the redirect
                    from urllib.parse import parse_qs, urlparse

                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    actual_url = params.get("u", [None])[0]
                    if actual_url:
                        from urllib.parse import unquote

                        href = unquote(actual_url)

                if href not in seen_urls:
                    seen_urls.add(href)
                    links.append(href)

        except Exception as e:
            logger.debug(f"Error extracting additional links from modal: {e}")

        return links

    async def _extract_form_fields_from_modal(self, modal) -> dict[str, Any] | None:
        """Extract lead gen form fields from within a specific modal element."""
        form_data: dict[str, Any] = {
            "intro_text": None,
            "questions": [],
            "fields": [],
            "terms_links": [],
            "thank_you_text": None,
        }

        has_form_content = False

        try:
            # Look for the "Text" section within the modal
            text_heading = await modal.query_selector('span:has-text("Text")')

            if not text_heading:
                # No Text section means this is not a lead gen ad
                return None

            # Find list items within the modal
            form_list_items = []
            all_uls = await modal.query_selector_all("ul")

            for ul in all_uls:
                items = await ul.query_selector_all("li")
                for item in items:
                    text = await item.inner_text()
                    text = text.strip()

                    # Skip empty items and navigation items
                    if not text:
                        continue

                    skip_patterns = [
                        "ad library api",
                        "about ads",
                        "privacy",
                        "terms",
                        "cookies",
                        "report ad",
                        "why am i seeing",
                        "system status",
                    ]
                    if any(skip in text.lower() for skip in skip_patterns):
                        continue

                    form_list_items.append((item, text))

            current_question = None
            current_options: list[str] = []

            for item, text in form_list_items:
                # Check if this is a link (Terms/Privacy for advertiser)
                link_el = await item.query_selector('a[href^="http"]')
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href and not any(
                        domain in href.lower()
                        for domain in [
                            "facebook.com",
                            "fb.com",
                            "instagram.com",
                            "meta.com",
                            "l.facebook.com",
                        ]
                    ):
                        # Decode Facebook redirect URLs
                        if "l.facebook.com/l.php" in href:
                            from urllib.parse import parse_qs, unquote, urlparse

                            parsed = urlparse(href)
                            params = parse_qs(parsed.query)
                            actual_url = params.get("u", [None])[0]
                            if actual_url:
                                href = unquote(actual_url)

                        form_data["terms_links"].append(
                            {
                                "text": text,
                                "url": href,
                            }
                        )
                        has_form_content = True
                        continue

                # Detect question patterns
                if text.endswith("?"):
                    if current_question:
                        form_data["questions"].append(
                            {
                                "question": current_question,
                                "options": current_options,
                            }
                        )
                        has_form_content = True

                    current_question = text
                    current_options = []
                    continue

                # Detect Yes/No options
                if text.lower() in ["yes", "no"] and current_question:
                    current_options.append(text)
                    continue

                # Detect form field names
                field_patterns = [
                    "full name",
                    "email",
                    "phone",
                    "phone number",
                    "post code",
                    "postcode",
                    "zip",
                    "address",
                    "city",
                    "state",
                    "country",
                    "company",
                    "job title",
                    "website",
                ]
                if any(
                    text.lower() == pattern or text.lower().startswith(pattern)
                    for pattern in field_patterns
                ):
                    form_data["fields"].append(text)
                    has_form_content = True
                    continue

                # Detect intro text
                if not form_data["intro_text"] and len(text) > 30 and "?" not in text:
                    intro_patterns = [
                        "fill in",
                        "complete",
                        "enter your",
                        "provide your",
                        "get in touch",
                    ]
                    if any(pattern in text.lower() for pattern in intro_patterns):
                        form_data["intro_text"] = text
                        has_form_content = True
                        continue

                # Detect thank you message
                thank_patterns = ["thank", "done", "submitted", "all done", "we'll be in touch"]
                if any(pattern in text.lower() for pattern in thank_patterns):
                    form_data["thank_you_text"] = text
                    has_form_content = True
                    continue

            # Save last question if exists
            if current_question:
                form_data["questions"].append(
                    {
                        "question": current_question,
                        "options": current_options,
                    }
                )
                has_form_content = True

        except Exception as e:
            logger.debug(f"Error extracting form fields from modal: {e}")

        return form_data if has_form_content else None

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
                snapshot_section = html_content[snapshot_start : snapshot_start + 3000]
                body_pattern = r'"body":"([^"]*)"'
                body_match = re.search(body_pattern, snapshot_section)
                if body_match:
                    try:
                        body_text = body_match.group(1).encode("utf-8").decode("unicode_escape")
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
                            details["carousel_items"].append(
                                {
                                    "index": i,
                                    "url": src,
                                    "type": "image",
                                }
                            )

                    # Get all videos in carousel
                    videos = await carousel_container.query_selector_all("video")
                    for i, video in enumerate(videos):
                        src = await video.get_attribute("src")
                        poster = await video.get_attribute("poster")
                        if src:
                            details["carousel_items"].append(
                                {
                                    "index": len(details["carousel_items"]),
                                    "url": src,
                                    "type": "video",
                                    "poster": poster,
                                }
                            )
                else:
                    # Single creative - determine type from page JSON data
                    # The Ad Library page shows multiple ads, so we need to identify
                    # the specific ad's creative type from the JSON data
                    content = await page.content()

                    # Extract ad ID from URL to find ad-specific data
                    ad_id = None
                    id_match = re.search(r"[?&]id=(\d+)", snapshot_url)
                    if id_match:
                        ad_id = id_match.group(1)

                    has_video_url = False
                    has_image_url = False
                    video_url = None
                    image_url = None

                    if ad_id:
                        # Search near the ad ID for video/image URL patterns
                        for match in re.finditer(ad_id, content):
                            pos = match.start()
                            window_start = max(0, pos - 2000)
                            window_end = min(len(content), pos + 3000)
                            window = content[window_start:window_end]

                            # Video URL patterns
                            if not video_url:
                                video_match = re.search(r'"video_sd_url"\s*:\s*"([^"]+)"', window)
                                if video_match:
                                    has_video_url = True
                                    video_url = (
                                        video_match.group(1)
                                        .replace("\\u0025", "%")
                                        .replace("\\/", "/")
                                    )

                            if not video_url:
                                video_match = re.search(r'"video_hd_url"\s*:\s*"([^"]+)"', window)
                                if video_match:
                                    has_video_url = True
                                    video_url = (
                                        video_match.group(1)
                                        .replace("\\u0025", "%")
                                        .replace("\\/", "/")
                                    )

                            if not video_url:
                                video_match = re.search(r'"playable_url"\s*:\s*"([^"]+)"', window)
                                if video_match:
                                    has_video_url = True
                                    video_url = (
                                        video_match.group(1)
                                        .replace("\\u0025", "%")
                                        .replace("\\/", "/")
                                    )

                            # Image URL patterns
                            if not image_url:
                                image_match = re.search(
                                    r'"resized_image_url"\s*:\s*"([^"]+)"', window
                                )
                                if image_match:
                                    has_image_url = True
                                    image_url = (
                                        image_match.group(1)
                                        .replace("\\u0025", "%")
                                        .replace("\\/", "/")
                                    )

                            if not image_url:
                                image_match = re.search(
                                    r'"watermarked_resized_image_url"\s*:\s*"([^"]+)"',
                                    window,
                                )
                                if image_match:
                                    has_image_url = True
                                    image_url = (
                                        image_match.group(1)
                                        .replace("\\u0025", "%")
                                        .replace("\\/", "/")
                                    )

                    # Decide based on JSON data - video ads have video URLs
                    if has_video_url and video_url:
                        details["creative_urls"].append({"url": video_url, "type": "video"})
                    elif has_image_url and image_url and not has_video_url:
                        details["creative_urls"].append({"url": image_url, "type": "image"})
                    else:
                        # Fallback to DOM inspection
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
        from tavily import AsyncTavilyClient

        from app.config import get_settings

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
                "/login",
                "/help",
                "/policies",
                "/privacy",
                "business.facebook",
                "developers.facebook",
                "/watch",
                "/groups",
                "/events",
                "/marketplace",
                "/share",
                "/sharer",
                "/dialog",
                "/plugins",
            ]

            for i, result in enumerate(results, 1):
                url = result.get("url", "")
                title = result.get("title", "")[:60]
                logger.debug(f"  Result {i}: {url} - {title}")

                if "facebook.com" in url and not facebook_link:
                    # Skip non-page URLs
                    if any(skip in url.lower() for skip in skip_patterns):
                        logger.debug("    -> SKIPPED (matches exclusion pattern)")
                        continue
                    logger.debug("    -> SELECTED")
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
                    page_id = await self._get_page_id_from_transparency(page, final_url, timeout_ms)
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

    async def _get_page_id_from_transparency(
        self, page: Page, profile_url: str, timeout_ms: int
    ) -> str | None:
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
                if re.match(r"^\d{10,}$", span_text.strip()):
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

                # Page Transparency section (direct URL)
                page_id = await self._get_page_id_from_transparency(page, profile_url, timeout_ms)
                if page_id:
                    logger.info(f"Found page ID via transparency section: {page_id}")
                    await context.close()
                    return page_id

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
        # Extract ad ID from URL to find ad-specific data
        ad_id = None
        id_match = re.search(r"[?&]id=(\d+)", snapshot_url)
        if id_match:
            ad_id = id_match.group(1)

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

                content = await page.content()

                # PRIORITY 1: Determine media type from JSON data in page source
                # This is the most reliable method because it uses ad-specific data
                # The Ad Library page contains multiple ads, so we need to find
                # the data for THIS specific ad by looking near the ad ID
                has_video_url = False
                has_image_url = False
                video_url = None
                image_url = None

                if ad_id:
                    # Search near the ad ID for video/image URL patterns
                    for match in re.finditer(ad_id, content):
                        pos = match.start()
                        # Look at a window around the ad ID
                        window_start = max(0, pos - 2000)
                        window_end = min(len(content), pos + 3000)
                        window = content[window_start:window_end]

                        # Video URL patterns - these indicate a video ad
                        video_match = re.search(r'"video_sd_url"\s*:\s*"([^"]+)"', window)
                        if video_match:
                            has_video_url = True
                            video_url = (
                                video_match.group(1).replace("\\u0025", "%").replace("\\/", "/")
                            )

                        if not video_url:
                            video_match = re.search(r'"video_hd_url"\s*:\s*"([^"]+)"', window)
                            if video_match:
                                has_video_url = True
                                video_url = (
                                    video_match.group(1).replace("\\u0025", "%").replace("\\/", "/")
                                )

                        if not video_url:
                            video_match = re.search(r'"playable_url"\s*:\s*"([^"]+)"', window)
                            if video_match:
                                has_video_url = True
                                video_url = (
                                    video_match.group(1).replace("\\u0025", "%").replace("\\/", "/")
                                )

                        # Image URL patterns
                        image_match = re.search(r'"resized_image_url"\s*:\s*"([^"]+)"', window)
                        if image_match:
                            has_image_url = True
                            if not image_url:
                                image_url = (
                                    image_match.group(1).replace("\\u0025", "%").replace("\\/", "/")
                                )

                        if not image_url:
                            image_match = re.search(
                                r'"watermarked_resized_image_url"\s*:\s*"([^"]+)"',
                                window,
                            )
                            if image_match:
                                has_image_url = True
                                image_url = (
                                    image_match.group(1).replace("\\u0025", "%").replace("\\/", "/")
                                )

                # Decide based on what we found
                # Video ads have video URLs; image ads have only image URLs
                if has_video_url and video_url:
                    await context.close()
                    return video_url, "video"
                elif has_image_url and image_url and not has_video_url:
                    await context.close()
                    return image_url, "image"

                # PRIORITY 2: Fallback to DOM element inspection
                # Only use this if JSON approach failed
                # Check for video element
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
                    "img._8jnf",
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

                # PRIORITY 3: Last resort - global pattern search
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
                        items.append(
                            {
                                "url": result.get("url", ""),
                                "title": result.get("title", ""),
                                "content": result.get("content", "")[:200],
                            }
                        )

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
                    selections.append(
                        {
                            "competitor_name": name,
                            "selected_url": None,
                            "confidence": "low",
                            "needs_manual_review": True,
                            "reason": "No search results found",
                        }
                    )

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
            "/login",
            "/help",
            "/policies",
            "/privacy",
            "business.facebook",
            "developers.facebook",
            "/watch",
            "/groups",
            "/events",
            "/marketplace",
            "/share",
            "/sharer",
            "/dialog",
            "/plugins",
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

            selections.append(
                {
                    "competitor_name": name,
                    "selected_url": selected_url,
                    "confidence": "low",
                    "needs_manual_review": selected_url is None,
                    "reason": "Fallback selection (GPT unavailable)",
                }
            )

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
            sel
            for sel in url_selections
            if sel.get("selected_url") and not sel.get("needs_manual_review")
        ]
        manual_review = [
            sel
            for sel in url_selections
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
                                logger.debug(
                                    f"Found page ID via transparency for '{name}': {page_id}"
                                )
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
                                logger.debug(
                                    f"Found page ID via regex for '{name}': {best_page_id}"
                                )
                                await context.close()
                                return name, best_page_id, final_url

                            logger.warning(
                                f"Could not extract page ID for '{name}' from {final_url}"
                            )
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
