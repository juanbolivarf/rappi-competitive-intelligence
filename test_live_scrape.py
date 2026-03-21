"""
Live Scraping Test Suite
========================

Two scraping strategies tested:

1. SSR EXTRACTION (works NOW, no CF credentials needed):
   - Extracts __NEXT_DATA__ from Rappi's server-rendered pages
   - Gets: delivery fee, ETA, rating, promotions per restaurant
   - Limitation: no individual product prices (needs JS execution)

2. CLOUDFLARE BROWSER RENDERING (needs CF account):
   - Full JS execution via /json endpoint with AI extraction
   - Gets: product prices, service fees, delivery fees, ETAs
   - Recommended approach for the full case

Usage:
    python tests/test_live_scrape.py               # SSR only (no credentials needed)
    python tests/test_live_scrape.py --with-cf      # Include CF Browser Rendering test
"""

import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.addresses import ADDRESSES, get_addresses_by_zone
from config.products import PRODUCTS


# ══════════════════════════════════════════════════════════════════
# STRATEGY 1: SSR Extraction (no CF credentials needed)
# ══════════════════════════════════════════════════════════════════

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}


def extract_rappi_ssr(lat: float, lng: float) -> dict:
    """
    Extract server-rendered data from Rappi's Next.js __NEXT_DATA__.
    Returns catalog-level data (delivery fees, ETAs, ratings, promos).
    """
    url = f"https://www.rappi.com.mx/restaurantes?lat={lat}&lng={lng}"
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)

    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}", "restaurants": []}

    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r.text, re.DOTALL
    )
    if not match:
        return {"error": "No __NEXT_DATA__ found", "restaurants": []}

    data = json.loads(match.group(1))
    page_props = data.get("props", {}).get("pageProps", {})

    # Location context
    location = page_props.get("location", {})

    # Restaurants from catalog or SWR fallback
    catalog = page_props.get("catalog", {})
    restaurants = catalog.get("restaurants", [])

    # If empty, try SWR fallback
    if not restaurants:
        fallback = page_props.get("fallback", {})
        for key, val in fallback.items():
            if isinstance(val, list) and len(val) > 0:
                restaurants = val
                break

    return {
        "location": location,
        "total_in_catalog": catalog.get("numberOfRestaurants", 0),
        "restaurants_loaded": len(restaurants),
        "restaurants": [
            {
                "name": r.get("name", ""),
                "id": r.get("id"),
                "status": r.get("status", "UNKNOWN"),
                "delivery_cost_mxn": r.get("deliveryCost"),
                "eta": r.get("etaString", ""),
                "rating": r.get("rating"),
                "promotion": r.get("promotionText", ""),
                "has_free_shipping": r.get("hasFreeShipping", False),
                "is_new": r.get("isNew", False),
            }
            for r in restaurants
        ],
    }


def test_rappi_ssr_multi_zone():
    """Test SSR extraction across multiple zones in GDL."""
    print("\n" + "=" * 70)
    print("STRATEGY 1: Rappi SSR Extraction (no CF credentials needed)")
    print("=" * 70)

    # Test 5 addresses (one per zone type)
    test_addresses = [
        get_addresses_by_zone(zt)[0] for zt in
        ["high_income", "mid_income", "low_income", "commercial", "university"]
    ]

    all_results = []
    for addr in test_addresses:
        print(f"\n📍 {addr.name} ({addr.zone_type})")
        result = extract_rappi_ssr(addr.lat, addr.lng)

        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            continue

        loc = result.get("location", {})
        print(f"   City: {loc.get('city', 'N/A')}")
        print(f"   Total catalog: {result['total_in_catalog']:,} restaurants")
        print(f"   Loaded: {result['restaurants_loaded']}")

        # Analyze delivery fees
        fees = [r["delivery_cost_mxn"] for r in result["restaurants"] if r["delivery_cost_mxn"] is not None]
        if fees:
            avg_fee = sum(fees) / len(fees)
            print(f"   Avg delivery fee: ${avg_fee:.0f} MXN")
            print(f"   Fee range: ${min(fees):.0f} - ${max(fees):.0f} MXN")

        # Analyze ETAs
        etas = []
        for r in result["restaurants"]:
            eta_str = r.get("eta", "")
            match = re.search(r"(\d+)", eta_str)
            if match:
                etas.append(int(match.group(1)))
        if etas:
            print(f"   Avg ETA: {sum(etas) / len(etas):.0f} min")

        # Count promos
        promos = [r for r in result["restaurants"] if r.get("promotion")]
        print(f"   Active promos: {len(promos)}/{len(result['restaurants'])}")

        all_results.append({
            "address": addr.name,
            "zone_type": addr.zone_type,
            "data": result,
        })

        time.sleep(2)  # Rate limit

    # Save SSR results
    output_path = Path("data/raw/ssr_test_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved to {output_path}")

    return all_results


