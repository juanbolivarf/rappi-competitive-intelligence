"""
DiDi Food scraper — Competitor #2.

Strategy:
- DiDi Food web: https://food.didi.com/mx
- Location-based search with lat/lng
- Same AI extraction pattern as other platforms
"""

from typing import Any

from config.addresses import Address
from config.products import Product
from scraper.base_scraper import BaseScraper, ScrapedDataPoint
from scraper.cloudflare_client import CloudflareClient
from scraper.schemas import (
    build_restaurant_prompt,
    RESTAURANT_DATA_SCHEMA,
)


class DiDiFoodScraper(BaseScraper):

    @property
    def platform_name(self) -> str:
        return "didifood"

    def build_url(self, address: Address, restaurant: str = "McDonald's") -> str:
        """
        Construct DiDi Food URL.

        ⚠️ KNOWN LIMITATION (from live testing):
        DiDi Food has a HARD LOGIN WALL — every page redirects to login.
        Unlike Rappi (public SSR) and Uber Eats (public mx-en subdomain),
        DiDi Food requires authentication for ALL content.

        For the case: DiDi data collected via manual spot-checks.
        The scraper architecture supports DiDi once session cookies
        are available from a logged-in browser.
        """
        lat, lng = address.lat, address.lng
        return (
            f"https://www.didi-food.com/es-MX/food/store/"
            f"5764607602869405740/McDonalds/"
            f"?lat={lat}&lng={lng}"
        )

    async def extract_data(
        self,
        client: CloudflareClient,
        url: str,
        products: list[Product],
    ) -> dict[str, Any]:
        """Extract data from DiDi Food using AI-powered /json endpoint."""
        product_names = [p.name for p in products]
        prompt = build_restaurant_prompt("McDonald's", product_names)

        result = await client.extract_json(
            url=url,
            prompt=prompt,
            response_format=RESTAURANT_DATA_SCHEMA,
            wait_until="networkidle0",
        )

        return result

    def parse_response(
        self,
        raw_data: dict[str, Any],
        address: Address,
        products: list[Product],
        url: str,
    ) -> list[ScrapedDataPoint]:
        """Normalize DiDi Food data into standard format."""
        data_points = []
        restaurant_available = raw_data.get("restaurant_available", False)
        extracted_products = raw_data.get("products", [])

        for product in products:
            matched = self._match_product(product, extracted_products)

            if matched:
                dp = ScrapedDataPoint(
                    platform=self.platform_name,
                    address_id=address.id,
                    address_name=address.name,
                    zone_type=address.zone_type,
                    product_id=product.id,
                    product_name=product.name,
                    product_price_mxn=matched.get("price_mxn"),
                    discounted_price_mxn=matched.get("discounted_price_mxn"),
                    delivery_fee_mxn=raw_data.get("delivery_fee_mxn"),
                    service_fee_mxn=raw_data.get("service_fee_mxn"),
                    estimated_minutes_min=raw_data.get("estimated_delivery_minutes_min"),
                    estimated_minutes_max=raw_data.get("estimated_delivery_minutes_max"),
                    restaurant_available=restaurant_available,
                    product_available=matched.get("available", False),
                    discount_text=matched.get("discount_text"),
                    platform_promotions=raw_data.get("platform_promotions", []),
                    url_scraped=url,
                )
            else:
                dp = ScrapedDataPoint(
                    platform=self.platform_name,
                    address_id=address.id,
                    address_name=address.name,
                    zone_type=address.zone_type,
                    product_id=product.id,
                    product_name=product.name,
                    restaurant_available=restaurant_available,
                    product_available=False,
                    delivery_fee_mxn=raw_data.get("delivery_fee_mxn"),
                    service_fee_mxn=raw_data.get("service_fee_mxn"),
                    platform_promotions=raw_data.get("platform_promotions", []),
                    url_scraped=url,
                    error_message="Product not found in extraction results",
                )

            data_points.append(dp)

        return data_points

    def _match_product(
        self, product: Product, extracted: list[dict]
    ) -> dict | None:
        """Fuzzy match reference product to extracted data."""
        for ext in extracted:
            ext_name = (ext.get("name") or "").lower()
            for term in product.search_terms:
                if term.lower() in ext_name:
                    return ext
        return None
