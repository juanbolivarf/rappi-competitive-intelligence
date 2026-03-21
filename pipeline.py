"""
Analysis Pipeline — From raw scraped data to actionable insights.

Usage:
    python -m analysis.pipeline
    python -m analysis.pipeline --input data/raw/scrape_2025-10-10.json
"""

import json
import logging
import sys
from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from config.settings import settings

console = Console()
logger = logging.getLogger(__name__)


def load_data(input_path: Path | None = None) -> pd.DataFrame:
    """Load the most recent scraped data (or a specific file)."""
    if input_path:
        path = input_path
    else:
        json_files = sorted(settings.raw_data_dir.glob("scrape_*.json"), reverse=True)
        if not json_files:
            console.print("[red]No scraped data found. Run the scraper first.[/red]")
            sys.exit(1)
        path = json_files[0]

    console.print(f"Loading data from: {path}")
    with open(path) as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    console.print(f"Loaded {len(df)} data points")
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize the scraped data."""
    df_clean = df[df["scrape_success"] == True].copy()

    numeric_cols = [
        "product_price_mxn", "discounted_price_mxn", "delivery_fee_mxn",
        "service_fee_mxn", "total_price_mxn",
        "estimated_minutes_min", "estimated_minutes_max",
    ]
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    df_clean["effective_price_mxn"] = df_clean["discounted_price_mxn"].fillna(
        df_clean["product_price_mxn"]
    )
    df_clean["total_user_cost"] = (
        df_clean["effective_price_mxn"].fillna(0)
        + df_clean["delivery_fee_mxn"].fillna(0)
        + df_clean["service_fee_mxn"].fillna(0)
    )
    df_clean["avg_delivery_minutes"] = (
        df_clean[["estimated_minutes_min", "estimated_minutes_max"]].mean(axis=1)
    )

    console.print(f"After normalization: {len(df_clean)} clean data points")
    return df_clean


def compare_platforms(df: pd.DataFrame) -> dict:
    """Generate cross-platform comparison metrics."""
    comparisons = {}

    comparisons["price_by_platform_product"] = df.groupby(
        ["platform", "product_id"]
    ).agg(
        avg_price=("effective_price_mxn", "mean"),
        median_price=("effective_price_mxn", "median"),
    ).round(2)

    comparisons["fees_by_platform_zone"] = df.groupby(
        ["platform", "zone_type"]
    ).agg(
        avg_delivery_fee=("delivery_fee_mxn", "mean"),
        avg_service_fee=("service_fee_mxn", "mean"),
    ).round(2)

    comparisons["time_by_platform_zone"] = df.groupby(
        ["platform", "zone_type"]
    ).agg(
        avg_delivery_time=("avg_delivery_minutes", "mean"),
    ).round(1)

    comparisons["total_cost_by_platform_product"] = df.groupby(
        ["platform", "product_id"]
    ).agg(
        avg_total_cost=("total_user_cost", "mean"),
    ).round(2)

    comparisons["availability_by_platform_zone"] = df.groupby(
        ["platform", "zone_type"]
    ).agg(
        restaurant_avail_pct=("restaurant_available", "mean"),
        product_avail_pct=("product_available", "mean"),
    ).round(3)

    return comparisons


def generate_insights(df: pd.DataFrame, comparisons: dict) -> list[dict]:
    """Generate Top 5 actionable insights (Finding -> Impact -> Recommendation)."""
    insights = []

    avg_price = df.groupby("platform")["effective_price_mxn"].mean()
    avg_fee = df.groupby("platform")["delivery_fee_mxn"].mean()
    avg_time = df.groupby("platform")["avg_delivery_minutes"].mean()
    promo_counts = df.groupby("platform")["discount_text"].apply(lambda x: x.notna().sum())
    avg_total = df.groupby("platform")["total_user_cost"].mean()

    insights.append({
        "number": 1,
        "title": "Price positioning across platforms",
        "finding": f"Rappi avg price: ${avg_price.get('rappi', 0):.0f} MXN vs "
                   f"Uber Eats: ${avg_price.get('ubereats', 0):.0f}, "
                   f"DiDi: ${avg_price.get('didifood', 0):.0f}.",
        "impact": "Price is #1 driver of platform selection in price-sensitive zones.",
        "recommendation": "Zone-level price parity analysis. Subsidize where >10% more expensive.",
    })

    insights.append({
        "number": 2,
        "title": "Delivery fee competitiveness by zone",
        "finding": f"Avg delivery fee — Rappi: ${avg_fee.get('rappi', 0):.0f}, "
                   f"UE: ${avg_fee.get('ubereats', 0):.0f}, "
                   f"DiDi: ${avg_fee.get('didifood', 0):.0f} MXN.",
        "impact": "Delivery fees are the most visible cost differentiator at checkout.",
        "recommendation": "Fee subsidies in peripheral zones; maintain fees in high-income zones.",
    })

    insights.append({
        "number": 3,
        "title": "Delivery time competitiveness",
        "finding": f"Avg time — Rappi: {avg_time.get('rappi', 0):.0f} min, "
                   f"UE: {avg_time.get('ubereats', 0):.0f}, "
                   f"DiDi: {avg_time.get('didifood', 0):.0f} min.",
        "impact": "Time correlates with satisfaction and repeat orders. Turbo depends on speed.",
        "recommendation": "Prioritize dark stores / Rappitendero allocation where >5 min slower.",
    })

    insights.append({
        "number": 4,
        "title": "Promotional intensity and strategy",
        "finding": f"Promotions detected — Rappi: {promo_counts.get('rappi', 0)}, "
                   f"UE: {promo_counts.get('ubereats', 0)}, "
                   f"DiDi: {promo_counts.get('didifood', 0)}.",
        "impact": "Promo-heavy zones signal competitive territory battles.",
        "recommendation": "Map competitor promo concentration. Counter-promote in contested zones.",
    })

    insights.append({
        "number": 5,
        "title": "Total cost to user — the real metric",
        "finding": f"Avg total checkout cost — Rappi: ${avg_total.get('rappi', 0):.0f}, "
                   f"UE: ${avg_total.get('ubereats', 0):.0f}, "
                   f"DiDi: ${avg_total.get('didifood', 0):.0f} MXN.",
        "impact": "Users compare checkout totals, not individual line items.",
        "recommendation": "Optimize total cost. Bundle fee reductions with minimum order thresholds.",
    })

    return insights


def save_analysis(df: pd.DataFrame, comparisons: dict, insights: list[dict]):
    """Save all outputs."""
    out = settings.processed_data_dir
    out.mkdir(parents=True, exist_ok=True)

    df.to_csv(out / "comparison_matrix.csv", index=False)
    for name, table in comparisons.items():
        table.to_csv(out / f"{name}.csv")

    with open(out / "insights.json", "w") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    console.print(f"[green]All outputs saved to {out}[/green]")


@click.command()
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), default=None)
def main(input_path):
    """Run the full analysis pipeline."""
    console.print("\n[bold]Competitive Intelligence — Analysis Pipeline[/bold]\n")

    path = Path(input_path) if input_path else None
    df = load_data(path)
    df_clean = normalize(df)
    comparisons = compare_platforms(df_clean)
    insights = generate_insights(df_clean, comparisons)

    for i in insights:
        console.print(f"\n  [bold]#{i['number']}: {i['title']}[/bold]")
        console.print(f"  {i['finding']}")

    save_analysis(df_clean, comparisons, insights)
    console.print("\n[bold green]✓ Analysis complete![/bold green]")


if __name__ == "__main__":
    main()