# ══════════════════════════════════════════════════════════════════
# STRATEGY 2: Cloudflare Browser Rendering (needs credentials)
# ══════════════════════════════════════════════════════════════════

async def test_cf_browser_rendering():
    """Test Cloudflare Browser Rendering /json endpoint."""
    print("\n" + "=" * 70)
    print("STRATEGY 2: Cloudflare Browser Rendering /json Endpoint")
    print("=" * 70)

    from config.settings import settings

    errors = settings.validate()
    if errors:
        print(f"\n⚠️  Cannot test CF Browser Rendering: {errors}")
        print("   Set CF_ACCOUNT_ID and CF_API_TOKEN in .env")
        print("   Free account: https://developers.cloudflare.com/browser-rendering/")
        return None

    from scraper.cloudflare_client import CloudflareClient
    from scraper.schemas import build_restaurant_prompt, RESTAURANT_DATA_SCHEMA

    # Test with one address
    addr = ADDRESSES[0]  # Providencia (high income)
    test_url = f"https://www.rappi.com.mx/restaurantes?lat={addr.lat}&lng={addr.lng}"

    print(f"\n📍 Testing: {addr.name}")
    print(f"   URL: {test_url[:80]}...")

    async with CloudflareClient() as client:
        # Test 1: /scrape endpoint
        print("\n--- Test: /scrape endpoint ---")
        try:
            result = await client.scrape(
                url=test_url,
                selectors=[
                    {"selector": "h1"},
                    {"selector": "[data-testid='store-card']"},
                    {"selector": ".restaurant-card"},
                ],
                wait_until="networkidle0",
            )
            print(f"   ✅ /scrape returned {len(result)} selector results")
            for sel in result:
                matches = sel.get("results", [])
                print(f"   '{sel.get('selector', 'N/A')}': {len(matches)} elements")
        except Exception as e:
            print(f"   ❌ /scrape error: {e}")

        # Test 2: /json endpoint (AI extraction)
        print("\n--- Test: /json endpoint (AI-powered) ---")
        try:
            prompt = build_restaurant_prompt(
                "McDonald's",
                [p.name for p in PRODUCTS],
            )
            result = await client.extract_json(
                url=test_url,
                prompt=prompt,
                response_format=RESTAURANT_DATA_SCHEMA,
                wait_until="networkidle0",
            )
            print(f"   ✅ /json returned data")
            print(f"   Restaurant: {result.get('restaurant_name', 'N/A')}")
            print(f"   Available: {result.get('restaurant_available', 'N/A')}")
            print(f"   Delivery fee: {result.get('delivery_fee_mxn', 'N/A')}")
            products = result.get("products", [])
            print(f"   Products extracted: {len(products)}")
            for p in products:
                print(f"     - {p.get('name', 'N/A')}: ${p.get('price_mxn', 'N/A')}")
        except Exception as e:
            print(f"   ❌ /json error: {e}")

        # Test 3: /screenshot endpoint
        print("\n--- Test: /screenshot endpoint ---")
        try:
            screenshot = await client.screenshot(url=test_url)
            screenshot_path = Path("assets/test_screenshot.png")
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            screenshot_path.write_bytes(screenshot)
            print(f"   ✅ Screenshot saved ({len(screenshot):,} bytes) → {screenshot_path}")
        except Exception as e:
            print(f"   ❌ /screenshot error: {e}")


