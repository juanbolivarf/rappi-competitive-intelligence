"""
Deep analysis of Uber Eats and DiDi Food to find scraping opportunities.

Strategies to explore:
1. JSON-LD schema.org data (already know UberEats has Restaurant schema)
2. Hidden API endpoints in the page
3. Mobile API reverse engineering
4. Different User-Agents (mobile vs desktop)
5. Cookie/session tricks
"""

import json
import re
import httpx
from bs4 import BeautifulSoup

DESKTOP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

def extract_json_ld(html: str) -> list[dict]:
    """Extract all JSON-LD blocks from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    blocks = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        if script.string:
            try:
                data = json.loads(script.string)
                blocks.append(data)
            except json.JSONDecodeError:
                pass
    return blocks


def find_api_endpoints(html: str) -> list[str]:
    """Search for API endpoint patterns in JavaScript."""
    patterns = [
        r'["\'](https?://[^"\']*api[^"\']*)["\']',
        r'["\'](/api/[^"\']+)["\']',
        r'["\'](/v\d/[^"\']+)["\']',
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.[a-z]+\(["\']([^"\']+)["\']',
    ]
    endpoints = set()
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        endpoints.update(matches)
    return sorted(endpoints)[:20]  # Limit output


def find_state_variables(html: str) -> dict:
    """Search for state/data variables in scripts."""
    patterns = {
        "__REDUX_STATE__": r'window\.__REDUX_STATE__\s*=\s*({.+?});',
        "__PRELOADED_STATE__": r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
        "__INITIAL_STATE__": r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
        "__APP_STATE__": r'window\.__APP_STATE__\s*=\s*({.+?});',
        "UBER_DATA": r'window\.UBER_DATA\s*=\s*({.+?});',
    }
    found = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, html, re.DOTALL)
        if match:
            found[name] = len(match.group(1))  # Just store size
    return found


def analyze_ubereats():
    """Deep analysis of Uber Eats."""
    print("\n" + "=" * 70)
    print("UBER EATS DEEP ANALYSIS")
    print("=" * 70)

    url = "https://www.ubereats.com/mx-en/store/mcdonalds-centro/pVf6cMIlRtCP2DC0iy7t4w"

    # Try desktop
    print("\n[1] Desktop User-Agent:")
    try:
        resp = httpx.get(url, headers=DESKTOP_HEADERS, follow_redirects=True, timeout=15)
        print(f"    Status: {resp.status_code}")
        print(f"    Final URL: {resp.url}")
        print(f"    Content size: {len(resp.text)} bytes")

        # Check JSON-LD
        json_ld = extract_json_ld(resp.text)
        print(f"\n    JSON-LD blocks found: {len(json_ld)}")
        for i, block in enumerate(json_ld):
            block_type = block.get("@type", "unknown")
            print(f"    Block {i+1}: {block_type}")

            # If it's a Restaurant, extract useful data
            if block_type == "Restaurant":
                print(f"      - name: {block.get('name', 'N/A')}")
                print(f"      - priceRange: {block.get('priceRange', 'N/A')}")
                print(f"      - servesCuisine: {block.get('servesCuisine', 'N/A')}")
                if "aggregateRating" in block:
                    rating = block["aggregateRating"]
                    print(f"      - rating: {rating.get('ratingValue', 'N/A')} ({rating.get('reviewCount', 'N/A')} reviews)")
                if "hasMenu" in block:
                    menu = block["hasMenu"]
                    print(f"      - hasMenu: {type(menu)}")
                    if isinstance(menu, dict):
                        sections = menu.get("hasMenuSection", [])
                        print(f"      - menu sections: {len(sections) if isinstance(sections, list) else 'N/A'}")
                        if sections and isinstance(sections, list):
                            for sec in sections[:3]:
                                sec_name = sec.get("name", "unnamed")
                                items = sec.get("hasMenuItem", [])
                                print(f"        - {sec_name}: {len(items) if isinstance(items, list) else 0} items")
                                if items and isinstance(items, list):
                                    for item in items[:2]:
                                        item_name = item.get("name", "?")
                                        offers = item.get("offers", {})
                                        price = offers.get("price", "N/A") if isinstance(offers, dict) else "N/A"
                                        print(f"          * {item_name}: ${price}")

        # Look for state variables
        state_vars = find_state_variables(resp.text)
        if state_vars:
            print(f"\n    State variables found:")
            for name, size in state_vars.items():
                print(f"      - {name}: {size} bytes")

    except Exception as e:
        print(f"    Error: {e}")

    # Try mobile
    print("\n[2] Mobile User-Agent:")
    try:
        resp = httpx.get(url, headers=MOBILE_HEADERS, follow_redirects=True, timeout=15)
        print(f"    Status: {resp.status_code}")
        print(f"    Final URL: {resp.url}")
        print(f"    Content size: {len(resp.text)} bytes")

        json_ld = extract_json_ld(resp.text)
        print(f"    JSON-LD blocks: {len(json_ld)}")

    except Exception as e:
        print(f"    Error: {e}")

    # Try the eats API directly
    print("\n[3] Testing Uber Eats API endpoint:")
    api_url = "https://www.ubereats.com/api/getStoreV1"
    store_uuid = "pVf6cMIlRtCP2DC0iy7t4w"

    try:
        # This is a GraphQL-like API
        payload = {
            "storeUuid": store_uuid,
            "sfNuggetCount": 0,
        }
        api_headers = {
            **DESKTOP_HEADERS,
            "Content-Type": "application/json",
            "x-csrf-token": "x",  # Often required
        }
        resp = httpx.post(api_url, json=payload, headers=api_headers, timeout=15)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"    Response: {resp.text[:500]}")
        else:
            print(f"    Response: {resp.text[:200]}")
    except Exception as e:
        print(f"    Error: {e}")


def analyze_didifood():
    """Deep analysis of DiDi Food."""
    print("\n" + "=" * 70)
    print("DIDI FOOD DEEP ANALYSIS")
    print("=" * 70)

    url = "https://www.didi-food.com/es-MX/food/store/5764607602869405740/McDonalds/?lat=20.6597&lng=-103.3496"

    # Try desktop
    print("\n[1] Desktop User-Agent:")
    try:
        resp = httpx.get(url, headers=DESKTOP_HEADERS, follow_redirects=True, timeout=15)
        print(f"    Status: {resp.status_code}")
        print(f"    Final URL: {resp.url}")
        print(f"    Content size: {len(resp.text)} bytes")

        # Check if login redirect
        if "login" in str(resp.url).lower() or "signin" in str(resp.url).lower():
            print("    [!] Redirected to login page")

        json_ld = extract_json_ld(resp.text)
        print(f"    JSON-LD blocks: {len(json_ld)}")

        # Look for API patterns
        endpoints = find_api_endpoints(resp.text)
        if endpoints:
            print(f"\n    Potential API endpoints found:")
            for ep in endpoints[:10]:
                print(f"      - {ep}")

    except Exception as e:
        print(f"    Error: {e}")

    # Try mobile
    print("\n[2] Mobile User-Agent:")
    try:
        resp = httpx.get(url, headers=MOBILE_HEADERS, follow_redirects=True, timeout=15)
        print(f"    Status: {resp.status_code}")
        print(f"    Final URL: {resp.url}")
        print(f"    Content size: {len(resp.text)} bytes")

    except Exception as e:
        print(f"    Error: {e}")

    # Try DiDi Food API
    print("\n[3] Testing DiDi Food API patterns:")

    # Common DiDi API patterns
    api_urls = [
        "https://food.didi-food.com/api/v1/store/5764607602869405740",
        "https://api.didi-food.com/v1/store/5764607602869405740",
        "https://www.didi-food.com/api/store/5764607602869405740",
    ]

    for api_url in api_urls:
        try:
            resp = httpx.get(api_url, headers=DESKTOP_HEADERS, timeout=10)
            print(f"    {api_url[:50]}...")
            print(f"      Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"      [SUCCESS] Response: {resp.text[:200]}")
        except Exception as e:
            print(f"      Error: {e}")


def main():
    print("=" * 70)
    print("DEEP SCRAPING ANALYSIS: UBER EATS & DIDI FOOD")
    print("=" * 70)
    print("\nGoal: Find alternative data extraction methods")

    analyze_ubereats()
    analyze_didifood()

    print("\n" + "=" * 70)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 70)


if __name__ == "__main__":
    main()
