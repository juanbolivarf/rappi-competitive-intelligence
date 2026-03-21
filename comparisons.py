"""
Cross-platform comparison engine.

Generates the structured comparisons that feed into insight generation:
- Price positioning by zone
- Delivery fee comparison
- Delivery time comparison
- Promotion intensity analysis
- Overall competitiveness score
"""

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def run_comparisons(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Run all comparison analyses and return results as DataFrames.

    Returns dict with keys:
    - summary: Overall platform comparison
    - price_by_zone: Price positioning per zone type
    - fees_by_zone: Fee structure per zone type
    - delivery_time: Delivery time comparison
    - promotions: Promotion activity analysis
    - rappi_delta: Rappi vs competition deltas
    """
    results = {}

    results["summary"] = _platform_summary(df)
    results["price_by_zone"] = _price_by_zone(df)
    results["fees_by_zone"] = _fees_by_zone(df)
    results["delivery_time"] = _delivery_time_comparison(df)
    results["promotions"] = _promotion_analysis(df)
    results["rappi_delta"] = _rappi_vs_competition(df)

    return results


def _platform_summary(df: pd.DataFrame) -> pd.DataFrame:
    """High-level comparison across all metrics by platform."""
    summary = (
        df.groupby("platform")
        .agg(
            avg_product_price=("effective_price", "mean"),
            median_product_price=("effective_price", "median"),
            avg_delivery_fee=("delivery_fee_mxn", "mean"),
            avg_service_fee=("service_fee_mxn", "mean"),
            avg_total_cost=("total_cost", "mean"),
            avg_delivery_time=("delivery_time_avg", "mean"),
            discount_rate=("has_discount", "mean"),
            data_points=("platform", "count"),
            availability_rate=("product_available", "mean"),
        )
        .round(2)
        .reset_index()
    )

    # Rank columns (1 = best/cheapest)
    for col in ["avg_total_cost", "avg_delivery_fee", "avg_delivery_time"]:
        if col in summary.columns:
            summary[f"{col}_rank"] = summary[col].rank(method="min")

    return summary


def _price_by_zone(df: pd.DataFrame) -> pd.DataFrame:
    """Product price comparison by zone type and platform."""
    return (
        df.groupby(["zone_type", "platform", "product_id"])
        .agg(
            avg_price=("effective_price", "mean"),
            min_price=("effective_price", "min"),
            max_price=("effective_price", "max"),
            count=("effective_price", "count"),
        )
        .round(2)
        .reset_index()
    )


def _fees_by_zone(df: pd.DataFrame) -> pd.DataFrame:
    """Delivery and service fee comparison by zone."""
    return (
        df.groupby(["zone_type", "platform"])
        .agg(
            avg_delivery_fee=("delivery_fee_mxn", "mean"),
            avg_service_fee=("service_fee_mxn", "mean"),
            avg_total_fees=("delivery_fee_mxn", lambda x: x.fillna(0).mean()
                + df.loc[x.index, "service_fee_mxn"].fillna(0).mean()),
        )
        .round(2)
        .reset_index()
    )


def _delivery_time_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Delivery time comparison by platform and zone."""
    return (
        df.groupby(["zone_type", "platform"])
        .agg(
            avg_time=("delivery_time_avg", "mean"),
            min_time=("estimated_minutes_min", "min"),
            max_time=("estimated_minutes_max", "max"),
        )
        .round(1)
        .reset_index()
    )


def _promotion_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze promotion activity across platforms."""
    promo = (
        df.groupby("platform")
        .agg(
            products_with_discount=("has_discount", "sum"),
            total_products=("has_discount", "count"),
            discount_rate=("has_discount", "mean"),
            avg_discount_pct=("effective_price", lambda x: _calc_avg_discount(df, x.index)),
        )
        .round(2)
        .reset_index()
    )
    return promo


def _calc_avg_discount(df: pd.DataFrame, idx) -> float:
    """Calculate average discount percentage for discounted items."""
    subset = df.loc[idx]
    discounted = subset[subset["has_discount"]]
    if discounted.empty:
        return 0.0
    pct = (
        (discounted["product_price_mxn"] - discounted["discounted_price_mxn"])
        / discounted["product_price_mxn"]
        * 100
    )
    return pct.mean()


def _rappi_vs_competition(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Rappi's position relative to each competitor.
    Positive delta = Rappi is MORE expensive.
    Negative delta = Rappi is CHEAPER.
    """
    rappi = df[df["platform"] == "rappi"]
    competitors = df[df["platform"] != "rappi"]

    if rappi.empty or competitors.empty:
        logger.warning("Insufficient data for Rappi vs competition comparison")
        return pd.DataFrame()

    # Average by zone and product for Rappi
    rappi_avg = (
        rappi.groupby(["zone_type", "product_id"])
        .agg(rappi_price=("effective_price", "mean"),
             rappi_fee=("delivery_fee_mxn", "mean"),
             rappi_total=("total_cost", "mean"),
             rappi_time=("delivery_time_avg", "mean"))
        .reset_index()
    )

    # Average by zone, product, and competitor platform
    comp_avg = (
        competitors.groupby(["zone_type", "product_id", "platform"])
        .agg(comp_price=("effective_price", "mean"),
             comp_fee=("delivery_fee_mxn", "mean"),
             comp_total=("total_cost", "mean"),
             comp_time=("delivery_time_avg", "mean"))
        .reset_index()
    )

    # Merge and compute deltas
    merged = comp_avg.merge(rappi_avg, on=["zone_type", "product_id"], how="inner")

    merged["price_delta_mxn"] = (merged["rappi_price"] - merged["comp_price"]).round(2)
    merged["price_delta_pct"] = (
        (merged["rappi_price"] - merged["comp_price"]) / merged["comp_price"] * 100
    ).round(1)
    merged["fee_delta_mxn"] = (merged["rappi_fee"] - merged["comp_fee"]).round(2)
    merged["total_delta_mxn"] = (merged["rappi_total"] - merged["comp_total"]).round(2)
    merged["time_delta_min"] = (merged["rappi_time"] - merged["comp_time"]).round(1)

    return merged
