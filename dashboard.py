"""
Rappi Competitive Intelligence — Interactive Dashboard

Bonus deliverable: an interactive Streamlit dashboard that lets
Strategy and Pricing teams explore the competitive data.

Usage:
    streamlit run analysis/dashboard.py

Features:
- KPI cards with platform comparison
- Interactive charts with Plotly (hover, zoom, filter)
- Zone-level drill-down
- Product-level comparison
- Raw data explorer
"""

from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from synthetic_data import generate_synthetic_data

# ── Page Config ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Rappi CI Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Colors & Constants ────────────────────────────────────────────

COLORS = {
    "rappi": "#FF6B35",
    "ubereats": "#142328",
    "didifood": "#F5A623",
}
LABELS = {"rappi": "Rappi", "ubereats": "Uber Eats", "didifood": "DiDi Food"}
ZONE_LABELS = {
    "high_income": "🏠 High Income",
    "mid_income": "🏘️ Mid Income",
    "commercial": "🏬 Commercial",
    "university": "🎓 University",
    "low_income": "📍 Periférica",
}
PRODUCT_LABELS = {
    "bigmac": "Big Mac",
    "combo_mediano": "Combo Mediano",
    "nuggets_10": "Nuggets 10pc",
    "coca_500": "Coca-Cola 500ml",
}


# ── Data Loading ──────────────────────────────────────────────────

@st.cache_data
def load_data():
    """Load or generate data."""
    raw = generate_synthetic_data()
    df = pd.DataFrame(raw)
    df["effective_price"] = df["discounted_price_mxn"].fillna(df["product_price_mxn"])
    df["total_cost"] = (
        df["effective_price"].fillna(0)
        + df["delivery_fee_mxn"].fillna(0)
        + df["service_fee_mxn"].fillna(0)
    )
    df["avg_delivery_time"] = (
        df["estimated_minutes_min"] + df["estimated_minutes_max"]
    ) / 2
    df["platform_label"] = df["platform"].map(LABELS)
    df["zone_label"] = df["zone_type"].map(ZONE_LABELS)
    df["product_label"] = df["product_id"].map(PRODUCT_LABELS)
    return df


df = load_data()
df_avail = df[df["product_available"] == True].copy()


# ── Sidebar Filters ──────────────────────────────────────────────

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Rappi_logo.svg/512px-Rappi_logo.svg.png", width=120)
st.sidebar.title("Filters")

selected_zones = st.sidebar.multiselect(
    "Zone Types",
    options=list(ZONE_LABELS.keys()),
    default=list(ZONE_LABELS.keys()),
    format_func=lambda x: ZONE_LABELS[x],
)

selected_products = st.sidebar.multiselect(
    "Products",
    options=list(PRODUCT_LABELS.keys()),
    default=list(PRODUCT_LABELS.keys()),
    format_func=lambda x: PRODUCT_LABELS[x],
)

selected_platforms = st.sidebar.multiselect(
    "Platforms",
    options=list(LABELS.keys()),
    default=list(LABELS.keys()),
    format_func=lambda x: LABELS[x],
)

# Apply filters
mask = (
    df_avail["zone_type"].isin(selected_zones)
    & df_avail["product_id"].isin(selected_products)
    & df_avail["platform"].isin(selected_platforms)
)
filtered = df_avail[mask]

st.sidebar.markdown("---")
st.sidebar.caption(
    f"📊 {len(filtered):,} data points | "
    f"{len(selected_zones)} zones | "
    f"{len(selected_products)} products"
)


# ── Header ────────────────────────────────────────────────────────

st.title("🔍 Competitive Intelligence Dashboard")
st.markdown(
    "**Rappi vs Uber Eats vs DiDi Food** — "
    "Guadalajara Metropolitan Area · 25 locations · 4 reference products"
)


# ── KPI Cards ─────────────────────────────────────────────────────

st.markdown("### Key Metrics at a Glance")

kpi_cols = st.columns(len(selected_platforms))

