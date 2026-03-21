"""
Visualization Engine — Publication-quality charts for the CI report.

Generates 5 charts aligned to the Top 5 Insights:
1. Price comparison grouped bars (platform × product)
2. Zone competitiveness heatmap (Rappi vs avg competitor by zone × product)
3. Fee structure stacked bars (delivery + service by platform)
4. Delivery time grouped bars (platform × zone)
5. Total cost to user (the real comparison — product + all fees)

Usage:
    python -m analysis.visualizations           # Generate all charts
    python -m analysis.visualizations --show    # Also display (requires GUI)
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches

logger = logging.getLogger(__name__)

# ── Style ─────────────────────────────────────────────────────────

COLORS = {
    "rappi": "#FF6B35",
    "ubereats": "#142328",
    "didifood": "#F5A623",
}
LABELS = {
    "rappi": "Rappi",
    "ubereats": "Uber Eats",
    "didifood": "DiDi Food",
}
ZONE_ORDER = ["high_income", "mid_income", "commercial", "university", "low_income"]
ZONE_LABELS = {
    "high_income": "High Income",
    "mid_income": "Mid Income",
    "commercial": "Commercial",
    "university": "University",
    "low_income": "Periférica",
}
PRODUCT_LABELS = {
    "bigmac": "Big Mac",
    "combo_mediano": "Combo Mediano",
    "nuggets_10": "Nuggets 10pc",
    "coca_500": "Coca-Cola 500ml",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "figure.dpi": 150,
    "legend.frameon": False,
    "legend.fontsize": 10,
})


def _platforms(df):
    return [p for p in ["rappi", "ubereats", "didifood"] if p in df["platform"].unique()]


def _add_value_labels(ax, bars, fmt="${:.0f}", offset=1, fontsize=9):
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2, h + offset,
                fmt.format(h), ha="center", va="bottom", fontsize=fontsize,
            )


# ── Chart 1: Price Comparison ────────────────────────────────────

def chart_price_comparison(df: pd.DataFrame) -> plt.Figure:
    """Grouped bar chart: avg product price by platform × product."""
    avail = df[df["product_available"] == True]
    summary = avail.groupby(["platform", "product_id"])["product_price_mxn"].mean().reset_index()

    products = list(PRODUCT_LABELS.keys())
    platforms = _platforms(df)
    n = len(products)
    w = 0.22
    x = np.arange(n)

    fig, ax = plt.subplots(figsize=(11, 6))

    for i, p in enumerate(platforms):
        vals = []
        for prod in products:
            row = summary[(summary["platform"] == p) & (summary["product_id"] == prod)]
            vals.append(row["product_price_mxn"].values[0] if len(row) else 0)
        bars = ax.bar(
            x + i * w, vals, w,
            label=LABELS[p], color=COLORS[p], edgecolor="white", linewidth=0.5,
        )
        _add_value_labels(ax, bars)

    ax.set_xticks(x + w)
    ax.set_xticklabels([PRODUCT_LABELS[p] for p in products])
    ax.set_ylabel("Average Price (MXN)")
    ax.set_title("Insight #1: Product Price Positioning by Platform\nGuadalajara Metro Area — 25 locations")
    ax.legend(loc="upper left")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%d"))
    ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
    fig.tight_layout()
    return fig


# ── Chart 2: Zone Heatmap ────────────────────────────────────────

def chart_zone_heatmap(df: pd.DataFrame) -> plt.Figure:
    """
    Heatmap: Rappi's total cost delta vs avg competitor, by zone × product.
    Green = Rappi cheaper, Red = Rappi more expensive.
    """
    avail = df[df["product_available"] == True].copy()
    avail["effective"] = avail["discounted_price_mxn"].fillna(avail["product_price_mxn"])
    avail["total_cost"] = (
        avail["effective"].fillna(0)
        + avail["delivery_fee_mxn"].fillna(0)
        + avail["service_fee_mxn"].fillna(0)
    )

    rappi = avail[avail["platform"] == "rappi"]
    competitors = avail[avail["platform"] != "rappi"]

    rappi_avg = rappi.groupby(["zone_type", "product_id"])["total_cost"].mean()
    comp_avg = competitors.groupby(["zone_type", "product_id"])["total_cost"].mean()

    delta_pct = ((rappi_avg - comp_avg) / comp_avg * 100).reset_index()
    delta_pct.columns = ["zone_type", "product_id", "delta_pct"]

    products = [p for p in PRODUCT_LABELS if p in delta_pct["product_id"].values]
    zones = [z for z in ZONE_ORDER if z in delta_pct["zone_type"].values]

    pivot = delta_pct.pivot(index="zone_type", columns="product_id", values="delta_pct")
    pivot = pivot.reindex(index=zones, columns=products)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    im = ax.imshow(pivot.values, cmap="RdYlGn_r", aspect="auto", vmin=-15, vmax=15)

    ax.set_xticks(range(len(products)))
    ax.set_xticklabels([PRODUCT_LABELS[p] for p in products])
    ax.set_yticks(range(len(zones)))
    ax.set_yticklabels([ZONE_LABELS[z] for z in zones])

    for i in range(len(zones)):
        for j in range(len(products)):
            val = pivot.iloc[i, j]
            if pd.notna(val):
                color = "white" if abs(val) > 8 else "black"
                sign = "+" if val > 0 else ""
                ax.text(j, i, f"{sign}{val:.1f}%", ha="center", va="center",
                        color=color, fontsize=11, fontweight="bold")

    ax.set_title("Insight #2: Rappi Total Cost vs Competition by Zone\nGreen = Cheaper · Red = More Expensive (% difference)")
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Rappi Premium (%)", fontsize=10)
    fig.tight_layout()
    return fig


# ── Chart 3: Fee Structure ───────────────────────────────────────

def chart_fee_structure(df: pd.DataFrame) -> plt.Figure:
    """Stacked bars: delivery fee + service fee by platform, split by zone."""
    avail = df[df["scrape_success"] == True]

    # Overall by platform
    fees = avail.groupby("platform").agg(
        delivery=("delivery_fee_mxn", "mean"),
        service=("service_fee_mxn", "mean"),
    ).reindex(_platforms(df))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [1, 1.8]})

    # Left: overall stacked bar
    platforms = fees.index.tolist()
    x = range(len(platforms))
    d = fees["delivery"].values
    s = fees["service"].values

    bars1 = ax1.bar(x, d, color=[COLORS[p] for p in platforms], label="Delivery Fee")
    bars2 = ax1.bar(x, s, bottom=d, color=[COLORS[p] for p in platforms],
                    alpha=0.45, hatch="///", label="Service Fee")

    for i, (dv, sv) in enumerate(zip(d, s)):
        ax1.text(i, dv + sv + 0.5, f"${dv + sv:.0f}", ha="center", fontsize=10, fontweight="bold")
        ax1.text(i, dv / 2, f"${dv:.0f}", ha="center", va="center", fontsize=9, color="white")
        ax1.text(i, dv + sv / 2, f"${sv:.0f}", ha="center", va="center", fontsize=9)

    ax1.set_xticks(x)
    ax1.set_xticklabels([LABELS[p] for p in platforms])
    ax1.set_ylabel("Average Fee (MXN)")
    ax1.set_title("Overall Fee Structure")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%d"))

    # Right: delivery fee by zone
    zone_fees = avail.groupby(["platform", "zone_type"])["delivery_fee_mxn"].mean().reset_index()
    zones = [z for z in ZONE_ORDER if z in zone_fees["zone_type"].values]
    w = 0.22
    xz = np.arange(len(zones))

    for i, p in enumerate(_platforms(df)):
        vals = []
        for z in zones:
            row = zone_fees[(zone_fees["platform"] == p) & (zone_fees["zone_type"] == z)]
            vals.append(row["delivery_fee_mxn"].values[0] if len(row) else 0)
        ax2.bar(xz + i * w, vals, w, label=LABELS[p], color=COLORS[p])

    ax2.set_xticks(xz + w)
    ax2.set_xticklabels([ZONE_LABELS[z] for z in zones], rotation=15, ha="right")
    ax2.set_ylabel("Avg Delivery Fee (MXN)")
    ax2.set_title("Delivery Fee by Zone Type")
    ax2.legend(fontsize=9)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%d"))

    fig.suptitle("Insight #3: Fee Structure Comparison", fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig


# ── Chart 4: Delivery Time ───────────────────────────────────────

def chart_delivery_time(df: pd.DataFrame) -> plt.Figure:
    """Grouped bars: avg delivery time by platform × zone."""
    avail = df[df["scrape_success"] == True].copy()
    avail["avg_time"] = (avail["estimated_minutes_min"] + avail["estimated_minutes_max"]) / 2

    time_data = avail.groupby(["platform", "zone_type"])["avg_time"].mean().reset_index()

    zones = [z for z in ZONE_ORDER if z in time_data["zone_type"].values]
    platforms = _platforms(df)
    w = 0.22
    x = np.arange(len(zones))

    fig, ax = plt.subplots(figsize=(11, 6))

    for i, p in enumerate(platforms):
        vals = []
        for z in zones:
            row = time_data[(time_data["platform"] == p) & (time_data["zone_type"] == z)]
            vals.append(row["avg_time"].values[0] if len(row) else 0)
        bars = ax.bar(xz := x + i * w, vals, w, label=LABELS[p], color=COLORS[p])
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3,
                        f"{v:.0f}", ha="center", fontsize=9)

    ax.set_xticks(x + w)
    ax.set_xticklabels([ZONE_LABELS[z] for z in zones], rotation=15, ha="right")
    ax.set_ylabel("Avg Estimated Delivery Time (min)")
    ax.set_title("Insight #4: Delivery Time Competitiveness by Zone\nLower = Better")
    ax.legend()
    ax.set_ylim(0, ax.get_ylim()[1] * 1.1)
    fig.tight_layout()
    return fig


# ── Chart 5: Total Cost to User ──────────────────────────────────

def chart_total_cost(df: pd.DataFrame) -> plt.Figure:
    """
    The chart that matters most: what does the user ACTUALLY pay?
    Product price + delivery fee + service fee.
    """
    avail = df[df["product_available"] == True].copy()
    avail["effective"] = avail["discounted_price_mxn"].fillna(avail["product_price_mxn"])
    avail["total_cost"] = (
        avail["effective"].fillna(0)
        + avail["delivery_fee_mxn"].fillna(0)
        + avail["service_fee_mxn"].fillna(0)
    )

    summary = avail.groupby(["platform", "product_id"]).agg(
        product_price=("effective", "mean"),
        delivery_fee=("delivery_fee_mxn", "mean"),
        service_fee=("service_fee_mxn", "mean"),
        total=("total_cost", "mean"),
    ).reset_index()

    products = list(PRODUCT_LABELS.keys())
    platforms = _platforms(df)

    fig, axes = plt.subplots(1, len(products), figsize=(14, 5.5), sharey=False)

    for idx, prod in enumerate(products):
        ax = axes[idx]
        prod_data = summary[summary["product_id"] == prod].set_index("platform").reindex(platforms)

        x = range(len(platforms))
        pp = prod_data["product_price"].fillna(0).values
        df_val = prod_data["delivery_fee"].fillna(0).values
        sf = prod_data["service_fee"].fillna(0).values

        ax.bar(x, pp, color=[COLORS[p] for p in platforms], label="Product")
        ax.bar(x, df_val, bottom=pp, color=[COLORS[p] for p in platforms],
               alpha=0.5, label="Delivery")
        ax.bar(x, sf, bottom=pp + df_val, color=[COLORS[p] for p in platforms],
               alpha=0.3, hatch="///", label="Service")

        for i in range(len(platforms)):
            total = pp[i] + df_val[i] + sf[i]
            ax.text(i, total + 1, f"${total:.0f}", ha="center", fontsize=10, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([LABELS[p].split()[0] for p in platforms], fontsize=9)
        ax.set_title(PRODUCT_LABELS[prod], fontsize=12)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%d"))

        if idx == 0:
            ax.set_ylabel("Total Cost to User (MXN)")

    # Shared legend
    handles = [
        mpatches.Patch(color="#888", alpha=1.0, label="Product Price"),
        mpatches.Patch(color="#888", alpha=0.5, label="Delivery Fee"),
        mpatches.Patch(color="#888", alpha=0.3, hatch="///", label="Service Fee"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=10,
              bbox_to_anchor=(0.5, -0.02))

    fig.suptitle("Insight #5: Total Checkout Cost — What Users Actually Pay",
                 fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    return fig


# ── Generate All ─────────────────────────────────────────────────

def generate_all_charts(df: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Generate all 5 charts and save to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    charts = [
        ("01_price_comparison.png", chart_price_comparison),
        ("02_zone_heatmap.png", chart_zone_heatmap),
        ("03_fee_structure.png", chart_fee_structure),
        ("04_delivery_time.png", chart_delivery_time),
        ("05_total_cost.png", chart_total_cost),
    ]

    for filename, func in charts:
        try:
            fig = func(df)
            path = output_dir / filename
            fig.savefig(path, bbox_inches="tight", dpi=150, facecolor="white")
            plt.close(fig)
            paths.append(path)
            print(f"  ✅ {filename}")
        except Exception as e:
            print(f"  ❌ {filename}: {e}")
            import traceback
            traceback.print_exc()

    return paths


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from settings import settings
    from synthetic_data import generate_synthetic_data

    print("Generating synthetic data...")
    data = generate_synthetic_data()
    df = pd.DataFrame(data)
    print(f"  {len(df)} data points\n")

    print("Generating charts...")
    out = settings.reports_dir / "charts"
    paths = generate_all_charts(df, out)

    print(f"\n✅ {len(paths)} charts saved to {out}")
    for p in paths:
        print(f"  → {p}")
