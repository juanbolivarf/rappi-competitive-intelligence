"""
Competitive Intelligence Scraper — Main Orchestrator.

Entry point for the scraping pipeline. Coordinates all platform scrapers,
manages the Cloudflare client lifecycle, and outputs structured data.

Usage:
    python -m scraper.main                     # Full run
    python -m scraper.main --platform rappi    # Single platform
    python -m scraper.main --addresses 5       # Subset (first N)
    python -m scraper.main --dry-run           # Validate config only
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
from scraper.rappi_scraper import RappiScraper
from scraper.ubereats_scraper import UberEatsScraper
from scraper.didifood_scraper import DiDiFoodScraper

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

SCRAPERS = {
    "rappi": RappiScraper,
    "ubereats": UberEatsScraper,
    "didifood": DiDiFoodScraper,
}


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
):
    """Execute the full scraping pipeline."""
    addresses = [
        address for address in ADDRESSES
        if not metro_areas or address.metro_area in metro_areas
    ]
    addresses = addresses[:addresses_limit] if addresses_limit else addresses
    all_results: list[ScrapedDataPoint] = []

    console.print(f"\n[bold]Competitive Intelligence Scraper[/bold]")
    console.print(f"Platforms: {', '.join(platforms)}")
    console.print(
        f"Metro areas: {', '.join(metro_areas) if metro_areas else 'all configured areas'}"
    )
    console.print(f"Addresses: {len(addresses)}")
    console.print(f"Products: {len(PRODUCTS)}")
    console.print(f"Expected data points: {len(platforms) * len(addresses) * len(PRODUCTS)}")
    console.print()

    async with CloudflareClient() as client:
        for platform_name in platforms:
            scraper_class = SCRAPERS[platform_name]
            scraper = scraper_class()

            console.print(f"\n[bold cyan]━━━ {platform_name.upper()} ━━━[/bold cyan]")
            results = await scraper.scrape_all(client, addresses, PRODUCTS)
            all_results.extend(results)

    # Save results
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    json_path, csv_path = save_results(all_results, settings.raw_data_dir, timestamp)

    console.print(f"\n[bold green]✓ Data saved:[/bold green]")
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
    help="Specific platform(s) to scrape. Default: all.",
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
    "--dry-run",
    is_flag=True,
    help="Validate configuration without scraping.",
)
@click.option(
    "--log-level", "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging verbosity.",
)
def main(platform, addresses, metro_areas, dry_run, log_level):
    """Rappi Competitive Intelligence — Data Collection Pipeline."""
    setup_logging(log_level)

    # Validate config
    errors = settings.validate()
    if errors:
        for error in errors:
            console.print(f"[bold red]Config Error:[/bold red] {error}")
        if not dry_run:
            sys.exit(1)

    if dry_run:
        console.print("[bold green]✓ Configuration valid[/bold green]")
        console.print(f"  Account ID: {settings.cf_account_id[:8]}...")
        console.print(f"  Addresses: {len(ADDRESSES)}")
        console.print(f"  Products: {len(PRODUCTS)}")
        console.print(f"  Rate limit: {settings.scrape_delay_seconds}s between requests")
        return

    platforms = list(platform) if platform else list(SCRAPERS.keys())
    selected_metro_areas = list(metro_areas) if metro_areas else None
    asyncio.run(run_pipeline(platforms, addresses, selected_metro_areas))


if __name__ == "__main__":
    main()
