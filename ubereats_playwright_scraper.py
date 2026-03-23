"""
Uber Eats Playwright Scraper - Full data extraction with browser rendering.

Uses Playwright to get dynamic data that isn't in the static JSON-LD:
- Delivery fee (location-based)
- Service fee
- Estimated delivery time (ETA)

No login required - Uber Eats pages are public.

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import json
import logging
import re
from typing import Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class Address:
    """A delivery address for scraping."""
    id: str
    name: str
    zone_type: str
    metro_area: str
    lat: float
    lng: float


@dataclass
class Product:
    """A product to search for."""
    id: str
    name: str
    search_terms: list[str] = field(default_factory=list)


@dataclass
class ScrapedDataPoint:
    """A single scraped data point."""
    platform: str
    address_id: str
    address_name: str
    zone_type: str
    metro_area: str
    product_id: str
    product_name: str
    product_price_mxn: float | None = None
    discounted_price_mxn: float | None = None
    delivery_fee_mxn: float | None = None
    service_fee_mxn: float | None = None
    total_price_mxn: float | None = None
    estimated_minutes_min: int | None = None
    estimated_minutes_max: int | None = None
    restaurant_available: bool = False
    product_available: bool = False
    discount_text: str | None = None
    platform_promotions: list[str] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scrape_success: bool = True
    error_message: str | None = None
    url_scraped: str | None = None

    def compute_total(self):
        if self.product_price_mxn is not None:
            effective_price = self.discounted_price_mxn or self.product_price_mxn
            fees = (self.delivery_fee_mxn or 0) + (self.service_fee_mxn or 0)
            self.total_price_mxn = round(effective_price + fees, 2)

    def to_dict(self) -> dict:
        return asdict(self)


class UberEatsPlaywrightScraper:
    """
    Uber Eats scraper using Playwright for full data extraction.

    Gets delivery fees and ETA that aren't available in static JSON-LD.
    """

    # McDonald's store IDs by market
    STORE_IDS = {
        "guadalajara": [
            {"slug": "mcdonalds-centro", "id": "pVf6cMIlRtCP2DC0iy7t4w", "lat": 20.6737, "lng": -103.3474},
            {"slug": "mcdonalds-plaza-midtown", "id": "KwUtfEVXQA6HYy9xbMphvA", "lat": 20.6806, "lng": -103.3906},
        ],
        "monterrey": [
            {"slug": "mcdonalds-garza-sada", "id": "922nSYLsT1-ERjpi9jnvgw", "lat": 25.6516, "lng": -100.2895},
        ],
        "cdmx": [
            {"slug": "mcdonalds-aeropuerto", "id": "ansFddgoSGilvVgV7sGxoA", "lat": 19.4240, "lng": -99.0844},
            {"slug": "mcdonalds-centro", "id": "pVf6cMIlRtCP2DC0iy7t4w", "lat": 19.4326, "lng": -99.1332},
        ],
    }

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    @property
    def platform_name(self) -> str:
        return "ubereats"

    def build_url(self, address: Address) -> str:
        """Construct Uber Eats URL using nearest store."""
        stores = self.STORE_IDS.get(address.metro_area, self.STORE_IDS["guadalajara"])
        nearest = min(
            stores,
            key=lambda s: (s["lat"] - address.lat) ** 2 + (s["lng"] - address.lng) ** 2,
        )
        return f"https://www.ubereats.com/mx-en/store/{nearest['slug']}/{nearest['id']}"

    async def _ensure_browser(self):
        """Initialize Playwright browser."""
        if self._browser:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")

        self._playwright = await async_playwright().__aenter__()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            locale="es-MX",
            geolocation={"latitude": 20.6737, "longitude": -103.3474},
            permissions=["geolocation"],
        )
        self._page = await self._context.new_page()
        logger.info("[ubereats-pw] Browser initialized")

    async def close(self):
        """Close browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self):
        await self._ensure_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def extract_page_data(self, url: str) -> dict:
        """Navigate to page and extract all data."""
        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for content to load
        await asyncio.sleep(3)

        # Extract data using JavaScript
        data = await self._page.evaluate("""
            () => {
                const result = {
                    products: [],
                    delivery_fee: null,
                    service_fee: null,
                    eta_min: null,
                    eta_max: null,
                    restaurant_name: null,
                };

                // Get restaurant name
                const h1 = document.querySelector('h1');
                if (h1) result.restaurant_name = h1.textContent.trim();

                // Look for delivery fee - usually in a span with $ and "delivery"
                const allText = document.body.innerText;

                // Find delivery fee pattern like "$29 Delivery Fee" or "Delivery Fee $29"
                const deliveryMatch = allText.match(/(?:delivery fee|fee de entrega)[:\\s]*\\$?([\\d.]+)|\\$([\\d.]+)\\s*(?:delivery|entrega)/i);
                if (deliveryMatch) {
                    result.delivery_fee = parseFloat(deliveryMatch[1] || deliveryMatch[2]);
                }

                // Look for "Free Delivery" or "$0 delivery"
                if (/free delivery|entrega gratis|\\$0\\s*delivery/i.test(allText)) {
                    result.delivery_fee = 0;
                }

                // Find ETA pattern like "25-35 min", "25 – 35 min", "25–35 min"
                const etaPatterns = [
                    /(\\d+)\\s*[-–—]\\s*(\\d+)\\s*min/i,
                    /(\\d+)\\s*a\\s*(\\d+)\\s*min/i,
                    /(\\d+)\\s*to\\s*(\\d+)\\s*min/i,
                ];
                for (const pattern of etaPatterns) {
                    const etaMatch = allText.match(pattern);
                    if (etaMatch) {
                        result.eta_min = parseInt(etaMatch[1]);
                        result.eta_max = parseInt(etaMatch[2]);
                        break;
                    }
                }

                // If no range found, look for single number like "30 min"
                if (!result.eta_min) {
                    const singleMatch = allText.match(/(\\d+)\\s*min(?:utos?)?/i);
                    if (singleMatch) {
                        const mins = parseInt(singleMatch[1]);
                        if (mins > 5 && mins < 120) {  // Reasonable delivery time
                            result.eta_min = mins;
                            result.eta_max = mins + 10;
                        }
                    }
                }

                // Extract products from JSON-LD if available
                const jsonLd = document.querySelector('script[type="application/ld+json"]');
                if (jsonLd) {
                    try {
                        const data = JSON.parse(jsonLd.textContent);
                        if (data['@type'] === 'Restaurant' && data.hasMenu) {
                            const sections = data.hasMenu.hasMenuSection || [];
                            sections.forEach(section => {
                                const items = section.hasMenuItem || [];
                                items.forEach(item => {
                                    const offers = item.offers || {};
                                    const price = offers.price ? parseFloat(offers.price) : null;
                                    result.products.push({
                                        name: item.name || '',
                                        price: price,
                                        category: section.name || '',
                                    });
                                });
                            });
                        }
                    } catch (e) {}
                }

                return result;
            }
        """)

        logger.info(
            f"[ubereats-pw] Extracted {len(data.get('products', []))} products, "
            f"delivery=${data.get('delivery_fee')}, ETA={data.get('eta_min')}-{data.get('eta_max')}"
        )

        return data

    async def scrape_address(
        self,
        address: Address,
        products: list[Product],
    ) -> list[ScrapedDataPoint]:
        """Scrape a single address using Playwright."""
        url = self.build_url(address)
        logger.info(f"[ubereats-pw] Scraping {address.name} -> {url[:60]}...")

        try:
            page_data = await self.extract_page_data(url)

            data_points = []
            for product in products:
                matched = self._match_product(product, page_data.get("products", []))

                if matched:
                    # Check for discount in name
                    discount_text = None
                    name = matched.get("name", "")
                    if "%" in name and "OFF" in name.upper():
                        pct_match = re.search(r"(\d+)%", name)
                        if pct_match:
                            discount_text = f"{pct_match.group(1)}% OFF"

                    dp = ScrapedDataPoint(
                        platform=self.platform_name,
                        address_id=address.id,
                        address_name=address.name,
                        zone_type=address.zone_type,
                        metro_area=address.metro_area,
                        product_id=product.id,
                        product_name=product.name,
                        product_price_mxn=matched.get("price"),
                        delivery_fee_mxn=page_data.get("delivery_fee"),
                        service_fee_mxn=page_data.get("service_fee"),
                        estimated_minutes_min=page_data.get("eta_min"),
                        estimated_minutes_max=page_data.get("eta_max"),
                        restaurant_available=True,
                        product_available=True,
                        discount_text=discount_text,
                        url_scraped=url,
                    )
                else:
                    dp = ScrapedDataPoint(
                        platform=self.platform_name,
                        address_id=address.id,
                        address_name=address.name,
                        zone_type=address.zone_type,
                        metro_area=address.metro_area,
                        product_id=product.id,
                        product_name=product.name,
                        delivery_fee_mxn=page_data.get("delivery_fee"),
                        estimated_minutes_min=page_data.get("eta_min"),
                        estimated_minutes_max=page_data.get("eta_max"),
                        restaurant_available=True,
                        product_available=False,
                        url_scraped=url,
                        error_message="Product not found in menu",
                    )

                dp.compute_total()
                data_points.append(dp)

            success = sum(1 for d in data_points if d.product_available)
            logger.info(f"[ubereats-pw] {address.name}: {success}/{len(data_points)} products")
            return data_points

        except Exception as e:
            logger.error(f"[ubereats-pw] {address.name}: Error - {e}")
            return [
                ScrapedDataPoint(
                    platform=self.platform_name,
                    address_id=address.id,
                    address_name=address.name,
                    zone_type=address.zone_type,
                    metro_area=address.metro_area,
                    product_id=p.id,
                    product_name=p.name,
                    scrape_success=False,
                    error_message=str(e),
                    url_scraped=url,
                )
                for p in products
            ]

    def _match_product(self, product: Product, extracted: list[dict]) -> dict | None:
        """Fuzzy match reference product to extracted products."""
        for ext in extracted:
            ext_name = (ext.get("name") or "").lower()
            for term in product.search_terms:
                if term.lower() in ext_name:
                    return ext
        return None

    async def scrape_all(
        self,
        addresses: list[Address],
        products: list[Product],
        delay_seconds: float = 2.0,
    ) -> list[ScrapedDataPoint]:
        """Scrape all addresses."""
        all_results = []

        logger.info(f"[ubereats-pw] Starting: {len(addresses)} addresses x {len(products)} products")

        for i, address in enumerate(addresses, 1):
            logger.info(f"[ubereats-pw] Progress: {i}/{len(addresses)}")
            results = await self.scrape_address(address, products)
            all_results.extend(results)

            if i < len(addresses) and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        successes = sum(1 for r in all_results if r.scrape_success and r.product_available)
        logger.info(f"[ubereats-pw] Complete: {successes}/{len(all_results)} data points")

        return all_results


