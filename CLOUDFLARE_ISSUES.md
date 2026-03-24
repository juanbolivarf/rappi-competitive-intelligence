# Cloudflare Browser Rendering - Known Issues

## Overview

Cloudflare Browser Rendering was initially chosen as the scraping backend for this project. While it works for some use cases, we encountered several issues that led us to implement SSR (Server-Side Rendering) extraction as the primary method.

**Current Recommendation**: Use SSR mode (default) for Rappi and Uber Eats. Use test data mode for DiDi Food.

---

## Issue #1: Rate Limiting (429 Errors)

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

## Conclusion

SSR extraction is the recommended approach for this project:
- **Rappi**: SSR works well, extracts all data
- **Uber Eats**: SSR + Playwright for full data
- **DiDi Food**: Use synthetic test data (login wall blocks all automated methods)

Cloudflare Browser Rendering remains available as a fallback but is not the primary scraping method.