# ══════════════════════════════════════════════════════════════════
# UBER EATS TEST
# ══════════════════════════════════════════════════════════════════

def test_ubereats_reachability():
    """Test Uber Eats page structure."""
    print("\n" + "=" * 70)
    print("UBER EATS: Page Reachability Test")
    print("=" * 70)

    addr = ADDRESSES[0]
    url = f"https://www.ubereats.com/mx/search?diningMode=DELIVERY&pl={addr.lat}%2C{addr.lng}&q=McDonalds"

    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
    print(f"Status: {r.status_code}")
    print(f"Final URL: {str(r.url)[:100]}")
    print(f"Body: {len(r.text):,} chars")

    # UE is a heavy React SPA — all data loaded via JS
    # This DEFINITIVELY needs CF Browser Rendering
    has_data = "McDonald" in r.text
    print(f"McDonald's in HTML: {'✅ Yes' if has_data else '❌ No (needs JS rendering)'}")
    print(f"→ Uber Eats requires Cloudflare Browser Rendering for data extraction")


# ══════════════════════════════════════════════════════════════════
# SUMMARY & RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════

def print_summary(ssr_results):
    """Print analysis summary and recommendations."""
    print("\n" + "=" * 70)
    print("LIVE TEST SUMMARY")
    print("=" * 70)

    print("""
┌─────────────────────────────────────────────────────────────────┐
│ Platform     │ SSR Data?  │ Needs CF?  │ Status                │
├─────────────────────────────────────────────────────────────────┤
│ Rappi        │ ✅ Partial  │ ✅ For prices│ SSR gives fees/ETAs  │
│ Uber Eats    │ ❌ No       │ ✅ Required  │ Pure SPA, no SSR data │
│ DiDi Food    │ ❌ No       │ ✅ Required  │ 403 without browser   │
└─────────────────────────────────────────────────────────────────┘

KEY FINDINGS:

1. RAPPI SSR provides catalog-level data WITHOUT JS execution:
   - Delivery cost per restaurant (MXN)
   - ETA per restaurant
   - Ratings and review counts
   - Active promotions (e.g., "Envío Gratis: Aplican TyC")
   ⚠️  Missing: individual product prices, service fees

2. For PRODUCT-LEVEL pricing (Big Mac, combos, etc.):
   → Must use Cloudflare Browser Rendering /json endpoint
   → Must navigate to specific restaurant page (not search)

3. Uber Eats and DiDi Food are pure SPAs:
   → REQUIRE Cloudflare Browser Rendering for any data

RECOMMENDED DUAL STRATEGY:
- Layer 1: SSR extraction for Rappi (delivery fees, ETAs, promos)
- Layer 2: CF /json for product pricing on all 3 platforms
- This gives PARTIAL data even if CF quotas are exhausted
""")

    if ssr_results:
        print("RAPPI SSR DATA COLLECTED:")
        for r in ssr_results:
            data = r["data"]
            fees = [rest["delivery_cost_mxn"] for rest in data["restaurants"] if rest["delivery_cost_mxn"]]
            avg = sum(fees) / len(fees) if fees else 0
            print(f"  {r['address']:20s} ({r['zone_type']:12s}) — Avg fee: ${avg:.0f} MXN, {data['restaurants_loaded']} restaurants")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("🔍 Rappi Competitive Intelligence — Live Scraping Test")
    print(f"   Timestamp: {datetime.utcnow().isoformat()}")
    print(f"   Addresses configured: {len(ADDRESSES)}")
    print(f"   Products configured: {len(PRODUCTS)}")

    # Always run SSR test (no credentials needed)
    ssr_results = test_rappi_ssr_multi_zone()

    # Test UE reachability
    test_ubereats_reachability()

    # Run CF test if requested
    if "--with-cf" in sys.argv:
        asyncio.run(test_cf_browser_rendering())

    # Summary
    print_summary(ssr_results)


if __name__ == "__main__":
    main()
