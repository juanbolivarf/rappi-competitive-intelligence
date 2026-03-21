# Approach & Methodology

## Scope Decisions

### Why Cloudflare Browser Rendering?

The traditional approach to competitive scraping involves managing local browser instances 
with Puppeteer/Playwright, dealing with anti-bot detection, and maintaining brittle CSS 
selectors that break when platforms update their UI.

Our approach uses **Cloudflare Browser Rendering**, specifically the `/json` endpoint which 
leverages AI (Llama 3.3 70B) to extract structured data from any page layout. This provides:

1. **Resilience**: No CSS selectors to maintain — the AI understands page structure semantically
2. **Scalability**: Headless browsers run on Cloudflare's edge network, not local machines
3. **Reproducibility**: Simple REST API calls, easy for any evaluator to run
4. **Cost-effective**: Free tier available, no need for proxy services
5. **Ethical**: Self-identifies as bot, respects robots.txt

### Why 25 Addresses?

We selected 25 addresses stratified across 5 zone types (5 each):
- The case suggests 20-50 addresses
- 25 gives us **statistical representation** while staying within practical limits
- 5 per zone type allows us to detect **geographic pricing patterns**
- All addresses are in the Guadalajara Metropolitan Area (ZMG)

### Why McDonald's as Primary Benchmark?

- **Universal availability**: Present on all 3 platforms in virtually every zone
- **Standardized menu**: A Big Mac is identical regardless of location
- **Industry standard**: Most used benchmark in competitive food delivery intelligence
- **Price range**: Covers both individual items ($75-$140 MXN) and combos ($120-$200 MXN)

### Why 3 Platforms (Not More)?

The case requires a minimum of 2 competitors + Rappi. We chose:
- **Rappi**: Baseline (what we're measuring against)
- **Uber Eats**: Largest global competitor in Mexico (#1 or #2 by GMV)
- **DiDi Food**: China-backed competitor with aggressive pricing in Mexico

These three represent the competitive core in Guadalajara. Additional platforms 
(Cornershop, PedidosYa) would add marginal value vs. the time cost.

## Architecture Decisions

### AI-Powered Extraction vs. CSS Selectors

| Approach | Pros | Cons |
|----------|------|------|
| CSS Selectors | Precise, deterministic | Brittle, per-platform maintenance |
| AI Extraction (/json) | Resilient, cross-platform | Slightly less deterministic, AI cost |

We chose AI extraction because:
1. All three platforms are React SPAs with different DOM structures
2. Platform UI changes would break selectors but not AI extraction
3. The same schema works across all platforms — write once, extract everywhere

### Rate Limiting Strategy

- **3-second minimum** between requests (configurable)
- Sequential processing per platform (not parallel across platforms)
- This yields ~20 requests per minute, well within ethical scraping norms
- Total scrape time estimate: ~25 addresses × 3 platforms × 3 seconds ≈ 4 minutes

### Error Handling Philosophy

Every failed scrape still produces a data point — marked with `scrape_success: false` 
and an `error_message`. This means:
- Analysis can report on **coverage** (what % of data was collected)
- Missing data is explicit, not silently dropped
- Evaluators can see exactly where and why scraping failed
