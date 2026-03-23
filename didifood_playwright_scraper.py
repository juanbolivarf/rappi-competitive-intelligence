"""
DiDi Food Playwright Scraper - Uses saved browser session to bypass login wall.

DiDi Food requires authentication. This scraper uses Playwright with a saved
browser session to scrape data after you've logged in once.

Setup (one-time):
    1. Run: python didifood_playwright_scraper.py --login
    2. Log in manually in the browser that opens
    3. Close the browser when done - session is saved automatically

Usage (after login):
    python didifood_playwright_scraper.py                    # Test scrape
    python main.py --platform didifood --use-playwright      # Full pipeline

Session expires after ~30 days. Re-run --login to refresh.

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Session storage path
SESSION_DIR = Path(__file__).parent / ".didi_session"
SESSION_FILE = SESSION_DIR / "session.json"


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


class DiDiFoodPlaywrightScraper:
    """
    DiDi Food scraper using Playwright with saved authentication.

    Requires one-time manual login to save session cookies.
    """

    # McDonald's store IDs by market
    STORE_IDS = {
        "guadalajara": "5764607602869405740",
        "monterrey": "5764607602869405740",  # Update with real ID
        "cdmx": "5764607602869405740",  # Update with real ID
    }

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None

    @property
    def platform_name(self) -> str:
        return "didifood"

    def build_url(self, address: Address) -> str:
        """Construct DiDi Food McDonald's URL."""
        store_id = self.STORE_IDS.get(address.metro_area, self.STORE_IDS["guadalajara"])
        return (
            f"https://www.didi-food.com/es-MX/food/store/{store_id}/McDonalds/"
            f"?lat={address.lat}&lng={address.lng}"
        )

    async def login_and_save_session(self):
        """
        Open browser for manual login and save session.

        Run this once to authenticate, then use saved session for scraping.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False

        print("\n" + "=" * 60)
        print("DIDI FOOD LOGIN")
        print("=" * 60)
        print("\n1. A browser will open")
        print("2. Log in to DiDi Food manually")
        print("3. Navigate to any restaurant page to confirm login works")
        print("4. Close the browser when done")
        print("\nSession will be saved automatically.\n")

        SESSION_DIR.mkdir(exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()

            page = await context.new_page()
            await page.goto("https://www.didi-food.com/es-MX")

            print("Waiting for you to log in and close the browser...")
            print("(The browser will stay open until you close it)")

            # Wait for browser to be closed by user
            try:
                while True:
                    await asyncio.sleep(1)
                    # Check if page is still valid
                    try:
                        await page.title()
                    except:
                        break
            except:
                pass

            # Save cookies/storage state
            storage = await context.storage_state()
            SESSION_FILE.write_text(json.dumps(storage, indent=2))
            print(f"\nSession saved to: {SESSION_FILE}")

            await browser.close()

        return True

    async def _ensure_browser(self):
        """Initialize browser with saved session."""
        if self._browser:
            return

        if not SESSION_FILE.exists():
            raise RuntimeError(
                "No saved session found. Run: python didifood_playwright_scraper.py --login"
            )

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")

        self._playwright = await async_playwright().__aenter__()
        self._browser = await self._playwright.chromium.launch(headless=True)

        # Load saved session
        storage_state = json.loads(SESSION_FILE.read_text())
        self._context = await self._browser.new_context(storage_state=storage_state)
        self._page = await self._context.new_page()

        logger.info("[didifood] Browser initialized with saved session")

    async def close(self):
        """Close browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.__aexit__(None, None, None)

    async def __aenter__(self):
        await self._ensure_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def extract_page_data(self, url: str) -> dict:
        """Navigate to page and extract menu data."""
        await self._page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for menu to load
        await asyncio.sleep(2)

        # Check if we hit login wall
        current_url = self._page.url
        if "login" in current_url.lower() or "signin" in current_url.lower():
            raise RuntimeError("Session expired. Re-run: python didifood_playwright_scraper.py --login")

        # Extract data from page
        data = await self._page.evaluate("""
            () => {
                const products = [];

                // Try to find product cards
                const productCards = document.querySelectorAll('[data-testid*="product"], [class*="product"], [class*="menu-item"]');

                productCards.forEach(card => {
                    const nameEl = card.querySelector('[class*="name"], h3, h4, [class*="title"]');
                    const priceEl = card.querySelector('[class*="price"]');

                    if (nameEl) {
                        const priceText = priceEl ? priceEl.textContent : '';
                        const priceMatch = priceText.match(/\\$?([\\d,]+(?:\\.\\d{2})?)/);

                        products.push({
                            name: nameEl.textContent.trim(),
                            price: priceMatch ? parseFloat(priceMatch[1].replace(',', '')) : null,
                        });
                    }
                });

                // Try to get delivery info
                const deliveryEl = document.querySelector('[class*="delivery"], [class*="fee"]');
                const etaEl = document.querySelector('[class*="eta"], [class*="time"], [class*="minutes"]');

                return {
                    products: products,
                    delivery_fee: deliveryEl ? deliveryEl.textContent : null,
                    eta: etaEl ? etaEl.textContent : null,
                    page_title: document.title,
                    url: window.location.href,
                };
            }
        """)

        return data

    async def scrape_address(
        self,
        address: Address,
        products: list[Product],
    ) -> list[ScrapedDataPoint]:
        """Scrape a single address."""
        url = self.build_url(address)
        logger.info(f"[didifood] Scraping {address.name} -> {url[:60]}...")

        try:
            page_data = await self.extract_page_data(url)
            logger.info(f"[didifood] Extracted {len(page_data.get('products', []))} products")

            data_points = []
            for product in products:
                matched = self._match_product(product, page_data.get("products", []))

                if matched:
                    dp = ScrapedDataPoint(
                        platform=self.platform_name,
                        address_id=address.id,
                        address_name=address.name,
                        zone_type=address.zone_type,
                        metro_area=address.metro_area,
                        product_id=product.id,
                        product_name=product.name,
                        product_price_mxn=matched.get("price"),
                        restaurant_available=True,
                        product_available=True,
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
                        restaurant_available=True,
                        product_available=False,
                        url_scraped=url,
                        error_message="Product not found in menu",
                    )

                dp.compute_total()
                data_points.append(dp)

            return data_points

        except Exception as e:
            logger.error(f"[didifood] {address.name}: Error - {e}")
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

        logger.info(f"[didifood] Starting: {len(addresses)} addresses x {len(products)} products")

        for i, address in enumerate(addresses, 1):
            logger.info(f"[didifood] Progress: {i}/{len(addresses)}")
            results = await self.scrape_address(address, products)
            all_results.extend(results)

            if i < len(addresses) and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        successes = sum(1 for r in all_results if r.scrape_success and r.product_available)
        logger.info(f"[didifood] Complete: {successes}/{len(all_results)} data points")

        return all_results


