#!/usr/bin/env python3
"""
Debug script for testing Facebook Page ID lookup.

Run with: python scripts/debug_page_id_lookup.py
"""

import asyncio
import logging
import sys

sys.path.insert(0, "/home/rjs/Desktop/Projects/marketing-ai")

from app.services.ad_library_scraper import AdLibraryScraper


async def test_single():
    """Test single page ID lookup."""
    print("\n" + "=" * 60)
    print("SINGLE PAGE ID LOOKUP - DEBUG MODE")
    print("=" * 60)

    company_name = input("\nEnter business name: ").strip()

    if not company_name:
        print("No business name provided.")
        return

    print(f"\nSearching for: {company_name}\n")

    scraper = AdLibraryScraper()
    page_id, facebook_url = await scraper.search_page_id_by_name(company_name)

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)

    if page_id:
        print(f"  Page ID: {page_id}")
        print(f"  Facebook URL: {facebook_url}")
        print(f"  Ad Library URL: {scraper.build_ad_library_url(page_id)}")
    else:
        print(f"  Page ID: Not found")
        if facebook_url:
            print(f"  Facebook URL (manual review): {facebook_url}")
        else:
            print(f"  No Facebook page found")


async def test_batch():
    """Test batch page ID lookup."""
    print("\n" + "=" * 60)
    print("BATCH PAGE ID LOOKUP - DEBUG MODE")
    print("=" * 60)

    print("\nEnter company names (comma-separated):")
    names_input = input("> ").strip()

    if not names_input:
        print("No company names provided.")
        return

    company_names = [name.strip() for name in names_input.split(",") if name.strip()]

    print(f"\nSearching for {len(company_names)} companies: {company_names}\n")

    scraper = AdLibraryScraper()
    results = await scraper.batch_search_page_ids(company_names)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    for name, (page_id, facebook_url) in results.items():
        print(f"\n  {name}:")
        if page_id:
            print(f"    Page ID: {page_id}")
            print(f"    Facebook URL: {facebook_url}")
            print(f"    Ad Library URL: {scraper.build_ad_library_url(page_id)}")
        else:
            print(f"    Page ID: Not found")
            if facebook_url:
                print(f"    Facebook URL (manual review): {facebook_url}")
            else:
                print(f"    No Facebook page found")


async def main():
    # Enable verbose logging for the scraper
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n" + "=" * 60)
    print("FACEBOOK PAGE ID LOOKUP - DEBUG MODE")
    print("=" * 60)

    print("\nSelect mode:")
    print("  1. Single lookup")
    print("  2. Batch lookup")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        await test_single()
    elif choice == "2":
        await test_batch()
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
