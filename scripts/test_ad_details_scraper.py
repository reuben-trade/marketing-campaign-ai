#!/usr/bin/env python3
"""
Test script for ad details scraping.

Usage:
    # Test with a specific ad library ID and page ID
    python scripts/test_ad_details_scraper.py --ad-id 1225940729470116 --page-id 156986678282507

    # Test with just an ad library URL
    python scripts/test_ad_details_scraper.py --url "https://www.facebook.com/ads/library/?id=1225940729470116"

    # Test with a full ad library URL (extracts page_id from URL)
    python scripts/test_ad_details_scraper.py --url "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=AU&id=1225940729470116&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id=156986678282507"
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ad_library_scraper import AdLibraryScraper


def parse_ad_library_url(url: str) -> tuple[str | None, str | None]:
    """Extract ad_id and page_id from an Ad Library URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    ad_id = params.get("id", [None])[0]
    page_id = params.get("view_all_page_id", [None])[0]

    return ad_id, page_id


async def test_scrape_ad_details(
    ad_library_id: str,
    page_id: str,
    country: str = "AU",
    verbose: bool = True,
) -> dict:
    """
    Test the scrape_ad_details method.

    Args:
        ad_library_id: Meta Ad Library ID
        page_id: Facebook Page ID
        country: Country code
        verbose: Print detailed output

    Returns:
        Dictionary with scraped ad details
    """
    scraper = AdLibraryScraper()

    print(f"\n{'='*60}")
    print(f"Testing Ad Details Scraper")
    print(f"{'='*60}")
    print(f"Ad Library ID: {ad_library_id}")
    print(f"Page ID: {page_id}")
    print(f"Country: {country}")
    print(f"{'='*60}\n")

    # Build the URL for reference
    url = scraper.build_ad_details_url(ad_library_id, page_id, country)
    print(f"URL: {url}\n")

    print("Scraping ad details...")
    details = await scraper.scrape_ad_details(
        ad_library_id=ad_library_id,
        page_id=page_id,
        country=country,
    )

    if verbose:
        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}\n")

        # Timing info
        print("TIMING INFO:")
        print(f"  Started Running Date: {details.get('started_running_date')}")
        print(f"  Total Active Time: {details.get('total_active_time')}")

        # Platforms
        print(f"\nPLATFORMS: {details.get('platforms', [])}")

        # Ad content
        print("\nAD CONTENT:")
        primary_text = details.get("primary_text")
        if primary_text:
            # Truncate for display
            display_text = primary_text[:200] + "..." if len(primary_text) > 200 else primary_text
            print(f"  Primary Text: {display_text}")
        else:
            print("  Primary Text: None")

        print(f"  Link Headline: {details.get('link_headline')}")
        print(f"  Link Description: {details.get('link_description')}")
        print(f"  CTA Text: {details.get('cta_text')}")

        # Additional links
        print("\nADDITIONAL LINKS:")
        links = details.get("additional_links", [])
        if links:
            for i, link in enumerate(links, 1):
                print(f"  {i}. {link}")
        else:
            print("  None found")

        # Form fields
        print("\nFORM FIELDS:")
        form_fields = details.get("form_fields")
        if form_fields:
            print(f"  Intro Text: {form_fields.get('intro_text')}")

            questions = form_fields.get("questions", [])
            if questions:
                print("  Questions:")
                for q in questions:
                    print(f"    - {q.get('question')}")
                    if q.get("options"):
                        print(f"      Options: {q.get('options')}")

            fields = form_fields.get("fields", [])
            if fields:
                print(f"  Form Fields: {fields}")

            terms_links = form_fields.get("terms_links", [])
            if terms_links:
                print("  Terms/Privacy Links:")
                for tl in terms_links:
                    print(f"    - {tl.get('text')}: {tl.get('url')}")

            if form_fields.get("thank_you_text"):
                print(f"  Thank You Text: {form_fields.get('thank_you_text')}")
        else:
            print("  None found (not a lead gen ad)")

        # Raw JSON output
        print(f"\n{'='*60}")
        print("RAW JSON OUTPUT")
        print(f"{'='*60}")
        print(json.dumps(details, indent=2, default=str))

    return details


async def test_multiple_ads(ad_ids: list[tuple[str, str]], country: str = "AU") -> None:
    """Test scraping multiple ads."""
    scraper = AdLibraryScraper()

    print(f"\n{'='*60}")
    print(f"Testing {len(ad_ids)} ads")
    print(f"{'='*60}\n")

    results = []
    for ad_library_id, page_id in ad_ids:
        print(f"\nScraping ad {ad_library_id}...")
        try:
            details = await scraper.scrape_ad_details(
                ad_library_id=ad_library_id,
                page_id=page_id,
                country=country,
            )
            results.append({
                "ad_library_id": ad_library_id,
                "success": True,
                "details": details,
            })
            print(f"  ✓ Success - Found: {len(details.get('additional_links', []))} links, "
                  f"form_fields: {'Yes' if details.get('form_fields') else 'No'}")
        except Exception as e:
            results.append({
                "ad_library_id": ad_library_id,
                "success": False,
                "error": str(e),
            })
            print(f"  ✗ Failed: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in results if r["success"])
    print(f"Total: {len(results)}, Success: {successful}, Failed: {len(results) - successful}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test ad details scraping from Meta Ad Library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--ad-id",
        help="Ad Library ID to scrape",
    )
    parser.add_argument(
        "--page-id",
        help="Facebook Page ID",
    )
    parser.add_argument(
        "--url",
        help="Full Ad Library URL (will extract ad-id and page-id from it)",
    )
    parser.add_argument(
        "--country",
        default="AU",
        help="Country code (default: AU)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (just JSON)",
    )

    args = parser.parse_args()

    # Parse URL if provided
    ad_id = args.ad_id
    page_id = args.page_id

    if args.url:
        url_ad_id, url_page_id = parse_ad_library_url(args.url)
        if url_ad_id:
            ad_id = url_ad_id
        if url_page_id:
            page_id = url_page_id

    # Validate inputs
    if not ad_id:
        print("Error: --ad-id or --url with id parameter required")
        sys.exit(1)

    if not page_id:
        print("Error: --page-id or --url with view_all_page_id parameter required")
        print("\nTip: You can find the page_id by:")
        print("  1. Going to the Facebook page")
        print("  2. Clicking 'Page Transparency' > 'See all'")
        print("  3. The numeric ID is shown there")
        print("\nOr provide a full Ad Library URL that includes view_all_page_id")
        sys.exit(1)

    # Run the test
    asyncio.run(test_scrape_ad_details(
        ad_library_id=ad_id,
        page_id=page_id,
        country=args.country,
        verbose=not args.quiet,
    ))


if __name__ == "__main__":
    main()
