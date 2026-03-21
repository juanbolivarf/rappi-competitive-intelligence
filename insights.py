"""
Insight generation engine.

Automatically generates the Top 5 actionable insights from comparison data.
Each insight follows the structure required by the case:
  - Finding: What did we discover?
  - Impact: Why does it matter?
  - Recommendation: What should Rappi do?

Insights are ranked by potential business impact.
"""

import logging
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def generate_insights(
    df: pd.DataFrame,
    comparisons: dict[str, pd.DataFrame],
) -> list[dict[str, str]]:
    """
    Generate Top 5 actionable insights from the competitive data.

    Returns list of dicts with keys: finding, impact, recommendation, category, priority
    """
    insights = []

    # Attempt to generate each insight type
    insight_generators = [
        _insight_price_positioning,
        _insight_delivery_fee_gaps,
        _insight_zone_competitiveness,
        _insight_delivery_time,
        _insight_promotion_strategy,
        _insight_total_cost_comparison,
        _insight_availability_gaps,
    ]

    for generator in insight_generators:
        try:
            insight = generator(df, comparisons)
            if insight:
                insights.append(insight)
        except Exception as e:
            logger.warning(f"Failed to generate insight from {generator.__name__}: {e}")

    # Sort by priority and return top 5
    insights.sort(key=lambda x: x.get("priority", 99))
    return insights[:5]


def _insight_price_positioning(
    df: pd.DataFrame, comparisons: dict
) -> dict[str, str] | None:
    """Analyze Rappi's overall price positioning vs competition."""
    delta = comparisons.get("rappi_delta")
    if delta is None or delta.empty:
        return None

    avg_delta = delta["price_delta_pct"].mean()
    direction = "más caro" if avg_delta > 0 else "más barato"
    abs_delta = abs(avg_delta)

    if abs_delta < 2:
        return None  # Not significant enough

    return {
        "finding": (
            f"Rappi's product prices are on average {abs_delta:.1f}% {direction} "
            f"than competitors across all zones in Guadalajara."
        ),
        "impact": (
            f"A {'higher' if avg_delta > 0 else 'lower'} price position directly affects "
            f"conversion rates and order volume. In price-sensitive segments "
            f"(students, peripheral zones), even a 5% difference drives platform switching."
        ),
        "recommendation": (
            f"{'Review pricing agreements with restaurant partners in zones where the gap is largest. '
            'Consider selective price matching on high-visibility items (Big Mac, combos) '
            'where consumers actively compare.' if avg_delta > 0 else
            'Leverage the price advantage in marketing — communicate ''lowest price guarantee'' '
            'in zones where Rappi is cheapest. Protect margins on delivery fees instead.'}"
        ),
        "category": "pricing",
        "priority": 1,
    }


def _insight_delivery_fee_gaps(
    df: pd.DataFrame, comparisons: dict
) -> dict[str, str] | None:
    """Identify zones where delivery fees are uncompetitive."""
    delta = comparisons.get("rappi_delta")
    if delta is None or delta.empty:
        return None

    # Find zones where Rappi's fees are highest
    zone_fees = delta.groupby("zone_type")["fee_delta_mxn"].mean()
    worst_zone = zone_fees.idxmax()
    worst_delta = zone_fees.max()

    if worst_delta <= 0:
        return None  # Rappi is competitive on fees everywhere

    return {
        "finding": (
            f"Rappi's delivery fees in {worst_zone.replace('_', ' ')} zones are "
            f"${worst_delta:.0f} MXN higher than the competitor average."
        ),
        "impact": (
            f"Delivery fees are the most visible cost component and the #1 reason "
            f"users switch platforms. In {worst_zone.replace('_', ' ')} zones, this gap "
            f"compounds with higher product prices, making Rappi the most expensive option "
            f"for total order cost."
        ),
        "recommendation": (
            f"Subsidize delivery fees in {worst_zone.replace('_', ' ')} zones for a "
            f"targeted 2-week test. Measure impact on order volume vs. fee revenue loss. "
            f"Consider implementing zone-specific fee optimization using demand elasticity data."
        ),
        "category": "fees",
        "priority": 2,
    }


