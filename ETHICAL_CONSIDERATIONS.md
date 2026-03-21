# Ethical Considerations

## Legal Framework

### Public Data Principle
All data collected by this system is **publicly visible** to any user who visits these 
platforms. We are not:
- Bypassing authentication or login walls
- Accessing private APIs or internal endpoints
- Collecting personal user data
- Scraping content behind paywalls

### robots.txt Compliance
Cloudflare Browser Rendering honors `robots.txt` directives by default. Our `/scrape` 
and `/json` calls target specific pages (not site-wide crawling), which is the equivalent 
of a user visiting a page.

### Terms of Service
While scraping publicly accessible data is generally legal for competitive analysis, 
platform Terms of Service may restrict automated access.

> **Recommendation**: Before deploying any competitive scraping system in production, 
> consult with Rappi's Legal team to ensure compliance with applicable laws and 
> competitor ToS in each operating country.

## Technical Safeguards

- **Rate limiting**: Minimum 3-second delay between requests
- **Sequential processing**: Never parallel-bombing a single platform
- **Bot identification**: Cloudflare Browser Rendering self-identifies as a bot
- **Minimal footprint**: Only specific data points needed, no mass crawling
- **No PII**: Zero personal data collection

## Production Recommendations

1. **Legal Review**: Have Legal approve the scraping approach per jurisdiction
2. **API Partnerships**: Negotiate data-sharing agreements where possible
3. **Internal Baseline**: Use Rappi's own APIs for baseline data
4. **Scheduled Runs**: Daily at off-peak hours, not continuous
5. **Third-Party Providers**: Consider licensed CI providers for regulated collection
