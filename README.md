# 🔍 Rappi Competitive Intelligence System

**Automated competitive intelligence platform for Rappi — collecting, analyzing, and visualizing pricing and delivery data across delivery platforms in Mexico.**

> Built for the Rappi AI Engineer technical case.

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                        │
│  Rappi (baseline)  ·  Uber Eats  ·  DiDi Food                 │
│  ↓ Cloudflare Browser Rendering API (/scrape + /json)          │
├─────────────────────────────────────────────────────────────────┤
│                    ORCHESTRATION LAYER                          │
│  Python orchestrator with rate limiting, retry logic,           │
│  address rotation, structured logging, error handling           │
├─────────────────────────────────────────────────────────────────┤
│                    PROCESSING LAYER                             │
│  Data normalization → Statistical analysis → CSV/JSON export    │
├─────────────────────────────────────────────────────────────────┤
│                    INSIGHTS LAYER                               │
│  Top 5 actionable insights (Finding → Impact → Recommendation) │
│  3+ visualizations: price comparison, zone heatmap, fee charts  │
├─────────────────────────────────────────────────────────────────┤
│                    DELIVERY LAYER                               │
│  Executive PDF Report · Streamlit Dashboard · GitHub Repo       │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Cloudflare account with Browser Rendering enabled ([free tier works](https://developers.cloudflare.com/browser-rendering/))
- Cloudflare API Token with `Browser Rendering - Edit` permission

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/[your-username]/rappi-competitive-intelligence.git
cd rappi-competitive-intelligence

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your Cloudflare credentials
```

### Configuration

Edit `.env` with your credentials:

```env
CF_ACCOUNT_ID=your_cloudflare_account_id
CF_API_TOKEN=your_cloudflare_api_token
```

### Running the Scraper

```bash
# Run full scraping pipeline (Rappi + Uber Eats, real-time SSR)
python main.py

# Use synthetic test data (includes all 3 platforms)
python main.py --test-data

# Run for a specific platform only
python main.py --platform rappi
python main.py --platform ubereats

# Run with a subset of addresses (for testing)
python main.py --addresses 5

# Filter by metro area
python main.py --metro-area gdl

# Dry run (validate config without scraping)
python main.py --dry-run
```

### Data Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Real-time SSR** | `python main.py` | Live scraping from Rappi & Uber Eats (FREE) |
| **Test Data** | `python main.py --test-data` | Synthetic data for all 3 platforms |
| **Cloudflare** | `python main.py --use-cloudflare` | Legacy mode using Cloudflare API |

**Notes**:
- DiDi Food is only available in test data mode. See [DIDI_FOOD_INVESTIGATION.md](DIDI_FOOD_INVESTIGATION.md) for details.
- Cloudflare mode has known issues. See [CLOUDFLARE_ISSUES.md](CLOUDFLARE_ISSUES.md) for details.

### Generating the Report

```bash
# Generate analysis and visualizations
python -m analysis.pipeline

# Launch interactive dashboard (bonus)
streamlit run dashboard.py
```

### Deploying to Streamlit Community Cloud

Use `dashboard.py` as the app entrypoint. The dependency ranges in
`requirements.txt` are intentionally broad enough for Streamlit Community Cloud
to resolve package wheels compatible with its current Python runtime, which
avoids source builds for older packages such as `pillow`.

To enable live scraping from the deployed dashboard, add `CF_ACCOUNT_ID` and
`CF_API_TOKEN` to your Streamlit app secrets. Without those secrets, the
dashboard will fall back to synthetic demo data unless a saved scrape already
exists under `data/raw/`.

For Cloudflare Browser Rendering, conservative defaults are recommended in
Streamlit Cloud to reduce `429` rate-limit errors:

```toml
SCRAPE_DELAY_SECONDS = "8"
REQUEST_TIMEOUT = "60"
```

## 📁 Project Structure

```
rappi-competitive-intelligence/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
│
├── config/
│   ├── __init__.py
│   ├── settings.py              # Global settings & env loading
│   ├── addresses.py             # Geographic addresses with zone classification
│   └── products.py              # Reference products for comparison
│
├── scraper/
│   ├── __init__.py
│   ├── main.py                  # CLI entry point & orchestrator
│   ├── cloudflare_client.py     # Cloudflare Browser Rendering API wrapper
│   ├── base_scraper.py          # Abstract scraper with retry/rate-limit logic
│   ├── rappi_scraper.py         # Rappi-specific extraction logic
│   ├── ubereats_scraper.py      # Uber Eats-specific extraction logic
│   ├── didifood_scraper.py      # DiDi Food-specific extraction logic
│   └── schemas.py               # JSON schemas for /json endpoint extraction
│
├── analysis/
│   ├── __init__.py
│   ├── pipeline.py              # Full analysis pipeline
│   ├── normalization.py         # Data cleaning & standardization
│   ├── comparisons.py           # Cross-platform statistical comparisons
│   ├── insights.py              # Insight generation engine
│   ├── visualizations.py        # Chart generation (matplotlib/plotly)
│   └── dashboard.py             # Streamlit interactive dashboard (bonus)
│
├── reports/
│   └── (generated PDF/HTML reports go here)
│
├── data/
│   ├── raw/                     # Raw scraped data (CSV/JSON per run)
│   └── processed/               # Cleaned, normalized datasets
│
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py          # Basic scraper tests
│   └── test_analysis.py         # Analysis pipeline tests
│
├── docs/
│   ├── APPROACH.md              # Scope decisions & methodology
│   ├── ETHICAL_CONSIDERATIONS.md # Scraping ethics & legal notes
│   └── LIMITATIONS.md           # Known blockers & limitations
│
└── assets/
    └── (screenshots, evidence captures)
```

## 🎯 Scope Definition

### Platforms (3)
| Platform | Role | Data Source | Status |
|----------|------|-------------|--------|
| **Rappi** | Baseline (own data) | SSR extraction | Live |
| **Uber Eats** | Competitor #1 | SSR + Playwright | Live |
| **DiDi Food** | Competitor #2 | Synthetic data | Test only |

### Geographic Coverage (25 addresses across Guadalajara metro)
Addresses are selected to represent diverse economic zones:
- **High income**: Providencia, Puerta de Hierro, Colinas de San Javier
- **Mid income**: Chapultepec, Centro Histórico, Ciudad del Sol
- **Low income / periférica**: Tonalá centro, Tlaquepaque, Miravalle
- **Commercial**: Andares, Plaza del Sol area, Av. Vallarta corridor
- **University**: ITESO area, UDG CUCEI area

### Reference Products (3 fast food + 1 retail)
| Product | Category | Why |
|---------|----------|-----|
| Big Mac (individual) | Fast food | Universal benchmark |
| Combo mediano McDonald's | Fast food | Tests bundled pricing |
| Coca-Cola 500ml | Retail/convenience | Tests retail vertical |

### Metrics Collected
- ✅ Product price (MXN)
- ✅ Delivery fee (before discounts)
- ✅ Service fee / platform commission
- ✅ Estimated delivery time (minutes)
- ✅ Active discounts / promotions
- ✅ Final total price (what user actually pays)

## ⚖️ Ethical Considerations

- All data scraped is **publicly visible** to any user of these platforms
- Rate limiting implemented: **minimum 3-second delay** between requests
- `robots.txt` respected where applicable
- Cloudflare Browser Rendering [self-identifies as a bot](https://developers.cloudflare.com/browser-rendering/rest-api/scrape-endpoint/) and honors site rules
- No authentication bypass or login-wall circumvention
- No personal data collected — only public pricing/availability info
- This exercise is for **recruitment purposes only**; production implementation should involve Legal review

## ⚠️ Known Limitations

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for full details.

- Delivery platforms serve **dynamic content** based on time, demand, and user profile — data represents a snapshot
- Some platforms may block or throttle automated access
- Prices may vary within the same zone based on surge pricing
- Cloudflare Browser Rendering does **not bypass CAPTCHAs** or bot protection
- **DiDi Food**: Login wall + SSL pinning prevent automated scraping. See [DIDI_FOOD_INVESTIGATION.md](DIDI_FOOD_INVESTIGATION.md) for our full investigation and technical blockers
- Pre-scraped backup data included in `data/raw/backup/` for presentation reliability

## 📊 Sample Output

After running the scraper, you'll find:

```
data/raw/scrape_2025-10-10_14-30.json    # Raw scraped data
data/processed/comparison_matrix.csv      # Normalized comparison
reports/competitive_report.pdf            # Executive PDF
```

## 🛠️ Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Scraping | Cloudflare Browser Rendering | Edge-rendered headless Chrome, /json for AI-powered extraction |
| Orchestration | Python 3.11 + asyncio | Async for parallel scraping, clean abstractions |
| Analysis | pandas + numpy | Industry standard for data manipulation |
| Visualization | matplotlib + plotly | Static charts for PDF, interactive for dashboard |
| Dashboard | Streamlit | Rapid interactive prototype |
| Report | matplotlib + reportlab | Programmatic PDF generation |

## 👤 Author

**Juan Bolívar** — Systems Engineering · AI-first Operator
- Currently: Partnerships Analyst @ Pluria
- Focus: AI-powered operational systems, B2B commercial execution, fintech in LATAM

---

*Built with systems thinking, pragmatism, and a product mindset.*
