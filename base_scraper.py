"""
Abstract base scraper class.

All platform-specific scrapers inherit from this and implement:
- build_url(): construct the platform URL for a given address + restaurant
- parse_response(): normalize AI-extracted data into our standard format

The base class provides:
- Orchestration: iterate over addresses × products with rate limiting
- Error handling: per-request try/catch with structured logging
- Data collection: accumulate results into a standard schema
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from config.addresses import Address
from config.products import Product
from scraper.cloudflare_client import CloudflareClient, CloudflareClientError

logger = logging.getLogger(__name__)


@dataclass
class ScrapedDataPoint:
    """
    A single data point: one product, one platform, one address.
    This is our universal schema — all platforms normalize into this.
    """
    # Identifiers
    platform: str
    address_id: str
    address_name: str
    zone_type: str
    metro_area: str
    product_id: str
    product_name: str

    # Pricing
    product_price_mxn: float | None = None
    discounted_price_mxn: float | None = None
    delivery_fee_mxn: float | None = None
    service_fee_mxn: float | None = None
    total_price_mxn: float | None = None  # Computed: price + fees

    # Delivery
    estimated_minutes_min: int | None = None
    estimated_minutes_max: int | None = None

    # Availability
    restaurant_available: bool = False
    product_available: bool = False

    # Promotions
    discount_text: str | None = None
    platform_promotions: list[str] = field(default_factory=list)

    # Metadata
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scrape_success: bool = True
    error_message: str | None = None
    url_scraped: str | None = None

    def compute_total(self):
        """Calculate total price the user actually pays."""
        if self.product_price_mxn is not None:
            effective_price = self.discounted_price_mxn or self.product_price_mxn
            fees = (self.delivery_fee_mxn or 0) + (self.service_fee_mxn or 0)
            self.total_price_mxn = round(effective_price + fees, 2)

    def to_dict(self) -> dict:
        return asdict(self)


class BaseScraper(ABC):
    """
    Abstract base for platform-specific scrapers.

    Subclasses must implement:
    - platform_name: str property
    - build_url(address, restaurant): construct the platform URL
    - extract_data(client, url, products): call CF API and return raw data
    - parse_response(raw, address, products): normalize into ScrapedDataPoint list
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Identifier for this platform (e.g., 'rappi', 'ubereats')."""
        ...

    @abstractmethod
    def build_url(self, address: Address, restaurant: str = "McDonald's") -> str:
        """Construct the platform URL for a given address and restaurant."""
        ...

    @abstractmethod
    async def extract_data(
        self,
        client: CloudflareClient,
        url: str,
        products: list[Product],
    ) -> dict[str, Any]:
        """
        Call Cloudflare API to extract data from the platform page.
        Returns raw extraction result (platform-specific format).
        """
        ...

    @abstractmethod
    def parse_response(
        self,
        raw_data: dict[str, Any],
        address: Address,
        products: list[Product],
        url: str,
    ) -> list[ScrapedDataPoint]:
        """
        Normalize raw API response into list of ScrapedDataPoint.
        One data point per product found.
        """
        ...

    async def scrape_address(
        self,
        client: CloudflareClient,
        address: Address,
        products: list[Product],
    ) -> list[ScrapedDataPoint]:
        """
        Scrape all products for a single address on this platform.
        Handles errors gracefully — returns error data points on failure.
        """
        url = self.build_url(address)
        logger.info(
            f"[{self.platform_name}] Scraping {address.name} ({address.zone_type}) → {url[:80]}"
        )

        try:
            raw_data = await self.extract_data(client, url, products)
            data_points = self.parse_response(raw_data, address, products, url)

            # Compute totals
            for dp in data_points:
                dp.compute_total()

            success_count = sum(1 for dp in data_points if dp.scrape_success)
            logger.info(
                f"[{self.platform_name}] ✓ {address.name}: "
                f"{success_count}/{len(data_points)} products extracted"
            )
            return data_points

        except CloudflareClientError as e:
            logger.error(f"[{self.platform_name}] ✗ {address.name}: CF API error — {e}")
            return self._error_data_points(address, products, url, str(e))

        except Exception as e:
            logger.error(f"[{self.platform_name}] ✗ {address.name}: Unexpected error — {e}")
            return self._error_data_points(address, products, url, str(e))

    async def scrape_all(
        self,
        client: CloudflareClient,
        addresses: list[Address],
        products: list[Product],
    ) -> list[ScrapedDataPoint]:
        """
        Scrape all addresses sequentially (respecting rate limits).
        Returns flat list of all data points.
        """
        all_results: list[ScrapedDataPoint] = []

        logger.info(
            f"[{self.platform_name}] Starting scrape: "
            f"{len(addresses)} addresses × {len(products)} products"
        )

        for i, address in enumerate(addresses, 1):
            logger.info(
                f"[{self.platform_name}] Progress: {i}/{len(addresses)} — {address.name}"
            )
            results = await self.scrape_address(client, address, products)
            all_results.extend(results)

        # Summary
        total = len(all_results)
        successes = sum(1 for r in all_results if r.scrape_success)
        logger.info(
            f"[{self.platform_name}] Complete: {successes}/{total} data points collected"
        )

        return all_results

    def _error_data_points(
        self,
        address: Address,
        products: list[Product],
        url: str,
        error_msg: str,
    ) -> list[ScrapedDataPoint]:
        """Generate error data points when scraping fails for an address."""
        return [
            ScrapedDataPoint(
                platform=self.platform_name,
                address_id=address.id,
                address_name=address.name,
                zone_type=address.zone_type,
                metro_area=address.metro_area,
                product_id=product.id,
                product_name=product.name,
                scrape_success=False,
                error_message=error_msg,
                url_scraped=url,
            )
            for product in products
        ]
