"""
Test SSR (Server-Side Rendered) data extraction from food delivery platforms.

Goal: Check if we can extract pricing data WITHOUT a headless browser
by finding embedded JSON in the initial HTML response.

Common patterns:
- Next.js: <script id="__NEXT_DATA__">
- Nuxt.js: window.__NUXT__
- React SSR: window.__INITIAL_STATE__ or window.__PRELOADED_STATE__
- Generic: <script type="application/json">
"""

import re
import json
import httpx
from bs4 import BeautifulSoup

# Sample URLs from the scrapers
URLS = {
    "rappi": "https://www.rappi.com.mx/restaurantes/1923209058-mcdonalds?lat=20.6597&lng=-103.3496",
    "ubereats": "https://www.ubereats.com/mx-en/store/mcdonalds-centro/pVf6cMIlRtCP2DC0iy7t4w",
    "didifood": "https://www.didi-food.com/es-MX/food/store/5764607602869405740/McDonalds/?lat=20.6597&lng=-103.3496",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}


def find_embedded_json(html: str, platform: str) -> dict:
    """Search for common SSR data patterns in HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results = {
        "has_next_data": False,
        "has_nuxt_data": False,
        "has_initial_state": False,
        "has_json_ld": False,
        "script_tags_count": 0,
        "interesting_scripts": [],
        "extracted_data": None,
    }

    # 1. Next.js __NEXT_DATA__
    next_data = soup.find("script", {"id": "__NEXT_DATA__"})
    if next_data and next_data.string:
        results["has_next_data"] = True
        try:
            data = json.loads(next_data.string)
            results["extracted_data"] = data
            print(f"  [OK] Found __NEXT_DATA__ ({len(next_data.string)} bytes)")
        except json.JSONDecodeError:
            print(f"  [WARN] Found __NEXT_DATA__ but couldn't parse JSON")

    # 2. Nuxt.js window.__NUXT__
    for script in soup.find_all("script"):
        if script.string and "__NUXT__" in script.string:
            results["has_nuxt_data"] = True
            print(f"  [OK] Found __NUXT__ data")
            break

    # 3. Generic __INITIAL_STATE__ or __PRELOADED_STATE__
    for script in soup.find_all("script"):
        if script.string:
            if "__INITIAL_STATE__" in script.string:
                results["has_initial_state"] = True
                print(f"  [OK] Found __INITIAL_STATE__")
            if "__PRELOADED_STATE__" in script.string:
                results["has_initial_state"] = True
                print(f"  [OK] Found __PRELOADED_STATE__")

    # 4. JSON-LD structured data (schema.org)
    json_ld = soup.find_all("script", {"type": "application/ld+json"})
    if json_ld:
        results["has_json_ld"] = True
        print(f"  [OK] Found {len(json_ld)} JSON-LD blocks (schema.org)")
        for i, block in enumerate(json_ld[:2]):  # Show first 2
            try:
                data = json.loads(block.string)
                print(f"    - Block {i+1}: {data.get('@type', 'unknown type')}")
            except:
                pass

    # 5. Count all script tags
    all_scripts = soup.find_all("script")
    results["script_tags_count"] = len(all_scripts)

    # 6. Look for interesting patterns in scripts
    patterns = [
        r"products?\s*[=:]\s*\[",  # products = [ or products: [
        r"price\s*[=:]\s*[\d\.]+",  # price = 99.00 or price: 99
        r"menuItems?\s*[=:]\s*\[",  # menuItems = [
        r"storeData\s*[=:]\s*\{",  # storeData = {
        r"restaurantData\s*[=:]\s*\{",  # restaurantData = {
    ]

    for script in all_scripts:
        if script.string:
            for pattern in patterns:
                if re.search(pattern, script.string, re.IGNORECASE):
                    snippet = script.string[:200].replace("\n", " ")
                    results["interesting_scripts"].append(snippet)
                    print(f"  [OK] Found pattern '{pattern}' in script")
                    break

    return results


def analyze_platform(name: str, url: str):
    """Fetch and analyze a platform's HTML for embedded data."""
    print(f"\n{'='*60}")
    print(f"PLATFORM: {name.upper()}")
    print(f"URL: {url[:80]}...")
    print("="*60)

    try:
        response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Content-Length: {len(response.text)} bytes")

        # Check if we hit a login wall
        if "login" in str(response.url).lower() or "signin" in str(response.url).lower():
            print("  [WARN] REDIRECTED TO LOGIN PAGE")

        # Look for common blocking indicators
        html_lower = response.text.lower()
        if "captcha" in html_lower:
            print("  [WARN] CAPTCHA detected")
        if "access denied" in html_lower or "blocked" in html_lower:
            print("  [WARN] Access denied/blocked message detected")

        # Find embedded JSON
        print("\nSearching for embedded data...")
        results = find_embedded_json(response.text, name)

        print(f"\nSummary:")
        print(f"  - Script tags: {results['script_tags_count']}")
        print(f"  - __NEXT_DATA__: {'Yes' if results['has_next_data'] else 'No'}")
        print(f"  - __NUXT__: {'Yes' if results['has_nuxt_data'] else 'No'}")
        print(f"  - __INITIAL_STATE__: {'Yes' if results['has_initial_state'] else 'No'}")
        print(f"  - JSON-LD: {'Yes' if results['has_json_ld'] else 'No'}")

        # If we found __NEXT_DATA__, explore its structure
        if results["extracted_data"]:
            data = results["extracted_data"]
            print(f"\n__NEXT_DATA__ structure:")
            print(f"  - Top-level keys: {list(data.keys())}")
            if "props" in data:
                print(f"  - props keys: {list(data['props'].keys())[:10]}")
                if "pageProps" in data["props"]:
                    page_props = data["props"]["pageProps"]
                    print(f"  - pageProps keys: {list(page_props.keys())[:15]}")

                    # Try to find product/price data
                    def find_prices(obj, path=""):
                        """Recursively search for price-like data."""
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if any(term in k.lower() for term in ["price", "product", "menu", "item", "delivery", "fee"]):
                                    print(f"    Found '{k}' at {path}")
                                    if isinstance(v, (int, float, str)) and v:
                                        print(f"      Value: {str(v)[:100]}")
                                find_prices(v, f"{path}.{k}")
                        elif isinstance(obj, list) and len(obj) > 0:
                            find_prices(obj[0], f"{path}[0]")

                    print(f"\n  Searching for price/product data...")
                    find_prices(page_props)

        return results

    except httpx.TimeoutException:
        print("  [FAIL] Request timed out")
        return None
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return None


def main():
    print("SSR Data Extraction Test")
    print("=" * 60)
    print("Testing if we can extract data WITHOUT headless browser...")

    results = {}
    for platform, url in URLS.items():
        results[platform] = analyze_platform(platform, url)

    print("\n" + "=" * 60)
    print("FINAL ASSESSMENT")
    print("=" * 60)

    for platform, result in results.items():
        if result is None:
            print(f"{platform}: FAILED - couldn't fetch")
        elif result["has_next_data"] and result["extracted_data"]:
            print(f"{platform}: [OK] SSR EXTRACTION POSSIBLE (Next.js)")
        elif result["has_nuxt_data"]:
            print(f"{platform}: [OK] SSR EXTRACTION POSSIBLE (Nuxt.js)")
        elif result["has_initial_state"]:
            print(f"{platform}: [OK] SSR EXTRACTION POSSIBLE (React SSR)")
        elif result["interesting_scripts"]:
            print(f"{platform}: [MAYBE] found inline data patterns")
        else:
            print(f"{platform}: [NO] NO SSR DATA - needs headless browser")


if __name__ == "__main__":
    main()
