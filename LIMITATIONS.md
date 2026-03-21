# Known Limitations

## Data Collection

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Dynamic pricing** | Data is a snapshot, prices vary by time/demand | Run at consistent times; for production, multiple daily runs |
| **Bot detection** | Some requests may be blocked | Real Chrome via CF, rate limiting, backup data for demos |
| **Location sensitivity** | Small lat/lng changes affect results | Fixed representative addresses per zone |
| **AI extraction accuracy** | Not 100% deterministic | Fuzzy matching, price range validation, sample verification |

## Analysis

- **Sample size**: 300 max data points — directional, not statistically significant
- **Single city**: Guadalajara only; dynamics differ in CDMX, Monterrey
- **Single vertical**: Fast food focus; grocery/pharmacy pricing may differ
- **No temporal baseline**: Single point-in-time, no trend analysis

## Technical

- Cloudflare free tier has usage limits
- Cannot bypass CAPTCHAs or Turnstile
- Response times vary (5-30s per request)
- Results may differ between runs due to A/B testing and real-time conditions

## What We'd Improve With More Time

1. Temporal analysis across 7+ days (time-of-day, day-of-week variation)
2. Geographic expansion to CDMX and Monterrey
3. More products and verticals (retail, pharmacy)
4. Automated scheduling via cron + n8n
5. Full interactive Streamlit dashboard
6. Alert system for significant competitor pricing changes
7. ML-based price prediction from historical data
