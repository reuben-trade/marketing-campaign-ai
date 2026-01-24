#!/usr/bin/env python3
"""
Test script for Facebook Page ID extraction from transparency section.

This script tests the _get_page_id_from_transparency method by prompting
the user for a Facebook URL and attempting to extract the Page ID.

Run with: python scripts/test_page_id_extraction.py
"""

import asyncio
import logging
import sys

sys.path.insert(0, "/home/rjs/Desktop/Projects/marketing-ai")

from playwright.async_api import async_playwright

from app.services.ad_library_scraper import AdLibraryScraper


async def test_extraction_from_url(facebook_url: str) -> tuple[str | None, str | None]:
    """
    Test Page ID extraction from a given Facebook URL.

    Args:
        facebook_url: The Facebook page URL to test

    Returns:
        Tuple of (page_id, error_message)
    """
    scraper = AdLibraryScraper()

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

            # First navigate to the main page to handle any redirects
            print(f"\n  Navigating to: {facebook_url}")
            await page.goto(facebook_url, timeout=30000, wait_until="networkidle")

            final_url = page.url
            print(f"  Final URL: {final_url}")

            # Now try to extract the Page ID using the transparency method
            print("\n  Attempting Page ID extraction from transparency section...")
            page_id = await scraper._get_page_id_from_transparency(page, final_url, 30000)

            await context.close()
            return page_id, None

        except Exception as e:
            return None, str(e)

        finally:
            await browser.close()


async def main():
    # Enable verbose logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n" + "=" * 70)
    print("FACEBOOK PAGE ID EXTRACTION TEST")
    print("=" * 70)
    print("\nThis script tests the Page ID extraction from the transparency section.")
    print("Enter a Facebook page URL to test (e.g., https://www.facebook.com/McDonalds)")

    while True:
        print("\n" + "-" * 70)
        facebook_url = input("\nEnter Facebook URL (or 'q' to quit): ").strip()

        if facebook_url.lower() == 'q':
            print("\nExiting...")
            break

        if not facebook_url:
            print("  No URL provided. Please try again.")
            continue

        # Normalize URL if needed
        if not facebook_url.startswith("http"):
            facebook_url = f"https://{facebook_url}"

        if "facebook.com" not in facebook_url:
            print("  Invalid URL. Please enter a Facebook page URL.")
            continue

        print(f"\n  Testing extraction for: {facebook_url}")

        page_id, error = await test_extraction_from_url(facebook_url)

        print("\n" + "=" * 70)
        print("RESULT")
        print("=" * 70)

        if page_id:
            print(f"\n  ✓ Page ID found: {page_id}")
            print(f"\n  Ad Library URL:")
            print(f"    https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=AU&view_all_page_id={page_id}")
        elif error:
            print(f"\n  ✗ Error: {error}")
        else:
            print(f"\n  ✗ Page ID not found")
            print("    The extraction method could not find the Page ID.")
            print("    This may require manual investigation.")


if __name__ == "__main__":
    asyncio.run(main())
