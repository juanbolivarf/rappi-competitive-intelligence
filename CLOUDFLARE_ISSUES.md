# Cloudflare Browser Rendering - Known Issues

## Overview

Cloudflare Browser Rendering was initially chosen as the scraping backend for this project. While it works for some use cases, we encountered several issues that led us to implement SSR (Server-Side Rendering) extraction as the primary method.

**Current Recommendation**: Use SSR mode (default) for Rappi and Uber Eats. Use test data mode for DiDi Food.

---

## Issue #1: Free Tier Neuron Limit (CRITICAL)

### Problem
Cloudflare's free tier has a **daily limit of 10,000 neurons** for AI-powered extraction. Once exceeded, all requests fail with HTTP 422 errors until the next day.

### Error Message
```
HTTP 422 from Cloudflare: {"success":false,"errors":[{"message":"AI error: AiError: 4006:
you have used up your daily free allocation of 10,000 neurons, please upgrade to
Cloudflare's Workers Paid plan if you would like to continue using AI features"}]}
```

### Impact
- A single page extraction can consume 500-2000 neurons
- With 15 addresses × 3 platforms = 45 pages = **~45,000 neurons minimum**
- **Free tier is exhausted after ~5-10 scrapes per day**

### Solution Required
- Upgrade to Cloudflare Workers Paid plan ($5/month + usage)
- Or use SSR extraction (FREE, no limits)

---

## Issue #2: Rate Limiting (429 Errors)

### Problem
Cloudflare imposes strict rate limits on Browser Rendering API calls. When scraping multiple addresses/products, we frequently hit `429 Too Many Requests` errors.

### Symptoms
```
Error: Request rate limited (429)
Cloudflare Browser Rendering: Rate limit exceeded
```

### Attempted Mitigations
- Increased `SCRAPE_DELAY_SECONDS` to 8+ seconds
- Reduced batch sizes
- Implemented exponential backoff

### Result
Partially effective. Still hits limits on full scrapes (15+ addresses).

---

## Issue #2: Timeout Errors

### Problem
Some pages take longer than the API timeout to fully render, especially pages with heavy JavaScript or lazy-loaded content.

### Symptoms
```
Error: Request timed out after 60000ms
Page load timeout exceeded
```

### Attempted Mitigations
- Increased `REQUEST_TIMEOUT` to 60+ seconds
- Added wait-for-selector logic

### Result
Inconsistent. Some pages still timeout even with extended limits.

---

## Issue #3: Bot Detection

### Problem
Delivery platforms implement bot detection that identifies Cloudflare's headless browser fingerprint.

### Symptoms
- Empty responses
- Captcha challenges
- Redirects to error pages
- Missing data in otherwise successful responses

### Platforms Affected
- **DiDi Food**: Most aggressive detection
- **Uber Eats**: Occasional detection
- **Rappi**: Least detection

### Result
Cannot reliably bypass. Requires more sophisticated fingerprint randomization.

---

## Issue #4: DiDi Food Login Wall

### Problem
DiDi Food requires user authentication to view menu prices, delivery fees, and ETAs. This is not a technical limitation of Cloudflare but a platform design choice.

### Symptoms
- Restaurant listings visible but no prices
- "Sign in to see prices" messages
- Empty cart/checkout data

### Attempted Mitigations
- Tried session cookies (expired quickly)
- Tried OAuth token injection (blocked)
- Investigated mobile app API (requires root device)

### Result
Not possible without valid user session. See `DIDI_FOOD_INVESTIGATION.md` for full investigation.

---

## Issue #5: Cost

### Problem
Cloudflare Browser Rendering consumes API credits. For competitive intelligence requiring frequent scrapes, costs add up.

### Calculation
- ~$0.01-0.02 per page render
- 15 addresses × 4 products × 3 platforms = 180 renders
- Full scrape = ~$2-4
- Daily monitoring = ~$60-120/month

### Result
SSR extraction is free and works for Rappi and Uber Eats.

---

## Issue #6: JavaScript Rendering Inconsistencies

### Problem
Dynamic content doesn't always render completely. Prices, fees, or ETAs sometimes missing even on successful page loads.

