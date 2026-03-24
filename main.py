"""
Competitive Intelligence Scraper — Main Orchestrator.

Entry point for the scraping pipeline. Coordinates all platform scrapers,
manages the Cloudflare client lifecycle, and outputs structured data.

Usage:
    python -m scraper.main                     # Full run (real-time scraping)
    python -m scraper.main --platform rappi    # Single platform
    python -m scraper.main --addresses 5       # Subset (first N)
    python -m scraper.main --dry-run           # Validate config only
    python -m scraper.main --test-data         # Use synthetic test data

Data Modes:
    1. Real-time Scraping (default): Live data from Rappi and Uber Eats SSR
    2. Test Data (--test-data): Synthetic data with realistic market patterns

SSR Mode (default):
    Rappi and Uber Eats use SSR extraction (FREE, no Cloudflare needed).
    DiDi Food requires authentication and is skipped by default.

Legacy Mode (--use-cloudflare):
    Uses Cloudflare Browser Rendering for all platforms.
    Costs API credits and is slower, but may be needed if SSR stops working.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from config import settings, ADDRESSES, PRODUCTS
from config.addresses import MARKET_AREAS
from scraper.cloudflare_client import CloudflareClient
from scraper.base_scraper import ScrapedDataPoint

# SSR Scrapers (FREE - no Cloudflare needed)
from rappi_ssr_scraper import RappiSSRScraper
from ubereats_ssr_scraper import UberEatsSSRScraper

# Playwright Scrapers (full data - requires browser)
from ubereats_playwright_scraper import UberEatsPlaywrightScraper

# Legacy Cloudflare-based scrapers (for fallback)
from scraper.rappi_scraper import RappiScraper
from scraper.ubereats_scraper import UberEatsScraper
from scraper.didifood_scraper import DiDiFoodScraper

# Synthetic data generator (for testing)
from synthetic_data import generate_synthetic_data

console = Console()

# ── Logging setup ─────────────────────────────────────────────────

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


# ── Scraper registry ─────────────────────────────────────────────

# SSR Scrapers (FREE - extract data from HTML without browser rendering)
SSR_SCRAPERS = {
    "rappi": RappiSSRScraper,
    "ubereats": UberEatsSSRScraper,
    # DiDi Food has login wall - SSR not possible
}

# Legacy Cloudflare-based scrapers (uses API credits)
CLOUDFLARE_SCRAPERS = {
    "rappi": RappiScraper,
    "ubereats": UberEatsScraper,
    "didifood": DiDiFoodScraper,
}

# Default scraper list (for CLI validation)
SCRAPERS = {**SSR_SCRAPERS, "didifood": DiDiFoodScraper}


# ── Data output ───────────────────────────────────────────────────

def save_results(
    results: list[ScrapedDataPoint],
    output_dir: Path,
    timestamp: str,
) -> tuple[Path, Path]:
    """Save results as both JSON and CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON (full fidelity)
    json_path = output_dir / f"scrape_{timestamp}.json"
    json_data = [r.to_dict() for r in results]
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))

    # CSV (for pandas/Excel analysis)
    csv_path = output_dir / f"scrape_{timestamp}.csv"
    if results:
        import csv
        fieldnames = list(results[0].to_dict().keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                row = r.to_dict()
                # Convert list fields to string for CSV
                row["platform_promotions"] = "; ".join(row.get("platform_promotions", []))
                writer.writerow(row)

    return json_path, csv_path


def print_summary(results: list[ScrapedDataPoint]):
    """Pretty-print scraping summary to console."""
    table = Table(title="Scraping Summary")
    table.add_column("Platform", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("Success", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Avg Price", justify="right")
    table.add_column("Avg Delivery Fee", justify="right")

    for platform in SCRAPERS:
        platform_results = [r for r in results if r.platform == platform]
        if not platform_results:
            continue

        total = len(platform_results)
        success = sum(1 for r in platform_results if r.scrape_success)
        failed = total - success

        prices = [r.product_price_mxn for r in platform_results if r.product_price_mxn]
        avg_price = f"${sum(prices) / len(prices):.0f}" if prices else "N/A"

        fees = [r.delivery_fee_mxn for r in platform_results if r.delivery_fee_mxn]
        avg_fee = f"${sum(fees) / len(fees):.0f}" if fees else "N/A"

        table.add_row(platform, str(total), str(success), str(failed), avg_price, avg_fee)

    console.print(table)


# ── Main pipeline ─────────────────────────────────────────────────

async def run_pipeline(
    platforms: list[str],
    addresses_limit: int | None = None,
    metro_areas: list[str] | None = None,
    use_cloudflare: bool = False,
):
    """Execute the full scraping pipeline.

    By default, uses SSR extraction (FREE) for Rappi and Uber Eats.
    Use --use-cloudflare flag to force Cloudflare Browser Rendering.
    """
    # Convert config addresses to the format SSR scrapers expect
    from rappi_ssr_scraper import Address as SSRAddress

    config_addresses = [
        address for address in ADDRESSES
        if not metro_areas or address.metro_area in metro_areas
    ]
    config_addresses = config_addresses[:addresses_limit] if addresses_limit else config_addresses

    # Convert to SSR address format
    addresses = [
        SSRAddress(
            id=addr.id,
            name=addr.name,
            zone_type=addr.zone_type,
            metro_area=addr.metro_area,
            lat=addr.lat,
            lng=addr.lng,
        )
        for addr in config_addresses
    ]

    # Convert products to SSR format
    from rappi_ssr_scraper import Product as SSRProduct
    products = [
        SSRProduct(
            id=p.id,
            name=p.name,
            search_terms=p.search_terms,
        )
        for p in PRODUCTS
    ]

    all_results = []

    mode = "Cloudflare" if use_cloudflare else "SSR (FREE)"
    console.print(f"\n[bold]Competitive Intelligence Scraper[/bold]")
    console.print(f"Mode: [green]{mode}[/green]")
    console.print(f"Platforms: {', '.join(platforms)}")
    console.print(
        f"Metro areas: {', '.join(metro_areas) if metro_areas else 'all configured areas'}"
    )
    console.print(f"Addresses: {len(addresses)}")
    console.print(f"Products: {len(products)}")
    console.print(f"Expected data points: {len(platforms) * len(addresses) * len(products)}")
    console.print()

    if use_cloudflare:
        # Legacy mode: use Cloudflare for all platforms
        async with CloudflareClient() as client:
            for platform_name in platforms:
                scraper_class = CLOUDFLARE_SCRAPERS.get(platform_name)
                if not scraper_class:
                    console.print(f"[yellow]Skipping {platform_name}: not available in Cloudflare mode[/yellow]")
                    continue

                scraper = scraper_class()
                console.print(f"\n[bold cyan]--- {platform_name.upper()} ---[/bold cyan]")
                results = await scraper.scrape_all(client, config_addresses, PRODUCTS)
                all_results.extend(results)
    else:
        # SSR mode: use free extraction for Rappi and Uber Eats
        for platform_name in platforms:
            console.print(f"\n[bold cyan]--- {platform_name.upper()} ---[/bold cyan]")

            if platform_name == "rappi":
                async with RappiSSRScraper() as scraper:
                    results = await scraper.scrape_all(None, addresses, products)
                    # Convert SSR results to standard format
                    for r in results:
                        all_results.append(ScrapedDataPoint(
                            platform=r.platform,
                            address_id=r.address_id,
                            address_name=r.address_name,
                            zone_type=r.zone_type,
                            metro_area=r.metro_area,
                            product_id=r.product_id,
                            product_name=r.product_name,
                            product_price_mxn=r.product_price_mxn,
                            discounted_price_mxn=r.discounted_price_mxn,
                            delivery_fee_mxn=r.delivery_fee_mxn,
                            service_fee_mxn=r.service_fee_mxn,
                            total_price_mxn=r.total_price_mxn,
                            estimated_minutes_min=r.estimated_minutes_min,
                            estimated_minutes_max=r.estimated_minutes_max,
                            restaurant_available=r.restaurant_available,
                            product_available=r.product_available,
                            discount_text=r.discount_text,
                            platform_promotions=r.platform_promotions,
                            scrape_success=r.scrape_success,
                            error_message=r.error_message,
                            url_scraped=r.url_scraped,
                        ))

            elif platform_name == "ubereats":
                # Try Playwright first (full data), fall back to SSR if not available
                use_playwright = True
                try:
                    from playwright.async_api import async_playwright
                    # Quick check if browsers are installed
                    import subprocess
                    result = subprocess.run(
                        ["playwright", "install", "--dry-run", "chromium"],
                        capture_output=True, timeout=5
                    )
                except Exception:
                    use_playwright = False
                    console.print("[yellow]Playwright not available, using SSR (limited data)[/yellow]")

                if use_playwright:
                    try:
                        async with UberEatsPlaywrightScraper() as scraper:
                            results = await scraper.scrape_all(addresses, products)
                    except Exception as e:
                        console.print(f"[yellow]Playwright failed: {e}[/yellow]")
                        console.print("[yellow]Falling back to SSR...[/yellow]")
                        use_playwright = False

                if not use_playwright:
                    # Fallback to SSR (no delivery fee/ETA but works everywhere)
                    async with UberEatsSSRScraper() as scraper:
                        results = await scraper.scrape_all(addresses, products)

                for r in results:
                    all_results.append(ScrapedDataPoint(
                        platform=r.platform,
                        address_id=r.address_id,
                        address_name=r.address_name,
                        zone_type=r.zone_type,
                        metro_area=r.metro_area,
                        product_id=r.product_id,
                        product_name=r.product_name,
                        product_price_mxn=r.product_price_mxn,
                        discounted_price_mxn=r.discounted_price_mxn,
                        delivery_fee_mxn=r.delivery_fee_mxn,
                        service_fee_mxn=r.service_fee_mxn,
                        total_price_mxn=r.total_price_mxn,
                        estimated_minutes_min=r.estimated_minutes_min,
                        estimated_minutes_max=r.estimated_minutes_max,
                        restaurant_available=r.restaurant_available,
                        product_available=r.product_available,
                        discount_text=r.discount_text,
                        platform_promotions=r.platform_promotions if hasattr(r, 'platform_promotions') else [],
                        scrape_success=r.scrape_success,
                        error_message=r.error_message,
                        url_scraped=r.url_scraped,
                    ))

            elif platform_name == "didifood":
                console.print("[yellow]DiDi Food has a login wall - SSR extraction not possible.[/yellow]")
                console.print("[yellow]Use --use-cloudflare flag to try Cloudflare (may still fail).[/yellow]")
                console.print("[yellow]Skipping DiDi Food.[/yellow]")
                continue
            else:
                console.print(f"[yellow]Unknown platform: {platform_name}[/yellow]")
                continue

    # Save results
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    json_path, csv_path = save_results(all_results, settings.raw_data_dir, timestamp)

    console.print(f"\n[bold green]Data saved:[/bold green]")
    console.print(f"  JSON: {json_path}")
    console.print(f"  CSV:  {csv_path}")

    # Summary
    print_summary(all_results)

    return all_results


# ── CLI ───────────────────────────────────────────────────────────

@click.command()
@click.option(
    "--platform", "-p",
    type=click.Choice(list(SCRAPERS.keys())),
    multiple=True,
    help="Specific platform(s) to scrape. Default: rappi, ubereats.",
)
@click.option(
    "--addresses", "-a",
    type=int,
    default=None,
    help="Limit to first N addresses (for testing).",
)
@click.option(
    "--metro-area", "-m",
    "metro_areas",
    type=click.Choice(MARKET_AREAS),
    multiple=True,
    help="Limit scraping to one or more metro areas.",
)
@click.option(
    "--use-cloudflare",
    is_flag=True,
    help="Use Cloudflare Browser Rendering instead of SSR (costs API credits).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate configuration without scraping.",
)
@click.option(
    "--test-data",
    is_flag=True,
    help="Use synthetic test data instead of real-time scraping. Includes all 3 platforms.",
)
@click.option(
    "--log-level", "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging verbosity.",
)
def main(platform, addresses, metro_areas, use_cloudflare, dry_run, test_data, log_level):
    """Rappi Competitive Intelligence — Data Collection Pipeline.

    By default, uses FREE SSR extraction for Rappi and Uber Eats.
    DiDi Food requires authentication and is skipped unless --use-cloudflare is set.
    Use --test-data to generate synthetic test data with all 3 platforms.
    """
    setup_logging(log_level)

    # SSR mode doesn't need Cloudflare config validation
    if use_cloudflare and not test_data:
        errors = settings.validate()
        if errors:
            for error in errors:
                console.print(f"[bold red]Config Error:[/bold red] {error}")
            if not dry_run:
                sys.exit(1)

    if dry_run:
        console.print("[bold green]Configuration valid[/bold green]")
        if test_data:
            console.print(f"  Mode: Synthetic Test Data")
        elif use_cloudflare:
            console.print(f"  Mode: Cloudflare Browser Rendering")
            console.print(f"  Account ID: {settings.cf_account_id[:8]}...")
        else:
            console.print(f"  Mode: SSR extraction (FREE)")
        console.print(f"  Addresses: {len(ADDRESSES)}")
        console.print(f"  Products: {len(PRODUCTS)}")
        return

    # Test data mode: generate synthetic data for all 3 platforms
    if test_data:
        console.print("\n[bold]Competitive Intelligence Scraper — Test Data Mode[/bold]")
        console.print("[yellow]Using synthetic data with realistic market patterns[/yellow]")
        console.print(f"Platforms: rappi, ubereats, didifood (all included)")
        console.print(f"Addresses: {len(ADDRESSES)}")
        console.print(f"Products: {len(PRODUCTS)}")
        console.print()

        # Generate synthetic data
        synthetic_data = generate_synthetic_data()

        # Filter by metro area if specified
        selected_metro_areas = list(metro_areas) if metro_areas else None
        if selected_metro_areas:
            synthetic_data = [
                d for d in synthetic_data
                if d["metro_area"] in selected_metro_areas
            ]
            console.print(f"Filtered to metro areas: {', '.join(selected_metro_areas)}")

        # Filter by address limit if specified
        if addresses:
            address_ids = [addr.id for addr in ADDRESSES[:addresses]]
            synthetic_data = [
                d for d in synthetic_data
                if d["address_id"] in address_ids
            ]
            console.print(f"Limited to first {addresses} addresses")

        # Convert to ScrapedDataPoint objects for consistent output
        results = [
            ScrapedDataPoint(
                platform=d["platform"],
                address_id=d["address_id"],
                address_name=d["address_name"],
                zone_type=d["zone_type"],
                metro_area=d["metro_area"],
                product_id=d["product_id"],
                product_name=d["product_name"],
                product_price_mxn=d["product_price_mxn"],
                discounted_price_mxn=d["discounted_price_mxn"],
                delivery_fee_mxn=d["delivery_fee_mxn"],
                service_fee_mxn=d["service_fee_mxn"],
                total_price_mxn=d["total_price_mxn"],
                estimated_minutes_min=d["estimated_minutes_min"],
                estimated_minutes_max=d["estimated_minutes_max"],
                restaurant_available=d["restaurant_available"],
                product_available=d["product_available"],
                discount_text=d["discount_text"],
                platform_promotions=d["platform_promotions"],
                scrape_success=d["scrape_success"],
                error_message=d["error_message"],
                url_scraped=d["url_scraped"],
            )
            for d in synthetic_data
        ]

        # Save results
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
        json_path, csv_path = save_results(results, settings.raw_data_dir, timestamp)

        console.print(f"\n[bold green]Synthetic data saved:[/bold green]")
        console.print(f"  JSON: {json_path}")
        console.print(f"  CSV:  {csv_path}")
        console.print(f"  Total data points: {len(results)}")

        # Summary
        print_summary(results)
        return

    # Default to rappi and ubereats only (didifood has login wall)
    platforms = list(platform) if platform else ["rappi", "ubereats"]
    selected_metro_areas = list(metro_areas) if metro_areas else None
    asyncio.run(run_pipeline(platforms, addresses, selected_metro_areas, use_cloudflare))


if __name__ == "__main__":
    main()
