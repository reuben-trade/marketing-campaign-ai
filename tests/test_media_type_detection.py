"""Test script to debug image vs video classification in Ad Library scraper."""

import asyncio
import re

from playwright.async_api import async_playwright

# Test URLs provided by user
IMAGE_AD_URL = "https://www.facebook.com/ads/library/?id=2150472312151855"
VIDEO_AD_URL = "https://www.facebook.com/ads/library/?id=869478225701965"


async def analyze_page_structure(page, ad_id: str) -> dict:
    """
    Analyze the DOM structure to understand how to find the specific ad.
    """
    result = {}

    # Save the page HTML for analysis
    content = await page.content()

    # Look for the ad ID in the page source and examine surrounding context
    # The ad ID should be present in data attributes or JSON payloads
    ad_id_positions = []
    start = 0
    while True:
        pos = content.find(ad_id, start)
        if pos == -1:
            break
        ad_id_positions.append(pos)
        start = pos + 1

    print(f"  Found ad ID {ad_id} at {len(ad_id_positions)} positions in page source")

    # For each occurrence, look at surrounding context
    for i, pos in enumerate(ad_id_positions[:5]):  # Check first 5
        context_start = max(0, pos - 200)
        context_end = min(len(content), pos + 200)
        context = content[context_start:context_end]

        # Check for media type indicators near this ad ID
        has_video_indicator = any(x in context.lower() for x in ["video", "playable", "mp4"])
        has_image_indicator = any(x in context.lower() for x in ["photo", "image", "jpg", "png"])

        if i == 0:
            print("  Context around first occurrence:")
            print(f"    Video indicators: {has_video_indicator}")
            print(f"    Image indicators: {has_image_indicator}")

    # Look for JSON data containing ad info
    # Facebook often embeds ad data in script tags or data attributes
    json_pattern = rf'"id"\s*:\s*"{ad_id}"[^}}]*"__typename"\s*:\s*"([^"]+)"'
    typename_match = re.search(json_pattern, content)
    if typename_match:
        result["typename_from_json"] = typename_match.group(1)
        print(f"  Found __typename in JSON: {typename_match.group(1)}")

    # Alternative pattern: __typename near ad_library_id
    alt_pattern = rf'"ad_library_id"\s*:\s*"{ad_id}"[^}}]*?"__typename"\s*:\s*"([^"]+)"'
    alt_match = re.search(alt_pattern, content)
    if alt_match:
        result["typename_alt"] = alt_match.group(1)
        print(f"  Found __typename (alt pattern): {alt_match.group(1)}")

    # Look for creative type in nearby JSON
    # Pattern: find the ad data block and look for video/image indicators
    ad_block_pattern = rf"{ad_id}[^{{}}]{{0,2000}}"
    ad_block_match = re.search(ad_block_pattern, content)
    if ad_block_match:
        ad_block = ad_block_match.group(0)
        if "video_sd_url" in ad_block or "video_hd_url" in ad_block or "playable_url" in ad_block:
            result["has_video_urls_in_block"] = True
            print("  Found video URLs in ad data block")
        if "resized_image_url" in ad_block or "watermarked_resized_image_url" in ad_block:
            result["has_image_urls_in_block"] = True
            print("  Found image URLs in ad data block")

    return result


async def check_creative_in_first_ad_card(page) -> dict:
    """
    The first ad card on the page should be the specific ad we're looking for.
    Check if it contains video or image.
    """
    result = {
        "method": "first_ad_card",
        "found": False,
        "has_video": False,
        "has_image": False,
        "video_src": None,
        "image_src": None,
    }

    # The ad library shows ads in cards/containers
    # Try to find the first/main ad container

    # Look for ad preview cards - Facebook uses various class naming
    selectors_to_try = [
        # The main ad being viewed (when clicking "See ad details")
        'div[data-testid="ad_card"]',
        'div[data-testid="ad_library_preview_card"]',
        # Generic ad container patterns
        "div._7jyr",  # Common Facebook ad container class
        "div._99s5",  # Another common pattern
        # First ad in the list
        'div[role="article"]',
    ]

    for selector in selectors_to_try:
        elements = await page.query_selector_all(selector)
        if elements and len(elements) > 0:
            first_element = elements[0]
            print(f"  Found {len(elements)} elements with selector: {selector}")

            # Check for video in first element
            video = await first_element.query_selector("video")
            if video:
                src = await video.get_attribute("src")
                result["has_video"] = True
                result["video_src"] = src
                print(f"    First element has VIDEO: {src[:80] if src else 'no src'}...")

            # Check for image in first element (excluding icons, avatars etc)
            # Look for larger images that are likely ad creatives
            imgs = await first_element.query_selector_all("img")
            for img in imgs:
                src = await img.get_attribute("src")
                width = await img.get_attribute("width")
                _style = await img.get_attribute("style")  # noqa: F841

                # Skip small images (likely icons/avatars)
                if src and not src.startswith("data:"):
                    # Check if it's a substantial image
                    if width and int(width) > 100:
                        result["has_image"] = True
                        result["image_src"] = src
                        print(f"    First element has IMAGE (w={width}): {src[:80]}...")
                        break
                    elif "scontent" in src and ("jpg" in src or "png" in src):
                        # Facebook CDN image URL pattern
                        result["has_image"] = True
                        result["image_src"] = src
                        print(f"    First element has IMAGE (scontent): {src[:80]}...")
                        break

            result["found"] = True
            result["selector_used"] = selector
            break

    return result


