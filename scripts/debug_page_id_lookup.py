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

    company_name = input("\nEnter business name: ").strip()

    if not company_name:
        print("No business name provided. Exiting.")
        return

    print(f"\nSearching for: {company_name}\n")

    scraper = AdLibraryScraper()
    page_id, facebook_url = await scraper.search_page_id_by_name(company_name)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
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


if __name__ == "__main__":
    asyncio.run(main())
