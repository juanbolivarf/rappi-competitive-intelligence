"""
Rappi SSR (Server-Side Rendering) Fallback Scraper.

Extracts catalog-level data directly from Rappi's __NEXT_DATA__ JSON
without needing Cloudflare Browser Rendering. This provides:
- Delivery fees per restaurant
- ETAs
- Ratings & review counts
- Active promotions

Limitations (needs CF Browser Rendering for these):
- Individual product prices (Big Mac, etc.)
- Service fees
- Restaurant-specific menu data

Usage:
    python -m scraper.rappi_ssr_fallback         # Full run (25 addresses)
    python -m scraper.rappi_ssr_fallback --limit 5   # Test with 5 addresses
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.addresses import ADDRESSES, ZONE_TYPES
from config.settings import settings

console = Console()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}


def scrape_rappi_ssr(lat: float, lng: float, timeout: int = 20) -> dict:
    """Extract __NEXT_DATA__ from Rappi's server-rendered page."""
    url = f"https://www.rappi.com.mx/restaurantes?lat={lat}&lng={lng}"
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=timeout)

    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}

    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r.text, re.DOTALL
    )
    if not match:
        return {"error": "No __NEXT_DATA__ found"}

    data = json.loads(match.group(1))
    pp = data.get("props", {}).get("pageProps", {})

    catalog = pp.get("catalog", {})
    restaurants = catalog.get("restaurants", [])
    if not restaurants:
        fallback = pp.get("fallback", {})
        for val in fallback.values():
            if isinstance(val, list) and len(val) > 0:
                restaurants = val
                break

    return {
        "location": pp.get("location", {}),
        "total_catalog": catalog.get("numberOfRestaurants", 0),
        "promotionBanners": catalog.get("promotionBanners", []),
        "restaurants": [
            {
                "name": r.get("name", ""),
                "id": r.get("id"),
                "status": r.get("status", "UNKNOWN"),
                "delivery_cost_mxn": r.get("deliveryCost"),
                "eta_string": r.get("etaString", ""),
                "rating": r.get("rating"),
                "review_count": r.get("reviewAmount", 0),
                "promotion": r.get("promotionText", ""),
                "has_free_shipping": r.get("hasFreeShipping", False),
                "brand_id": r.get("brandId"),
            }
            for r in restaurants
        ],
    }


@click.command()
@click.option("--limit", "-l", type=int, default=None, help="Limit to first N addresses")
def main(limit):
    """Rappi SSR Fallback Scraper — catalog-level data extraction."""
    addresses = ADDRESSES[:limit] if limit else ADDRESSES
    console.print(f"\n[bold]Rappi SSR Scraper — {len(addresses)} addresses[/bold]\n")

    all_results = []
    for i, addr in enumerate(addresses, 1):
        console.print(f"[{i}/{len(addresses)}] {addr.name} ({addr.zone_type})")

        result = scrape_rappi_ssr(addr.lat, addr.lng)
        all_results.append({
            "address_id": addr.id,
            "address_name": addr.name,
            "zone_type": addr.zone_type,
            "lat": addr.lat,
            "lng": addr.lng,
            "scraped_at": datetime.now().isoformat(),
            "data": result,
        })

        if "error" in result:
            console.print(f"  ❌ {result['error']}")
        else:
            fees = [r["delivery_cost_mxn"] for r in result["restaurants"] if r["delivery_cost_mxn"]]
            avg = sum(fees) / len(fees) if fees else 0
            console.print(f"  ✅ {len(result['restaurants'])} restaurants, avg fee ${avg:.0f}")

        time.sleep(2)

    # Save
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out = settings.raw_data_dir / f"rappi_ssr_{ts}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]✅ Saved {len(all_results)} results → {out}[/green]")

    # Summary table
    table = Table(title="Rappi SSR Summary by Zone")
    table.add_column("Zone", style="cyan")
    table.add_column("Addresses", justify="right")
    table.add_column("Avg Fee", justify="right")
    table.add_column("Avg ETA", justify="right")
    table.add_column("Promos", justify="right")

    for zt in ZONE_TYPES:
        zone_results = [r for r in all_results if r["zone_type"] == zt and "error" not in r["data"]]
        if not zone_results:
            continue
        all_fees = []
        all_etas = []
        all_promos = 0
        for zr in zone_results:
            for rest in zr["data"]["restaurants"]:
                if rest["delivery_cost_mxn"]:
                    all_fees.append(rest["delivery_cost_mxn"])
                m = re.search(r"(\d+)", rest.get("eta_string", ""))
                if m:
                    all_etas.append(int(m.group(1)))
                if rest.get("promotion"):
                    all_promos += 1

        avg_fee = f"${sum(all_fees) / len(all_fees):.0f}" if all_fees else "N/A"
        avg_eta = f"{sum(all_etas) / len(all_etas):.0f} min" if all_etas else "N/A"
        table.add_row(zt, str(len(zone_results)), avg_fee, avg_eta, str(all_promos))

    console.print(table)


if __name__ == "__main__":
    main()
