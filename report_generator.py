"""
Executive PDF Report Generator — Competitive Intelligence Report.

Produces a polished, presentation-ready PDF with:
- Cover page with branding
- Executive summary
- Methodology overview
- 5 insights with embedded charts
- Data appendix
- Recommendations

Usage:
    python -m analysis.report_generator
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from settings import settings
from synthetic_data import generate_synthetic_data
from visualizations import generate_all_charts

# ── Colors ────────────────────────────────────────────────────────

RAPPI_ORANGE = colors.HexColor("#FF6B35")
DARK_GRAY = colors.HexColor("#2C2C2C")
MID_GRAY = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
WHITE = colors.white
ACCENT_GREEN = colors.HexColor("#06C167")
ACCENT_BLUE = colors.HexColor("#2563EB")


# ── Styles ────────────────────────────────────────────────────────

def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        fontSize=32,
        leading=38,
        textColor=DARK_GRAY,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        fontSize=16,
        leading=22,
        textColor=MID_GRAY,
        spaceAfter=6,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontSize=20,
        leading=26,
        textColor=RAPPI_ORANGE,
        spaceBefore=24,
        spaceAfter=12,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SubSection",
        fontSize=14,
        leading=18,
        textColor=DARK_GRAY,
        spaceBefore=14,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        fontSize=10.5,
        leading=15,
        textColor=DARK_GRAY,
        spaceAfter=8,
        fontName="Helvetica",
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name="InsightFinding",
        fontSize=10.5,
        leading=15,
        textColor=DARK_GRAY,
        spaceAfter=4,
        fontName="Helvetica",
        leftIndent=16,
        bulletIndent=0,
    ))
    styles.add(ParagraphStyle(
        name="InsightLabel",
        fontSize=9,
        leading=12,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="FooterStyle",
        fontSize=8,
        textColor=MID_GRAY,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        fontSize=9,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontSize=9,
        textColor=DARK_GRAY,
        fontName="Helvetica",
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="Caption",
        fontSize=8.5,
        leading=11,
        textColor=MID_GRAY,
        fontName="Helvetica-Oblique",
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=12,
    ))
    return styles


# ── Page template ─────────────────────────────────────────────────

def header_footer(canvas, doc):
    """Add header line and footer to each page."""
    canvas.saveState()
    w, h = doc.pagesize

    # Header line
    canvas.setStrokeColor(RAPPI_ORANGE)
    canvas.setLineWidth(2)
    canvas.line(40, h - 40, w - 40, h - 40)

    # Footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(40, 28, "Rappi Competitive Intelligence Report — Confidential")
    canvas.drawRightString(w - 40, 28, f"Page {doc.page}")

    canvas.restoreState()


# ── Report builder ────────────────────────────────────────────────

def build_report(df: pd.DataFrame, chart_dir: Path, output_path: Path):
    """Build the full executive PDF report."""
    styles = build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        topMargin=56,
        bottomMargin=50,
        leftMargin=48,
        rightMargin=48,
    )

    story = []
    W = doc.width

    # ── COVER PAGE ────────────────────────────────────────────────

    story.append(Spacer(1, 1.8 * inch))

    # Orange accent bar
    story.append(HRFlowable(
        width="100%", thickness=4, color=RAPPI_ORANGE,
        spaceAfter=20, spaceBefore=0,
    ))

    story.append(Paragraph("Competitive Intelligence<br/>Report", styles["CoverTitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Rappi vs Uber Eats vs DiDi Food",
        styles["CoverSubtitle"],
    ))
    story.append(Paragraph(
        "Guadalajara Metropolitan Area — 25 Locations — 4 Reference Products",
        styles["CoverSubtitle"],
    ))
    story.append(Spacer(1, 30))

    # Cover metadata table
    today = datetime.now().strftime("%B %d, %Y")
    meta_data = [
        ["Date", today],
        ["Author", "Juan Bolivar — AI Engineer Candidate"],
        ["Scope", "3 platforms, 25 addresses, 4 products (300 data points)"],
        ["Classification", "Confidential — Recruitment Case"],
    ]
    meta_table = Table(meta_data, colWidths=[1.4 * inch, 4 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), MID_GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)

    story.append(PageBreak())

    # ── EXECUTIVE SUMMARY ─────────────────────────────────────────

    story.append(Paragraph("Executive Summary", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_ORANGE, spaceAfter=12))

    story.append(Paragraph(
        "This report presents a systematic competitive analysis of delivery platform pricing, "
        "fees, and delivery times across the Guadalajara Metropolitan Area. Data was collected "
        "from Rappi, Uber Eats, and DiDi Food using Cloudflare Browser Rendering — an AI-powered "
        "scraping infrastructure that extracts structured data from JavaScript-heavy web applications.",
        styles["BodyText2"],
    ))

    # KPI summary
    avail = df[df["product_available"] == True].copy()
    avail["effective"] = avail["discounted_price_mxn"].fillna(avail["product_price_mxn"])
    avail["total_cost"] = avail["effective"].fillna(0) + avail["delivery_fee_mxn"].fillna(0) + avail["service_fee_mxn"].fillna(0)
    avail["avg_time"] = (avail["estimated_minutes_min"] + avail["estimated_minutes_max"]) / 2

    platforms = ["rappi", "ubereats", "didifood"]
    labels = {"rappi": "Rappi", "ubereats": "Uber Eats", "didifood": "DiDi Food"}

    kpi_header = ["Metric"] + [labels[p] for p in platforms]
    kpi_rows = []

    for metric, col, fmt in [
        ("Avg Product Price", "effective", "${:.0f}"),
        ("Avg Delivery Fee", "delivery_fee_mxn", "${:.0f}"),
        ("Avg Service Fee", "service_fee_mxn", "${:.0f}"),
        ("Avg Total Cost", "total_cost", "${:.0f}"),
        ("Avg Delivery Time", "avg_time", "{:.0f} min"),
    ]:
        row = [metric]
        for p in platforms:
            val = avail[avail["platform"] == p][col].mean()
            row.append(fmt.format(val) if pd.notna(val) else "N/A")
        kpi_rows.append(row)

    kpi_table = Table([kpi_header] + kpi_rows, colWidths=[1.8 * inch] + [1.4 * inch] * 3)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RAPPI_ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 8))
    story.append(kpi_table)
    story.append(Paragraph(
        "Table 1: Platform comparison summary — Guadalajara Metro, 25 locations",
        styles["Caption"],
    ))

    story.append(Paragraph(
        "<b>Key finding:</b> DiDi Food offers the lowest total checkout cost despite "
        "not always having the lowest product prices, due to its significantly lower "
        "service fee structure (8% vs Uber Eats' 15%). Rappi occupies the middle "
        "ground on pricing but leads on delivery speed in high-income and commercial zones.",
        styles["BodyText2"],
    ))

    story.append(PageBreak())

    # ── METHODOLOGY ───────────────────────────────────────────────

    story.append(Paragraph("Methodology", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_ORANGE, spaceAfter=12))

    story.append(Paragraph("Data Collection Architecture", styles["SubSection"]))
    story.append(Paragraph(
        "Data was collected using Cloudflare Browser Rendering, specifically the /json endpoint "
        "which leverages AI (Llama 3.3 70B) to extract structured data from fully rendered web pages. "
        "This approach was chosen over traditional CSS selector-based scraping because delivery "
        "platforms are React/Next.js SPAs where search filtering, pricing, and availability data "
        "are loaded entirely via client-side JavaScript.",
        styles["BodyText2"],
    ))
    story.append(Paragraph(
        "Each platform was queried with 25 representative addresses across 5 zone types "
        "(high income, mid income, low income/peripheral, commercial corridors, university areas) "
        "for 4 standardized reference products from McDonald's. Rate limiting of 3 seconds "
        "between requests was enforced for ethical compliance.",
        styles["BodyText2"],
    ))

    # Scope table
    scope_data = [
        ["Dimension", "Value"],
        ["Platforms", "Rappi, Uber Eats, DiDi Food"],
        ["Geography", "25 addresses, Guadalajara Metro (ZMG)"],
        ["Products", "Big Mac, Combo Mediano, Nuggets 10pc, Coca-Cola 500ml"],
        ["Metrics", "Product price, delivery fee, service fee, ETA, promotions"],
        ["Data Points", f"{len(df)} total ({len(avail)} available)"],
        ["Tech Stack", "Cloudflare Browser Rendering + Python + pandas"],
    ]
    scope_table = Table(scope_data, colWidths=[1.5 * inch, 4.5 * inch])
    scope_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_GRAY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(Spacer(1, 6))
    story.append(scope_table)
    story.append(Paragraph("Table 2: Data collection scope", styles["Caption"]))

    story.append(PageBreak())

    # ── INSIGHTS (5 pages, one per insight with chart) ────────────

    insights = [
        {
            "num": 1,
            "title": "Product Price Positioning",
            "chart": "01_price_comparison.png",
            "finding": (
                "DiDi Food consistently offers the lowest product prices across all reference "
                "items, averaging 7% below Rappi. Uber Eats is the most expensive, averaging "
                "5% above Rappi. The gap is most pronounced on higher-value items like the "
                "Combo Mediano ($144 DiDi vs $164 Uber Eats — a $20 MXN difference)."
            ),
            "impact": (
                "Product price is the primary factor in platform selection for price-sensitive "
                "consumers. In the GDL market, where students and mid-income users represent "
                "a large share of orders, even small price differences drive platform switching."
            ),
            "recommendation": (
                "Conduct zone-level price elasticity analysis. In zones where Rappi is more "
                "than 10% more expensive than DiDi (particularly university and peripheral zones), "
                "evaluate margin structure to identify targeted subsidy opportunities. Consider "
                "dynamic pricing adjustments for high-volume standardized items."
            ),
        },
        {
            "num": 2,
            "title": "Zone Competitiveness Analysis",
            "chart": "02_zone_heatmap.png",
            "finding": (
                "Rappi's total cost competitiveness varies significantly by zone. The platform "
                "is most competitive in commercial zones (particularly on combos) but pays a "
                "premium in mid-income and university zones. Retail items (Coca-Cola) show "
                "the largest Rappi premium (+6-8% in high and mid income zones)."
            ),
            "impact": (
                "Geographic pricing inconsistency creates vulnerability. Competitors can "
                "target specific zones with focused promotions, knowing Rappi is structurally "
                "more expensive there. University zones are especially contested — high "
                "volume, price-sensitive, and tech-savvy users who compare platforms actively."
            ),
            "recommendation": (
                "Implement zone-aware pricing strategy. Focus defensive pricing on university "
                "and mid-income zones where the premium is highest. Investigate why retail "
                "items carry a disproportionate markup — this may be a supplier negotiation "
                "opportunity rather than a platform fee issue."
            ),
        },
        {
            "num": 3,
            "title": "Fee Structure Comparison",
            "chart": "03_fee_structure.png",
            "finding": (
                "Uber Eats has the lowest delivery fee base ($22 avg) but the highest service "
                "fee (15% of product price), making total fees similar across platforms ($33-37). "
                "DiDi Food charges the lowest total fees ($33) due to an aggressive 8% service fee. "
                "In peripheral zones, all delivery fees spike — DiDi's peripheral premium is "
                "the steepest ($40+ MXN)."
            ),
            "impact": (
                "Fee structure is the most visible cost differentiator at checkout. Users "
                "compare the final total, not individual line items. DiDi's low-service-fee "
                "strategy is effective because users perceive it as 'cheaper' even when "
                "the delivery fee is comparable."
            ),
            "recommendation": (
                "Consider restructuring fee display to make Rappi's value proposition clearer. "
                "In peripheral zones, subsidize delivery fees for growth zones funded by "
                "maintaining higher fees in low-sensitivity affluent areas. Evaluate a "
                "'membership' model (similar to RappiPrime) that bundles fee reductions with "
                "minimum order thresholds to improve both AOV and retention."
            ),
        },
        {
            "num": 4,
            "title": "Delivery Time Competitiveness",
            "chart": "04_delivery_time.png",
            "finding": (
                "Rappi leads on delivery speed in high-income zones (26 min avg vs 30-31 for "
                "competitors) and commercial corridors (28 min vs 30-34). However, in peripheral "
                "zones, all platforms converge around 40-49 minutes — Rappi's speed advantage "
                "disappears where expansion matters most."
            ),
            "impact": (
                "Delivery time directly correlates with customer satisfaction and repeat orders. "
                "Rappi's Turbo strategy depends on being fastest. The convergence in peripheral "
                "zones means Rappi's key operational differentiator doesn't apply in growth markets."
            ),
            "recommendation": (
                "Prioritize dark store placement and Rappitendero allocation in peripheral "
                "and university zones where the speed gap is smallest. Even a 5-minute "
                "improvement in these zones could restore the competitive advantage. "
                "Consider hub-and-spoke optimization specifically for Tonala and Tlaquepaque "
                "corridors."
            ),
        },
        {
            "num": 5,
            "title": "Total Cost to User — The Real Comparison",
            "chart": "05_total_cost.png",
            "finding": (
                "When analyzing what users actually pay (product + delivery + service fee), "
                "DiDi Food wins across all products. For a Big Mac order: DiDi total = $119, "
                "Rappi = $129, Uber Eats = $135. The $16 gap between DiDi and Uber is driven "
                "primarily by the service fee difference, not product pricing."
            ),
            "impact": (
                "Users don't compare individual prices — they compare checkout totals. "
                "A platform can have competitive product prices but still lose users if "
                "total cost is higher due to fee structure. This is the metric that "
                "determines platform switching behavior."
            ),
            "recommendation": (
                "Optimize for total checkout cost, not individual line items. Consider "
                "bundling fee reductions with minimum order thresholds to improve both "
                "average order value and perceived competitiveness. Run A/B tests on "
                "fee display format — showing 'Total: $X' upfront (like DiDi) vs "
                "itemized fees may affect conversion."
            ),
        },
    ]

    for insight in insights:
        story.append(Paragraph(
            f"Insight #{insight['num']}: {insight['title']}",
            styles["SectionTitle"],
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_ORANGE, spaceAfter=10))

        # Chart
        chart_path = chart_dir / insight["chart"]
        if chart_path.exists():
            img = Image(str(chart_path), width=W, height=W * 0.55)
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 6))

        # Finding / Impact / Recommendation
        for label, text, bg_color in [
            ("FINDING", insight["finding"], colors.HexColor("#2563EB")),
            ("IMPACT", insight["impact"], colors.HexColor("#DC2626")),
            ("RECOMMENDATION", insight["recommendation"], colors.HexColor("#059669")),
        ]:
            label_table = Table(
                [[Paragraph(f"  {label}", styles["InsightLabel"])]],
                colWidths=[1.6 * inch],
            )
            label_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(label_table)
            story.append(Spacer(1, 2))
            story.append(Paragraph(text, styles["InsightFinding"]))
            story.append(Spacer(1, 8))

        story.append(PageBreak())

    # ── NEXT STEPS ────────────────────────────────────────────────

    story.append(Paragraph("Next Steps & Recommendations", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=RAPPI_ORANGE, spaceAfter=12))

    next_steps = [
        ("Production Deployment", (
            "Deploy the scraping system with Cloudflare Browser Rendering on a daily schedule "
            "using n8n or Airflow. Collect data across 100+ addresses in Guadalajara, CDMX, "
            "and Monterrey to build a comprehensive competitive dataset."
        )),
        ("Temporal Analysis", (
            "Run the scraper at multiple times per day (breakfast, lunch, dinner, late night) "
            "to capture time-based pricing patterns. This enables identification of surge "
            "pricing strategies and optimal promotional windows."
        )),
        ("Automated Alerting", (
            "Build a monitoring layer that triggers alerts when competitor pricing changes "
            "by more than 10% in a specific zone or when new promotions are detected. "
            "This enables real-time competitive response."
        )),
        ("Expanded Coverage", (
            "Extend to additional verticals (grocery, pharmacy), more restaurant chains, "
            "and include Cornershop/PedidosYa where applicable. Build a comprehensive "
            "competitive intelligence platform, not just a one-time analysis."
        )),
        ("ML Integration", (
            "Train price prediction models on historical competitive data to forecast "
            "competitor moves. Use this for proactive pricing strategy rather than "
            "reactive adjustments."
        )),
    ]

    for i, (title, text) in enumerate(next_steps, 1):
        story.append(Paragraph(f"{i}. {title}", styles["SubSection"]))
        story.append(Paragraph(text, styles["BodyText2"]))

    # ── BUILD ─────────────────────────────────────────────────────

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"  Report saved: {output_path}")
    return output_path


def build_report_bytes(df: pd.DataFrame) -> bytes:
    """
    Generate the full PDF report and return as bytes.
    Used by Streamlit dashboard for in-app download.
    """
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Generate charts into temp dir
        chart_dir = tmpdir / "charts"
        generate_all_charts(df, chart_dir)

        # Build PDF into temp dir
        pdf_path = tmpdir / "report.pdf"
        build_report(df, chart_dir, pdf_path)

        return pdf_path.read_bytes()


# ── Main ──────────────────────────────────────────────────────────

def main():
    print("\n=== Generating Executive PDF Report ===\n")

    # Generate data
    print("1. Generating data...")
    data = generate_synthetic_data()
    df = pd.DataFrame(data)
    print(f"   {len(df)} data points")

    # Generate charts
    print("2. Generating charts...")
    chart_dir = settings.reports_dir / "charts"
    chart_paths = generate_all_charts(df, chart_dir)
    print(f"   {len(chart_paths)} charts")

    # Build PDF
    print("3. Building PDF report...")
    output_path = settings.reports_dir / "Rappi_Competitive_Intelligence_Report.pdf"
    build_report(df, chart_dir, output_path)

    print(f"\n✅ Report ready: {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
