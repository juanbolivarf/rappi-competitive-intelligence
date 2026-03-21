"""
Rappi scraper — baseline data collection.

Strategy:
- Uses Cloudflare /json endpoint to extract structured data via AI
- Rappi's web app is a React SPA, so we need full JS rendering (networkidle0)
- URL pattern: https://www.rappi.com.mx/restaurantes/mcdonalds-{slug}
  (we construct search URLs and let the AI extract from the results page)

Note: Rappi baseline data is critical for the comparison — it's what
the Pricing/Ops teams already partially know, but not systematically.
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


class RappiScraper(BaseScraper):

    @property
    def platform_name(self) -> str:
        return "rappi"

    def build_url(self, address: Address, restaurant: str = "McDonald's") -> str:
        """
        Construct Rappi McDonald's restaurant URL.

        KEY FINDING from live testing:
        - Search page (?term=McDonalds) doesn't filter server-side
        - Direct store pages work: /restaurantes/{store_id}-{slug}
        - The /json endpoint successfully extracts product pricing from store pages
        - Store ID 1306703465 = McDonald's in GDL area

        Strategy: use direct store URL for product pricing,
        with lat/lng as context for delivery fee calculation.
        """
        lat, lng = address.lat, address.lng
        # Direct McDonald's store page (discovered via live scraping)
        return (
            f"https://www.rappi.com.mx/restaurantes/1306703465-mcdonalds"
            f"?lat={lat}&lng={lng}"
        )

    async def extract_data(
        self,
        client: CloudflareClient,
        url: str,
        products: list[Product],
    ) -> dict[str, Any]:
        """
        Use Cloudflare /json endpoint to extract structured restaurant data.
        The AI handles the complexity of Rappi's dynamic React UI.
        """
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
        """
        Normalize Rappi AI-extracted data into ScrapedDataPoint objects.
        """
        data_points = []
        restaurant_available = raw_data.get("restaurant_available", False)
        extracted_products = raw_data.get("products", [])

        for product in products:
            # Try to match extracted product to our reference product
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
                    estimated_minutes_min=raw_data.get("estimated_delivery_minutes_min"),
                    estimated_minutes_max=raw_data.get("estimated_delivery_minutes_max"),
                    platform_promotions=raw_data.get("platform_promotions", []),
                    url_scraped=url,
                    error_message="Product not found in extraction results",
                )

            data_points.append(dp)

        return data_points

    def _match_product(
        self, product: Product, extracted: list[dict]
    ) -> dict | None:
        """
        Fuzzy match a reference product to the AI-extracted product list.
        Uses search terms from product config for flexible matching.
        """
        for ext in extracted:
            ext_name = (ext.get("name") or "").lower()
            for term in product.search_terms:
                if term.lower() in ext_name:
                    return ext
        return None