async def test_scraper():
    """Test the Uber Eats Playwright scraper."""
    test_products = [
        Product(id="bigmac", name="Big Mac", search_terms=["big mac", "bigmac"]),
        Product(id="mcnuggets", name="McNuggets", search_terms=["nuggets", "mcnuggets"]),
        Product(id="mctrio", name="McTrio", search_terms=["mctrio", "combo"]),
    ]

    test_address = Address(
        id="test_gdl",
        name="Guadalajara Centro",
        zone_type="commercial",
        metro_area="guadalajara",
        lat=20.6737,
        lng=-103.3474,
    )

    print("\n" + "=" * 60)
    print("UBER EATS PLAYWRIGHT SCRAPER TEST")
    print("=" * 60)

    async with UberEatsPlaywrightScraper() as scraper:
        results = await scraper.scrape_address(test_address, test_products)

        print(f"\nResults for {test_address.name}:")
        print("-" * 40)

        for dp in results:
            status = "OK" if dp.product_available else "NOT FOUND"
            price = f"${dp.product_price_mxn}" if dp.product_price_mxn else "N/A"
            print(f"  [{status}] {dp.product_name}: {price}")

        if results:
            print("-" * 40)
            print(f"Delivery Fee: ${results[0].delivery_fee_mxn}")
            print(f"ETA: {results[0].estimated_minutes_min}-{results[0].estimated_minutes_max} min")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(test_scraper())