async def test_scraper():
    """Test the DiDi Food scraper."""
    test_products = [
        Product(id="bigmac", name="Big Mac", search_terms=["big mac", "bigmac"]),
        Product(id="mcnuggets", name="McNuggets", search_terms=["nuggets", "mcnuggets"]),
    ]

    test_address = Address(
        id="test_gdl",
        name="Guadalajara Test",
        zone_type="commercial",
        metro_area="guadalajara",
        lat=20.6737,
        lng=-103.3474,
    )

    print("\n" + "=" * 60)
    print("DIDI FOOD PLAYWRIGHT SCRAPER TEST")
    print("=" * 60)

    try:
        async with DiDiFoodPlaywrightScraper() as scraper:
            results = await scraper.scrape_address(test_address, test_products)

            print(f"\nResults for {test_address.name}:")
            print("-" * 40)

            for dp in results:
                status = "OK" if dp.product_available else "NOT FOUND"
                price = f"${dp.product_price_mxn}" if dp.product_price_mxn else "N/A"
                print(f"  [{status}] {dp.product_name}: {price}")

    except RuntimeError as e:
        print(f"\nError: {e}")
        print("\nTo fix: Run with --login flag first")


async def main_login():
    """Run login flow."""
    scraper = DiDiFoodPlaywrightScraper()
    await scraper.login_and_save_session()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    if "--login" in sys.argv:
        asyncio.run(main_login())
    else:
        asyncio.run(test_scraper())