async def analyze_ad_page(url: str, expected_type: str) -> dict:
    """
    Analyze an ad page to understand what media elements are present.
    """
    print(f"\n{'=' * 80}")
    print(f"Analyzing: {url}")
    print(f"Expected type: {expected_type}")
    print("=" * 80)

    # Extract ad ID from URL
    ad_id = url.split("id=")[-1].split("&")[0]
    print(f"Ad ID: {ad_id}")

    result = {
        "url": url,
        "ad_id": ad_id,
        "expected_type": expected_type,
        "detected_type": None,
    }

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

            print("\nLoading page...")
            await page.goto(url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(3)  # Extra wait for dynamic content

            # Save screenshot for debugging
            screenshot_path = f"/tmp/ad_{ad_id}.png"
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to: {screenshot_path}")

            # Method 1: Analyze page structure and JSON data
            print("\n--- Method 1: Page Structure Analysis ---")
            structure_result = await analyze_page_structure(page, ad_id)
            result["structure_analysis"] = structure_result

            # Method 2: Check the first ad card
            print("\n--- Method 2: First Ad Card Analysis ---")
            card_result = await check_creative_in_first_ad_card(page)
            result["card_analysis"] = card_result

            # Method 3: Count all videos vs all substantial images
            print("\n--- Method 3: Element Counts ---")
            all_videos = await page.query_selector_all("video")
            all_imgs = await page.query_selector_all("img")

            # Filter substantial images (not icons)
            substantial_imgs = []
            for img in all_imgs:
                src = await img.get_attribute("src")
                if src and not src.startswith("data:") and "scontent" in src:
                    substantial_imgs.append(img)

            print(f"  Total video elements: {len(all_videos)}")
            print(f"  Total substantial images: {len(substantial_imgs)}")

            # Method 4: Look for the specific ad's creative URL in page source
            print("\n--- Method 4: Creative URL Search ---")
            content = await page.content()

            # Search for ad-specific data blocks more broadly
            # The ad ID appears in JSON data, search nearby for video/image indicators
            has_video_url = False
            has_image_url = False

            # Find all occurrences of the ad ID and check nearby content
            for match in re.finditer(ad_id, content):
                pos = match.start()
                # Look at a large window around the ad ID (5000 chars)
                window_start = max(0, pos - 2000)
                window_end = min(len(content), pos + 3000)
                window = content[window_start:window_end]

                # Video indicators
                if re.search(r'"video_sd_url"\s*:\s*"[^"]+"', window):
                    has_video_url = True
                if re.search(r'"video_hd_url"\s*:\s*"[^"]+"', window):
                    has_video_url = True
                if re.search(r'"playable_url"\s*:\s*"[^"]+"', window):
                    has_video_url = True

                # Image indicators (but only if it's the main creative, not a thumbnail)
                if re.search(r'"resized_image_url"\s*:\s*"[^"]+"', window):
                    has_image_url = True
                if re.search(r'"watermarked_resized_image_url"\s*:\s*"[^"]+"', window):
                    has_image_url = True

            if has_video_url:
                print("  Found video URL patterns near ad ID")
                result["has_video_url_patterns"] = True
            if has_image_url:
                print("  Found image URL patterns near ad ID")
                result["has_image_url_patterns"] = True

            # Also do a global search for these patterns associated with this ad
            # Sometimes the ad data is in a different part of the page
            video_global = (
                re.search(rf'"id"\s*:\s*"{ad_id}"[^}}]*"video_sd_url"', content)
                or re.search(rf'"video_sd_url"[^}}]*"{ad_id}"', content)
                or re.search(rf'"ad_archive_id"\s*:\s*"{ad_id}"[^}}{{]*"video_', content, re.DOTALL)
            )
            image_global = (
                re.search(rf'"id"\s*:\s*"{ad_id}"[^}}]*"resized_image_url"', content)
                or re.search(rf'"resized_image_url"[^}}]*"{ad_id}"', content)
                or re.search(
                    rf'"ad_archive_id"\s*:\s*"{ad_id}"[^}}{{]*"resized_image_url"',
                    content,
                    re.DOTALL,
                )
            )

            if video_global:
                print("  Global search: Found video URL associated with this ad")
                result["global_video_match"] = True
            if image_global:
                print("  Global search: Found image URL associated with this ad")
                result["global_image_match"] = True

            # DECISION LOGIC: How should we determine the type?
            print("\n--- DECISION ---")

            # The key insight: video ads have video_sd_url/video_hd_url in JSON
            # Image ads have resized_image_url but NO video URLs
            has_video = result.get("has_video_url_patterns") or result.get("global_video_match")
            has_image = result.get("has_image_url_patterns") or result.get("global_image_match")

            if has_video:
                # Video ads have video URLs - this is the definitive indicator
                result["detected_type"] = "video"
                result["detection_reason"] = "Found video URL patterns in ad data"
            elif has_image:
                # Only image URLs found, no video - this is an image ad
                result["detected_type"] = "image"
                result["detection_reason"] = "Found image URL patterns but no video URLs"
            # Fallback to structure analysis
            elif structure_result.get("has_video_urls_in_block") and not structure_result.get(
                "has_image_urls_in_block"
            ):
                result["detected_type"] = "video"
                result["detection_reason"] = "JSON block contains video URLs"
            elif structure_result.get("has_image_urls_in_block") and not structure_result.get(
                "has_video_urls_in_block"
            ):
                result["detected_type"] = "image"
                result["detection_reason"] = "JSON block contains image URLs"
            else:
                result["detected_type"] = "unknown"
                result["detection_reason"] = "Could not determine from JSON data"

            print(f"  Detected type: {result['detected_type']}")
            print(f"  Reason: {result.get('detection_reason', 'N/A')}")

            # VERDICT
            print("\n--- VERDICT ---")
            if result["detected_type"] == result["expected_type"]:
                print(
                    f"  ✓ CORRECT: Detected {result['detected_type']} matches expected {result['expected_type']}"
                )
            else:
                print(
                    f"  ✗ MISMATCH: Detected {result['detected_type']} but expected {result['expected_type']}"
                )

            await context.close()

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
            result["error"] = str(e)

        finally:
            await browser.close()

    return result


async def test_actual_scraper():
    """Test the actual scraper function after our fix."""
    print("\n" + "=" * 80)
    print("TESTING ACTUAL SCRAPER FUNCTION")
    print("=" * 80)

    # Import the scraper
    import sys

    sys.path.insert(0, "/home/rjs/Desktop/Projects/marketing-ai")

    from app.services.ad_library_scraper import AdLibraryScraper

    scraper = AdLibraryScraper()

    test_cases = [
        (IMAGE_AD_URL, "image"),
        (VIDEO_AD_URL, "video"),
    ]

    results = []
    for url, expected_type in test_cases:
        ad_id = url.split("id=")[-1].split("&")[0]
        print(f"\nTesting scraper with ad ID {ad_id} (expected: {expected_type})...")

        try:
            creative_url, detected_type = await scraper.get_creative_url_from_snapshot(url)

            success = detected_type == expected_type
            status = "✓" if success else "✗"
            print(f"  {status} Detected type: {detected_type}")
            print(f"     Creative URL: {creative_url[:80] if creative_url else 'None'}...")

            results.append(
                {
                    "ad_id": ad_id,
                    "expected": expected_type,
                    "detected": detected_type,
                    "success": success,
                }
            )
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append(
                {
                    "ad_id": ad_id,
                    "expected": expected_type,
                    "detected": "error",
                    "success": False,
                }
            )

    # Summary
    print("\n--- SCRAPER FUNCTION TEST RESULTS ---")
    all_passed = all(r["success"] for r in results)
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} Ad {r['ad_id']}: expected {r['expected']}, got {r['detected']}")

    if all_passed:
        print("\n✓ ALL TESTS PASSED - Scraper correctly distinguishes images from videos")
    else:
        print("\n✗ SOME TESTS FAILED - Fix may not be working correctly")

    return all_passed


async def main():
    """Run analysis on both test URLs."""
    print("\n" + "=" * 80)
    print("MEDIA TYPE DETECTION TEST")
    print("=" * 80)

    results = []

    # Test the image ad
    image_result = await analyze_ad_page(IMAGE_AD_URL, "image")
    results.append(image_result)

    # Test the video ad
    video_result = await analyze_ad_page(VIDEO_AD_URL, "video")
    results.append(video_result)

    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    for r in results:
        status = "✓" if r.get("detected_type") == r.get("expected_type") else "✗"
        print(f"\n{status} Ad ID {r['ad_id']} ({r['expected_type'].upper()} ad)")
        print(f"   Detected as: {r.get('detected_type', 'error')}")
        print(f"   Reason: {r.get('detection_reason', 'N/A')}")

    # Now test the actual scraper function
    await test_actual_scraper()


if __name__ == "__main__":
    asyncio.run(main())