for i, platform in enumerate(selected_platforms):
    pdata = filtered[filtered["platform"] == platform]
    with kpi_cols[i]:
        avg_price = pdata["effective_price"].mean()
        avg_fee = pdata["delivery_fee_mxn"].mean() + pdata["service_fee_mxn"].mean()
        avg_time = pdata["avg_delivery_time"].mean()
        avg_total = pdata["total_cost"].mean()
        avail = pdata["product_available"].mean() * 100

        color = COLORS[platform]
        st.markdown(
            f"""
            <div style="
                border-left: 4px solid {color};
                padding: 12px 16px;
                border-radius: 0 8px 8px 0;
                margin-bottom: 8px;
            ">
                <h3 style="margin:0; color: {color};">{LABELS[platform]}</h3>
                <table style="width:100%; font-size:14px; margin-top:8px;">
                    <tr><td>Avg Product Price</td><td style="text-align:right; font-weight:bold;">${avg_price:.0f} MXN</td></tr>
                    <tr><td>Avg Total Fees</td><td style="text-align:right; font-weight:bold;">${avg_fee:.0f} MXN</td></tr>
                    <tr><td>Avg Total Cost</td><td style="text-align:right; font-weight:bold;">${avg_total:.0f} MXN</td></tr>
                    <tr><td>Avg Delivery Time</td><td style="text-align:right; font-weight:bold;">{avg_time:.0f} min</td></tr>
                    <tr><td>Availability</td><td style="text-align:right; font-weight:bold;">{avail:.0f}%</td></tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")


# ── Chart 1: Price Comparison ─────────────────────────────────────

st.markdown("### 📊 Insight #1: Product Price Positioning")

fig1 = px.bar(
    filtered.groupby(["platform_label", "product_label"])["effective_price"]
    .mean().reset_index(),
    x="product_label",
    y="effective_price",
    color="platform_label",
    barmode="group",
    color_discrete_map={LABELS[k]: v for k, v in COLORS.items()},
    labels={"effective_price": "Avg Price (MXN)", "product_label": "Product", "platform_label": "Platform"},
    text_auto="$.0f",
)
fig1.update_layout(height=420, legend_title="Platform", yaxis_tickprefix="$")
fig1.update_traces(textposition="outside")
st.plotly_chart(fig1, use_container_width=True)


# ── Chart 2: Zone Heatmap ────────────────────────────────────────

st.markdown("### 🗺️ Insight #2: Rappi vs Competition by Zone")

col_a, col_b = st.columns([2, 1])

with col_a:
    rappi_data = filtered[filtered["platform"] == "rappi"]
    comp_data = filtered[filtered["platform"] != "rappi"]

    if not rappi_data.empty and not comp_data.empty:
        rappi_avg = rappi_data.groupby(["zone_type", "product_id"])["total_cost"].mean()
        comp_avg = comp_data.groupby(["zone_type", "product_id"])["total_cost"].mean()

        delta = ((rappi_avg - comp_avg) / comp_avg * 100).reset_index()
        delta.columns = ["zone_type", "product_id", "delta_pct"]
        delta["zone_label"] = delta["zone_type"].map(ZONE_LABELS)
        delta["product_label"] = delta["product_id"].map(PRODUCT_LABELS)

        pivot = delta.pivot(index="zone_label", columns="product_label", values="delta_pct")

        fig2 = px.imshow(
            pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            color_continuous_scale="RdYlGn_r",
            zmin=-15, zmax=15,
            text_auto="+.1f",
            labels={"color": "Rappi Premium (%)"},
            aspect="auto",
        )
        fig2.update_layout(height=380)
        fig2.update_traces(texttemplate="%{z:+.1f}%")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select Rappi + at least one competitor to see the heatmap.")

with col_b:
    st.markdown("""
    **How to read this chart:**
    - 🟢 **Green** = Rappi is **cheaper**
    - 🔴 **Red** = Rappi is **more expensive**
    - Values show % difference in total checkout cost
    
    **Key takeaway:**
    Rappi's competitiveness varies significantly by zone and product. 
    The Pricing team should focus on red cells — those are zones where 
    we're losing on total cost.
    """)


# ── Chart 3: Fee Structure ───────────────────────────────────────

st.markdown("### 💰 Insight #3: Fee Structure Deep Dive")

tab1, tab2 = st.tabs(["Overall Fees", "Fees by Zone"])

with tab1:
    fee_data = filtered.groupby("platform_label").agg(
        delivery=("delivery_fee_mxn", "mean"),
        service=("service_fee_mxn", "mean"),
    ).reset_index()

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        name="Delivery Fee",
        x=fee_data["platform_label"],
        y=fee_data["delivery"],
        marker_color=[COLORS.get(k, "#888") for k in selected_platforms],
        text=fee_data["delivery"].apply(lambda x: f"${x:.0f}"),
        textposition="inside",
    ))
    fig3.add_trace(go.Bar(
        name="Service Fee",
        x=fee_data["platform_label"],
        y=fee_data["service"],
        marker_color=[COLORS.get(k, "#888") for k in selected_platforms],
        marker_opacity=0.5,
        marker_pattern_shape="/",
        text=fee_data["service"].apply(lambda x: f"${x:.0f}"),
        textposition="inside",
    ))
    fig3.update_layout(barmode="stack", height=380, yaxis_tickprefix="$",
                       yaxis_title="Average Fee (MXN)")
    st.plotly_chart(fig3, use_container_width=True)

with tab2:
    zone_fees = filtered.groupby(["platform_label", "zone_label"])["delivery_fee_mxn"].mean().reset_index()
    fig3b = px.bar(
        zone_fees, x="zone_label", y="delivery_fee_mxn",
        color="platform_label", barmode="group",
        color_discrete_map={LABELS[k]: v for k, v in COLORS.items()},
        labels={"delivery_fee_mxn": "Avg Delivery Fee (MXN)", "zone_label": "Zone", "platform_label": "Platform"},
        text_auto="$.0f",
    )
    fig3b.update_layout(height=420, yaxis_tickprefix="$")
    fig3b.update_traces(textposition="outside")
    st.plotly_chart(fig3b, use_container_width=True)


# ── Chart 4: Delivery Time ───────────────────────────────────────

st.markdown("### ⏱️ Insight #4: Delivery Time Competitiveness")

time_data = filtered.groupby(["platform_label", "zone_label"])["avg_delivery_time"].mean().reset_index()
fig4 = px.bar(
    time_data, x="zone_label", y="avg_delivery_time",
    color="platform_label", barmode="group",
    color_discrete_map={LABELS[k]: v for k, v in COLORS.items()},
    labels={"avg_delivery_time": "Avg Time (min)", "zone_label": "Zone", "platform_label": "Platform"},
    text_auto=".0f",
)
fig4.update_layout(height=420)
fig4.update_traces(textposition="outside")
st.plotly_chart(fig4, use_container_width=True)


# ── Chart 5: Total Cost Breakdown ─────────────────────────────────

st.markdown("### 🧾 Insight #5: Total Checkout Cost — What Users Actually Pay")

product_selector = st.selectbox(
    "Select product to analyze:",
    options=list(PRODUCT_LABELS.keys()),
    format_func=lambda x: PRODUCT_LABELS[x],
    index=0,
)

prod_data = filtered[filtered["product_id"] == product_selector]
cost_breakdown = prod_data.groupby("platform_label").agg(
    product=("effective_price", "mean"),
    delivery=("delivery_fee_mxn", "mean"),
    service=("service_fee_mxn", "mean"),
    total=("total_cost", "mean"),
).reset_index()

fig5 = go.Figure()
for component, name, opacity in [
    ("product", "Product Price", 1.0),
    ("delivery", "Delivery Fee", 0.6),
    ("service", "Service Fee", 0.35),
]:
    fig5.add_trace(go.Bar(
        name=name,
        x=cost_breakdown["platform_label"],
        y=cost_breakdown[component],
        marker_opacity=opacity,
        marker_color=[COLORS.get(k, "#888") for k in selected_platforms],
        text=cost_breakdown[component].apply(lambda x: f"${x:.0f}"),
        textposition="inside",
    ))

# Add total labels on top
fig5.add_trace(go.Scatter(
    x=cost_breakdown["platform_label"],
    y=cost_breakdown["total"] + 3,
    text=cost_breakdown["total"].apply(lambda x: f"Total: ${x:.0f}"),
    mode="text",
    textfont=dict(size=14, color="black"),
    showlegend=False,
))

fig5.update_layout(
    barmode="stack", height=420,
    yaxis_tickprefix="$", yaxis_title="Cost (MXN)",
    title=f"Cost Breakdown: {PRODUCT_LABELS[product_selector]}",
)
st.plotly_chart(fig5, use_container_width=True)


# ── Promotions Analysis ──────────────────────────────────────────

st.markdown("---")
st.markdown("### 🏷️ Promotional Activity")

promo_cols = st.columns(len(selected_platforms))
for i, platform in enumerate(selected_platforms):
    pdata = filtered[filtered["platform"] == platform]
    promos = pdata[pdata["discount_text"].notna()]
    promo_rate = len(promos) / len(pdata) * 100 if len(pdata) > 0 else 0

    with promo_cols[i]:
        st.metric(
            label=f"{LABELS[platform]} Promo Rate",
            value=f"{promo_rate:.0f}%",
            delta=f"{len(promos)} active promotions",
        )
        if not promos.empty:
            top_promos = promos["discount_text"].value_counts().head(3)
            for promo, count in top_promos.items():
                st.caption(f"• {promo} ({count}x)")


# ── Raw Data Explorer ─────────────────────────────────────────────

st.markdown("---")

with st.expander("📋 Raw Data Explorer"):
    st.markdown(f"**{len(filtered):,}** data points after filtering")

    display_cols = [
        "platform_label", "address_name", "zone_label", "product_label",
        "product_price_mxn", "delivery_fee_mxn", "service_fee_mxn",
        "total_cost", "avg_delivery_time", "discount_text",
    ]
    st.dataframe(
        filtered[display_cols].rename(columns={
            "platform_label": "Platform",
            "address_name": "Address",
            "zone_label": "Zone",
            "product_label": "Product",
            "product_price_mxn": "Price (MXN)",
            "delivery_fee_mxn": "Delivery Fee",
            "service_fee_mxn": "Service Fee",
            "total_cost": "Total Cost",
            "avg_delivery_time": "ETA (min)",
            "discount_text": "Promotion",
        }),
        use_container_width=True,
        height=400,
    )

    csv = filtered[display_cols].to_csv(index=False)
    st.download_button(
        "📥 Download filtered data as CSV",
        csv,
        "rappi_ci_filtered.csv",
        "text/csv",
    )


# ── PDF Report Download ───────────────────────────────────────────

st.markdown("---")
st.markdown("### 📄 Executive Report")
st.markdown(
    "Generate a publication-ready PDF report with all 5 insights, "
    "charts, KPI tables, methodology, and recommendations."
)

report_col1, report_col2 = st.columns([1, 2])

with report_col1:
    generate_report = st.button("🔄 Generate PDF Report", type="primary", use_container_width=True)

with report_col2:
    if generate_report:
        with st.spinner("Building executive report (charts + analysis + PDF)..."):
            from report_generator import build_report_bytes
            pdf_bytes = build_report_bytes(df)

        st.success(f"Report ready — {len(pdf_bytes) / 1024:.0f} KB")
        st.download_button(
            label="📥 Download Executive PDF Report",
            data=pdf_bytes,
            file_name=f"Rappi_CI_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Click **Generate PDF Report** to create the downloadable report.")


# ── Footer ────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "Rappi Competitive Intelligence System · "
    "Built by Juan Bolívar · "
    "Data: 25 addresses × 3 platforms × 4 products = 300 data points · "
    "Powered by Cloudflare Browser Rendering + Python + Streamlit"
)
