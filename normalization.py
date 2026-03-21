"""
Data normalization — clean and standardize raw scraped data.

Handles:
- Type coercion (strings to numbers)
- Outlier detection & flagging
- Missing value handling
- Price validation against expected ranges
"""

import logging

import pandas as pd
import numpy as np

from config.products import PRODUCTS

logger = logging.getLogger(__name__)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize raw scraped data.

    Steps:
    1. Filter to successful scrapes only (keep failures for coverage reporting)
    2. Coerce numeric columns
    3. Validate prices against expected ranges
    4. Flag outliers
    5. Compute derived metrics
    """
    df = df.copy()

    # Step 1: Type coercion
    numeric_cols = [
        "product_price_mxn", "discounted_price_mxn",
        "delivery_fee_mxn", "service_fee_mxn", "total_price_mxn",
        "estimated_minutes_min", "estimated_minutes_max",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Step 2: Boolean coercion
    bool_cols = ["scrape_success", "restaurant_available", "product_available"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    # Step 3: Filter successful scrapes for analysis
    df_clean = df[df["scrape_success"] == True].copy()
    dropped = len(df) - len(df_clean)
    if dropped > 0:
        logger.info(f"Filtered {dropped} failed scrapes (kept for coverage report)")

    # Step 4: Validate prices against expected ranges
    product_ranges = {p.id: p.expected_price_range for p in PRODUCTS}
    df_clean["price_valid"] = df_clean.apply(
        lambda row: _validate_price(
            row.get("product_price_mxn"),
            product_ranges.get(row.get("product_id"), (0, 9999))
        ),
        axis=1,
    )
    invalid_count = (~df_clean["price_valid"]).sum()
    if invalid_count > 0:
        logger.warning(f"{invalid_count} prices outside expected range — flagged")

    # Step 5: Compute derived metrics
    df_clean["effective_price"] = df_clean.apply(
        lambda r: r["discounted_price_mxn"]
        if pd.notna(r.get("discounted_price_mxn"))
        else r.get("product_price_mxn"),
        axis=1,
    )

    df_clean["total_cost"] = (
        df_clean["effective_price"].fillna(0)
        + df_clean["delivery_fee_mxn"].fillna(0)
        + df_clean["service_fee_mxn"].fillna(0)
    )

    df_clean["has_discount"] = df_clean["discounted_price_mxn"].notna()

    df_clean["delivery_time_avg"] = (
        df_clean[["estimated_minutes_min", "estimated_minutes_max"]]
        .mean(axis=1)
    )

    return df_clean


def _validate_price(price, expected_range: tuple[float, float]) -> bool:
    """Check if a price falls within the expected range (with 50% tolerance)."""
    if pd.isna(price) or price is None:
        return False
    low, high = expected_range
    tolerance = 0.5
    return (low * (1 - tolerance)) <= price <= (high * (1 + tolerance))


def compute_coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a coverage report showing scraping success rate
    by platform × zone type.
    """
    coverage = (
        df.groupby(["platform", "zone_type"])
        .agg(
            total=("scrape_success", "count"),
            success=("scrape_success", "sum"),
        )
        .reset_index()
    )
    coverage["success_rate"] = (coverage["success"] / coverage["total"] * 100).round(1)
    return coverage
