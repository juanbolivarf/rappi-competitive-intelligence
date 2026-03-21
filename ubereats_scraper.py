"""
Uber Eats scraper — Competitor #1.

Strategy:
- Uber Eats web app at ubereats.com uses React with server-side rendering
- URL pattern: https://www.ubereats.com/mx/store/mcdonalds-{slug}
- Location set via URL params or cookies
- Same AI extraction approach via /json endpoint
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


class UberEatsScraper(BaseScraper):

    @property
    def platform_name(self) -> str:
        return "ubereats"

    def build_url(self, address: Address, restaurant: str = "McDonald's") -> str:
        """
        Construct Uber Eats URL with location context.

        KEY FINDING from live testing:
        - The main ubereats.com/mx site shows a login wall for unauthenticated users
        - The mx-en (English) subdomain has PUBLIC direct store pages
        - Direct store URLs bypass the login wall entirely
        - URL pattern: /mx-en/store/{slug}/{store_id}

        Strategy: use a set of pre-discovered McDonald's store IDs for GDL,
        then select the nearest one based on address coordinates.
        """
        market_stores = {
            "guadalajara": [
                {"slug": "mcdonalds-centro", "id": "pVf6cMIlRtCP2DC0iy7t4w", "lat": 20.6737, "lng": -103.3474},
                {"slug": "mcdonalds-plaza-independencia", "id": "HqLRowiBS5KMBfE48ygXgg", "lat": 20.7014, "lng": -103.3211},
                {"slug": "mcdonalds-plaza-midtown", "id": "KwUtfEVXQA6HYy9xbMphvA", "lat": 20.6806, "lng": -103.3906},
                {"slug": "mcdonalds-la-normal-av-avila-camacho", "id": "2RRMtHa9R1KNZ0ze98zJPw", "lat": 20.6880, "lng": -103.3560},
                {"slug": "mcdonalds-avenida-mariano-otero", "id": "4gmTDifEQHm5pbiKs4vDBQ", "lat": 20.6437, "lng": -103.3990},
            ],
            "monterrey": [
                {"slug": "mcdonalds-garza-sada", "id": "922nSYLsT1-ERjpi9jnvgw", "lat": 25.6516, "lng": -100.2895},
            ],
            "cdmx": [
                {"slug": "mcdonalds-aeropuerto", "id": "ansFddgoSGilvVgV7sGxoA", "lat": 19.4240, "lng": -99.0844},
            ],
        }

        stores = market_stores.get(address.metro_area, market_stores["guadalajara"])

        # Find nearest McDonald's to this address
        nearest = min(
            stores,
            key=lambda s: (s["lat"] - address.lat) ** 2 + (s["lng"] - address.lng) ** 2,
        )

        return f"https://www.ubereats.com/mx-en/store/{nearest['slug']}/{nearest['id']}"

    async def extract_data(
        self,
        client: CloudflareClient,
        url: str,
        products: list[Product],
    ) -> dict[str, Any]:
        """Extract data from Uber Eats using AI-powered /json endpoint."""
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
        """Normalize Uber Eats data into standard format."""
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
                    metro_area=address.metro_area,
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
                    metro_area=address.metro_area,
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