def _insight_zone_competitiveness(
    df: pd.DataFrame, comparisons: dict
) -> dict[str, str] | None:
    """Identify geographic patterns in competitiveness."""
    delta = comparisons.get("rappi_delta")
    if delta is None or delta.empty:
        return None

    # Zone-level total cost comparison
    zone_total = delta.groupby("zone_type")["total_delta_mxn"].mean()
    best_zone = zone_total.idxmin()
    worst_zone = zone_total.idxmax()

    if zone_total.max() - zone_total.min() < 5:
        return None  # No significant geographic variation

    return {
        "finding": (
            f"Rappi's competitiveness varies significantly by zone: strongest in "
            f"{best_zone.replace('_', ' ')} (${abs(zone_total[best_zone]):.0f} cheaper) "
            f"and weakest in {worst_zone.replace('_', ' ')} "
            f"(${zone_total[worst_zone]:.0f} more expensive)."
        ),
        "impact": (
            f"Geographic pricing inconsistency means Rappi is leaving market share "
            f"on the table in {worst_zone.replace('_', ' ')} zones while potentially "
            f"over-investing in {best_zone.replace('_', ' ')} zones where it already leads."
        ),
        "recommendation": (
            f"Implement zone-tiered pricing strategy: protect margins in "
            f"{best_zone.replace('_', ' ')} zones (strong position) and invest in "
            f"closing the gap in {worst_zone.replace('_', ' ')} zones through "
            f"targeted fee subsidies or promotional campaigns."
        ),
        "category": "geographic",
        "priority": 3,
    }


def _insight_delivery_time(
    df: pd.DataFrame, comparisons: dict
) -> dict[str, str] | None:
    """Compare delivery time competitiveness."""
    delta = comparisons.get("rappi_delta")
    if delta is None or delta.empty:
        return None

    avg_time_delta = delta["time_delta_min"].mean()
    if abs(avg_time_delta) < 2:
        return None  # Not significant

    faster_or_slower = "slower" if avg_time_delta > 0 else "faster"

    return {
        "finding": (
            f"Rappi's estimated delivery times are on average {abs(avg_time_delta):.0f} "
            f"minutes {faster_or_slower} than competitors across Guadalajara."
        ),
        "impact": (
            f"Delivery speed is the second most important factor (after price) in "
            f"platform selection. {'Slower delivery times compound with any price '
            'disadvantage, reducing the value proposition.' if avg_time_delta > 0 else
            'Faster delivery is a strong competitive advantage that can justify '
            'slightly higher prices or fees.'}"
        ),
        "recommendation": (
            f"{'Investigate operational bottlenecks: driver density in underserved zones, '
            'restaurant prep time optimization, and routing efficiency. Consider Turbo '
            'dark store expansion in zones with largest time gaps.' if avg_time_delta > 0 else
            'Highlight speed advantage in marketing. Test ''Delivery in X minutes or free'' '
            'guarantee in zones where Rappi is consistently fastest.'}"
        ),
        "category": "operations",
        "priority": 4,
    }


def _insight_promotion_strategy(
    df: pd.DataFrame, comparisons: dict
) -> dict[str, str] | None:
    """Analyze competitor promotion intensity."""
    promo = comparisons.get("promotions")
    if promo is None or promo.empty:
        return None

    rappi_row = promo[promo["platform"] == "rappi"]
    comp_rows = promo[promo["platform"] != "rappi"]

    if rappi_row.empty or comp_rows.empty:
        return None

    rappi_rate = rappi_row["discount_rate"].iloc[0]
    comp_avg_rate = comp_rows["discount_rate"].mean()
    gap = comp_avg_rate - rappi_rate

    if abs(gap) < 0.05:
        return None  # Minimal difference

    more_or_fewer = "fewer" if gap > 0 else "more"

    return {
        "finding": (
            f"Rappi is running {more_or_fewer} promotions than competitors: "
            f"{rappi_rate:.0%} of products discounted vs {comp_avg_rate:.0%} industry average."
        ),
        "impact": (
            f"{'Competitors are using aggressive discounting to capture market share. '
            'Without matching, Rappi risks losing price-sensitive segments.' if gap > 0 else
            'Rappi''s heavier discounting may be eroding margins without proportional '
            'volume gains. Evaluate ROI per promotion.'}"
        ),
        "recommendation": (
            f"{'Launch targeted counter-promotions on high-visibility products '
            '(Big Mac, combos) in the zones where competitor discounts are deepest. '
            'Focus on first-order and reactivation campaigns.' if gap > 0 else
            'Rationalize promotion spend: A/B test reducing discounts by 10-20% in '
            'zones where Rappi already leads on total cost. Redirect savings to '
            'delivery fee subsidies in weak zones.'}"
        ),
        "category": "promotions",
        "priority": 5,
    }


