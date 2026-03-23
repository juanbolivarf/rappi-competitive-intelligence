"""
Uber Eats SSR Scraper - Extract data from JSON-LD (NO Cloudflare needed!)

Uber Eats embeds full menu data in schema.org JSON-LD format:
- Restaurant info (name, rating, cuisine)
- Full menu with sections
- All product prices

Benefits:
- FREE: No API costs
- FAST: ~500ms per request
- RELIABLE: Structured schema.org data
"""

import json
import logging
import asyncio
import re
from typing import Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

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


@dataclass
class UberEatsSSRResult:
    """Parsed result from Uber Eats JSON-LD data."""
    restaurant_name: str = ""
    restaurant_available: bool = False
    rating: float | None = None
    review_count: int | None = None
    price_range: str = ""
    cuisines: list[str] = field(default_factory=list)
    delivery_fee_mxn: float | None = None
    estimated_minutes_min: int | None = None
    estimated_minutes_max: int | None = None
    products: list[dict] = field(default_factory=list)
    promotions: list[str] = field(default_factory=list)


class UberEatsSSRScraper:
    """
    Uber Eats scraper using JSON-LD extraction (no Cloudflare needed).

    Extracts data from schema.org Restaurant/Menu JSON-LD embedded in HTML.
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        # Note: Removed Accept-Encoding to avoid brotli issues with async client
    }

    # Pre-discovered McDonald's store IDs by market
    STORE_IDS = {
        "guadalajara": [
            {"slug": "mcdonalds-centro", "id": "pVf6cMIlRtCP2DC0iy7t4w", "lat": 20.6737, "lng": -103.3474},
            {"slug": "mcdonalds-plaza-independencia", "id": "HqLRowiBS5KMBfE48ygXgg", "lat": 20.7014, "lng": -103.3211},
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
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @property
    def platform_name(self) -> str:
        return "ubereats"

    def build_url(self, address: Address, restaurant: str = "McDonald's") -> str:
        """Construct Uber Eats URL using nearest store."""
        stores = self.STORE_IDS.get(address.metro_area, self.STORE_IDS["guadalajara"])

        # Find nearest McDonald's
        nearest = min(
            stores,
            key=lambda s: (s["lat"] - address.lat) ** 2 + (s["lng"] - address.lng) ** 2,
        )

        return f"https://www.ubereats.com/mx-en/store/{nearest['slug']}/{nearest['id']}"

    async def fetch_page(self, url: str) -> str:
        """Fetch the HTML page."""
        response = await self._client.get(url)
        response.raise_for_status()
        return response.text

    def extract_json_ld(self, html: str) -> list[dict]:
        """Extract all JSON-LD blocks from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        blocks = []

        # Try both methods to find JSON-LD scripts
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        logger.debug(f"Found {len(scripts)} JSON-LD script tags")

        for script in scripts:
            content = script.string or script.get_text()
            if content:
                try:
                    data = json.loads(content)
                    blocks.append(data)
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON decode error: {e}")

        # Fallback: regex search for JSON-LD
        if not blocks:
            import re
            pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            logger.debug(f"Regex found {len(matches)} JSON-LD blocks")
            for match in matches:
                try:
                    data = json.loads(match.strip())
                    blocks.append(data)
                except json.JSONDecodeError:
                    pass

        return blocks

    def parse_json_ld(self, json_ld_blocks: list[dict]) -> UberEatsSSRResult:
        """Parse JSON-LD Restaurant schema to extract menu data."""
        result = UberEatsSSRResult()

        logger.debug(f"Parsing {len(json_ld_blocks)} JSON-LD blocks")

        for block in json_ld_blocks:
            block_type = block.get("@type")
            logger.debug(f"Block type: {block_type}")
            if block_type != "Restaurant":
                continue

            result.restaurant_available = True
            logger.debug("Found Restaurant block!")
            result.restaurant_name = block.get("name", "")
            result.price_range = block.get("priceRange", "")

            # Cuisines
            cuisines = block.get("servesCuisine", [])
            if isinstance(cuisines, list):
                result.cuisines = cuisines
            elif isinstance(cuisines, str):
                result.cuisines = [cuisines]

            # Rating
            rating_data = block.get("aggregateRating", {})
            if rating_data:
                try:
                    result.rating = float(rating_data.get("ratingValue", 0))
                    result.review_count = int(rating_data.get("reviewCount", 0))
                except (ValueError, TypeError):
                    pass

            # Menu items
            menu = block.get("hasMenu", {})
            if isinstance(menu, dict):
                sections = menu.get("hasMenuSection", [])
                if isinstance(sections, list):
                    for section in sections:
                        section_name = section.get("name", "")
                        items = section.get("hasMenuItem", [])
                        if isinstance(items, list):
                            for item in items:
                                product = self._parse_menu_item(item, section_name)
                                if product:
                                    result.products.append(product)

            logger.info(
                f"[ubereats-ssr] Extracted {len(result.products)} products from {result.restaurant_name}"
            )
            break  # Only process first Restaurant block

        return result

    def _parse_menu_item(self, item: dict, section: str) -> dict | None:
        """Parse a single menu item from JSON-LD."""
        name = item.get("name", "")
        if not name:
            return None

        # Extract price from offers
        offers = item.get("offers", {})
        price = None
        if isinstance(offers, dict):
            price_str = offers.get("price", "")
            if price_str:
                try:
                    # Handle formats like "160.00" or "$160.00"
                    price = float(re.sub(r"[^\d.]", "", str(price_str)))
                except ValueError:
                    pass

        # Check for discounts in name (e.g., "Big Mac + Papas 30% OFF")
        discount_text = None
        if "%" in name and ("OFF" in name.upper() or "DESCUENTO" in name.upper()):
            discount_match = re.search(r"(\d+)%\s*(?:OFF|DESCUENTO)", name, re.IGNORECASE)
            if discount_match:
                discount_text = f"{discount_match.group(1)}% OFF"

        return {
            "name": name,
            "description": item.get("description", ""),
            "price_mxn": price,
            "category": section,
            "discount_text": discount_text,
            "available": True,
        }

    async def scrape_address(
        self,
        address: Address,
        products: list[Product],
    ) -> list[ScrapedDataPoint]:
        """Scrape a single address using JSON-LD extraction."""
        url = self.build_url(address)
        logger.info(f"[ubereats-ssr] Scraping {address.name} -> {url[:60]}...")

        try:
            html = await self.fetch_page(url)
            json_ld_blocks = self.extract_json_ld(html)
            ssr_result = self.parse_json_ld(json_ld_blocks)

            data_points = []
            for product in products:
                matched = self._match_product(product, ssr_result.products)

                if matched:
                    dp = ScrapedDataPoint(
                        platform=self.platform_name,
                        address_id=address.id,
                        address_name=address.name,
                        zone_type=address.zone_type,
                        metro_area=address.metro_area,
                        product_id=product.id,
                        product_name=product.name,
                        product_price_mxn=matched.get("price_mxn"),
                        delivery_fee_mxn=ssr_result.delivery_fee_mxn,
                        estimated_minutes_min=ssr_result.estimated_minutes_min,
                        estimated_minutes_max=ssr_result.estimated_minutes_max,
                        restaurant_available=ssr_result.restaurant_available,
                        product_available=True,
                        discount_text=matched.get("discount_text"),
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
                        restaurant_available=ssr_result.restaurant_available,
                        product_available=False,
                        url_scraped=url,
                        error_message="Product not found in menu",
                    )

                dp.compute_total()
                data_points.append(dp)

            success_count = sum(1 for dp in data_points if dp.product_available)
            logger.info(f"[ubereats-ssr] {address.name}: {success_count}/{len(data_points)} products")

            return data_points

        except Exception as e:
            logger.error(f"[ubereats-ssr] {address.name}: Error - {e}")
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
        delay_seconds: float = 1.0,
    ) -> list[ScrapedDataPoint]:
        """Scrape all addresses with optional delay."""
        all_results = []

        logger.info(f"[ubereats-ssr] Starting: {len(addresses)} addresses x {len(products)} products")

        for i, address in enumerate(addresses, 1):
            results = await self.scrape_address(address, products)
            all_results.extend(results)

            if i < len(addresses) and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        successes = sum(1 for r in all_results if r.scrape_success and r.product_available)
        logger.info(f"[ubereats-ssr] Complete: {successes}/{len(all_results)} data points")

        return all_results