### Symptoms
- `product_price_mxn: null` on otherwise successful scrapes
- Partial data extraction
- Inconsistent results between runs

### Cause
- Lazy loading not triggered
- Intersection observers not fired
- API calls not completed before snapshot

### Result
SSR extraction gets data directly from HTML/JSON, avoiding rendering issues.

---

## Comparison: Cloudflare vs SSR

| Aspect | Cloudflare | SSR |
|--------|------------|-----|
| Cost | ~$0.01/page | FREE |
| Speed | 5-15 sec/page | 1-2 sec/page |
| Reliability | ~70-80% | ~90-95% |
| Rate Limits | Strict | Lenient |
| DiDi Food | Blocked | Blocked |
| Bot Detection | Sometimes detected | Rarely detected |
| JavaScript | Full render | Not needed |

---

## When to Use Cloudflare

Despite the issues, Cloudflare may still be useful for:

1. **Fallback**: If SSR extraction breaks due to HTML structure changes
2. **Screenshots**: Capturing visual evidence of competitor pages
3. **Complex SPAs**: Sites that require full JavaScript execution
4. **One-off scrapes**: When cost isn't a concern

---

## Configuration for Cloudflare Mode

If you need to use Cloudflare mode, configure `.env`:

```env
CF_ACCOUNT_ID=your_account_id
CF_API_TOKEN=your_api_token

# Recommended settings for stability
SCRAPE_DELAY_SECONDS=8
REQUEST_TIMEOUT=60
```

Run with:
```bash
python main.py --use-cloudflare --addresses 3
```

---

---

## Alternative Scraping Approaches

Given the limitations of Cloudflare's free tier, here are alternative approaches for future development:

### 1. AI Agent-Based Scraping

Use an AI agent (like Claude or GPT-4) with computer use capabilities to navigate websites like a human user.

**Pros:**
- Can handle dynamic content and JavaScript
- Adapts to UI changes automatically
- Can solve CAPTCHAs with human-like interaction
- No rate limits from scraping APIs

**Cons:**
- Higher latency (agent thinks before each action)
- More expensive per page ($0.05-0.20 per page)
- Requires careful prompt engineering

**Implementation:**
```python
# Example with Claude Computer Use
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=[{"type": "computer_20241022", "display_width": 1024, "display_height": 768}],
    messages=[{
        "role": "user",
        "content": "Go to rappi.com.mx, search for McDonald's near Providencia, "
                   "and extract the Big Mac price and delivery fee."
    }]
)
```

### 2. Browserless.io or Similar Services

Cloud browser services with better rate limits and pricing.

**Options:**
- Browserless.io (~$0.01/page)
- ScrapingBee (~$0.001/page)
- Bright Data (~$0.002/page)

### 3. Playwright with Residential Proxies

Run your own Playwright browser with rotating residential IPs to avoid detection.

**Pros:**
- Full control over browser behavior
- No neuron/API limits
- One-time proxy cost

**Cons:**
- Requires proxy subscription (~$15-50/month)
- More infrastructure to maintain

### 4. Official APIs (Where Available)

Some platforms offer partner/affiliate APIs:
- **Rappi**: Partner API (requires business relationship)
- **Uber Eats**: Affiliate API (limited data)
- **DiDi Food**: No public API

### 5. Hybrid Approach (Recommended)

Combine multiple methods for resilience:
1. **Primary**: SSR extraction (FREE) for Rappi + Uber Eats
2. **Fallback**: Playwright with proxy for failed extractions
3. **DiDi Food**: AI agent or manual collection
4. **Testing**: Synthetic data for development

---

## Conclusion

SSR extraction is the recommended approach for this project:
- **Rappi**: SSR works well, extracts all data
- **Uber Eats**: SSR + Playwright for full data
- **DiDi Food**: Use synthetic test data (login wall blocks all automated methods)

Cloudflare Browser Rendering is **not recommended** for production use due to:
1. Free tier neuron limit (10,000/day) exhausted quickly
2. Paid tier adds ongoing costs
3. SSR extraction is faster and free

For future scaling, consider AI agent-based scraping or a hybrid approach with residential proxies.
