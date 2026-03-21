"""
Basic tests for the scraping infrastructure.
Validates configuration, data models, and scraper structure.
"""

import pytest
from config.addresses import ADDRESSES, get_addresses_by_zone, ZONE_TYPES
from config.products import PRODUCTS, get_product_by_id
from config.settings import Settings
from scraper.base_scraper import ScrapedDataPoint
from scraper.rappi_scraper import RappiScraper
from scraper.ubereats_scraper import UberEatsScraper
from scraper.didifood_scraper import DiDiFoodScraper


class TestAddressConfig:
    def test_has_25_addresses(self):
        assert len(ADDRESSES) == 25

    def test_all_zone_types_represented(self):
        zone_types = {a.zone_type for a in ADDRESSES}
        for zt in ZONE_TYPES:
            assert zt in zone_types, f"Missing zone type: {zt}"

    def test_5_per_zone_type(self):
        for zt in ZONE_TYPES:
            count = len(get_addresses_by_zone(zt))
            assert count == 5, f"Zone {zt} has {count} addresses, expected 5"

    def test_unique_ids(self):
        ids = [a.id for a in ADDRESSES]
        assert len(ids) == len(set(ids)), "Duplicate address IDs found"

    def test_valid_coordinates(self):
        for a in ADDRESSES:
            assert 20.5 < a.lat < 20.8, f"{a.name} lat out of GDL range: {a.lat}"
            assert -103.5 < a.lng < -103.2, f"{a.name} lng out of GDL range: {a.lng}"


class TestProductConfig:
    def test_has_4_products(self):
        assert len(PRODUCTS) == 4

    def test_lookup_by_id(self):
        bigmac = get_product_by_id("bigmac")
        assert bigmac is not None
        assert bigmac.restaurant == "McDonald's"

    def test_price_ranges_valid(self):
        for p in PRODUCTS:
            low, high = p.expected_price_range
            assert low < high, f"{p.name} has invalid price range"
            assert low > 0, f"{p.name} has non-positive min price"

    def test_search_terms_not_empty(self):
        for p in PRODUCTS:
            assert len(p.search_terms) > 0, f"{p.name} has no search terms"


class TestScrapedDataPoint:
    def test_compute_total_basic(self):
        dp = ScrapedDataPoint(
            platform="rappi",
            address_id="hi_01",
            address_name="Providencia",
            zone_type="high_income",
            product_id="bigmac",
            product_name="Big Mac",
            product_price_mxn=99.0,
            delivery_fee_mxn=29.0,
            service_fee_mxn=10.0,
        )
        dp.compute_total()
        assert dp.total_price_mxn == 138.0

    def test_compute_total_with_discount(self):
        dp = ScrapedDataPoint(
            platform="rappi",
            address_id="hi_01",
            address_name="Providencia",
            zone_type="high_income",
            product_id="bigmac",
            product_name="Big Mac",
            product_price_mxn=99.0,
            discounted_price_mxn=79.0,
            delivery_fee_mxn=29.0,
            service_fee_mxn=10.0,
        )
        dp.compute_total()
        assert dp.total_price_mxn == 118.0  # Uses discounted price

    def test_to_dict(self):
        dp = ScrapedDataPoint(
            platform="rappi",
            address_id="hi_01",
            address_name="Test",
            zone_type="high_income",
            product_id="bigmac",
            product_name="Big Mac",
        )
        d = dp.to_dict()
        assert isinstance(d, dict)
        assert d["platform"] == "rappi"


class TestScraperURLs:
    def test_rappi_url_contains_coordinates(self):
        from config.addresses import ADDRESSES
        scraper = RappiScraper()
        url = scraper.build_url(ADDRESSES[0])
        assert "lat=" in url
        assert "lng=" in url
        assert "rappi.com.mx" in url

    def test_ubereats_url_format(self):
        scraper = UberEatsScraper()
        url = scraper.build_url(ADDRESSES[0])
        assert "ubereats.com/mx" in url
        assert "McDonalds" in url

    def test_didifood_url_format(self):
        scraper = DiDiFoodScraper()
        url = scraper.build_url(ADDRESSES[0])
        assert "food.didi.com" in url


class TestSettingsValidation:
    def test_missing_credentials_detected(self):
        s = Settings()
        s.cf_account_id = ""
        s.cf_api_token = ""
        errors = s.validate()
        assert len(errors) == 2