# Test
async def test_ubereats_ssr():
    """Test the Uber Eats SSR scraper."""
    test_products = [
        Product(id="bigmac", name="Big Mac", search_terms=["big mac", "bigmac"]),
        Product(id="combo_mediano", name="McTrio", search_terms=["mctrio", "combo", "mccombo"]),
        Product(id="nuggets_10", name="McNuggets", search_terms=["nuggets", "mcnuggets"]),
        Product(id="coca_500", name="Coca-Cola", search_terms=["coca", "coca-cola", "refresco"]),
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
    print("UBER EATS SSR SCRAPER TEST (NO CLOUDFLARE!)")
    print("=" * 60)

    async with UberEatsSSRScraper() as scraper:
        results = await scraper.scrape_address(test_address, test_products)

        print(f"\nResults for {test_address.name}:")
        print("-" * 40)

        for dp in results:
            status = "OK" if dp.product_available else "NOT FOUND"
            price = f"${dp.product_price_mxn}" if dp.product_price_mxn else "N/A"
            discount = f" ({dp.discount_text})" if dp.discount_text else ""
            print(f"  [{status}] {dp.product_name}: {price}{discount}")

        print("-" * 40)
        print(f"Restaurant: {results[0].restaurant_available if results else 'N/A'}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(test_ubereats_ssr())