def _insight_total_cost_comparison(
    df: pd.DataFrame, comparisons: dict
) -> dict[str, str] | None:
    """Total cost (price + all fees) comparison — what the user actually pays."""
    summary = comparisons.get("summary")
    if summary is None or summary.empty:
        return None

    rappi_total = summary.loc[summary["platform"] == "rappi", "avg_total_cost"]
    if rappi_total.empty:
        return None

    rappi_total = rappi_total.iloc[0]
    cheapest = summary["avg_total_cost"].min()
    cheapest_platform = summary.loc[summary["avg_total_cost"].idxmin(), "platform"]

    if cheapest_platform == "rappi":
        return {
            "finding": (
                f"Rappi offers the lowest average total cost (product + fees) "
                f"at ${rappi_total:.0f} MXN across Guadalajara."
            ),
            "impact": "Total cost leadership is the strongest competitive position in delivery.",
            "recommendation": (
                "Amplify this message in marketing: 'Lowest total price' campaigns "
                "with side-by-side comparisons. Protect this position by monitoring "
                "competitor fee changes weekly."
            ),
            "category": "pricing",
            "priority": 1,
        }

    gap = rappi_total - cheapest
    return {
        "finding": (
            f"Rappi's average total cost is ${gap:.0f} MXN higher than "
            f"{cheapest_platform}, which offers the lowest total at ${cheapest:.0f} MXN."
        ),
        "impact": (
            f"Users compare the final price at checkout. A ${gap:.0f} MXN difference "
            f"on a typical order represents a {gap/rappi_total*100:.0f}% premium — "
            f"significant enough to drive platform switching."
        ),
        "recommendation": (
            f"Identify which cost component (product price vs delivery fee vs service fee) "
            f"drives the gap. Target the most actionable lever first — delivery fee "
            f"subsidies have the fastest impact on perceived total cost."
        ),
        "category": "pricing",
        "priority": 1,
    }


def _insight_availability_gaps(
    df: pd.DataFrame, comparisons: dict
) -> dict[str, str] | None:
    """Identify zones where Rappi has lower restaurant/product availability."""
    rappi = df[df["platform"] == "rappi"]
    comps = df[df["platform"] != "rappi"]

    if rappi.empty or comps.empty:
        return None

    rappi_avail = rappi.groupby("zone_type")["product_available"].mean()
    comp_avail = comps.groupby("zone_type")["product_available"].mean()

    merged = pd.DataFrame({"rappi": rappi_avail, "competition": comp_avail}).dropna()
    merged["gap"] = merged["competition"] - merged["rappi"]

    worst = merged["gap"].idxmax() if not merged.empty else None
    if worst is None or merged.loc[worst, "gap"] < 0.1:
        return None

    return {
        "finding": (
            f"In {worst.replace('_', ' ')} zones, competitor product availability "
            f"is {merged.loc[worst, 'gap']:.0%} higher than Rappi's."
        ),
        "impact": (
            "When a user searches and finds 'Restaurant not available' or 'Product unavailable', "
            "they switch platforms immediately. Availability gaps drive permanent user loss."
        ),
        "recommendation": (
            f"Prioritize restaurant onboarding and operational support in "
            f"{worst.replace('_', ' ')} zones. Investigate whether gaps are due to "
            f"fewer affiliated restaurants or operational hours differences."
        ),
        "category": "operations",
        "priority": 3,
    }
