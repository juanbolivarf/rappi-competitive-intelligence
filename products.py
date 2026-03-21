"""
Reference products for cross-platform comparison.

Selection criteria:
1. Available on ALL three platforms (Rappi, Uber Eats, DiDi Food)
2. Standardized — same product regardless of restaurant/store
3. Mix of categories: fast food (restaurant delivery) + retail (convenience)
4. Range of price points to test fee structures at different order values

McDonald's is used as the primary fast food benchmark because:
- Present on all platforms in virtually every zone
- Highly standardized menu (a Big Mac is a Big Mac)
- Most compared product in competitive intelligence globally
"""

from dataclasses import dataclass


@dataclass
class Product:
    """A reference product for cross-platform price comparison."""
    id: str
    name: str
    category: str           # fast_food | retail
    restaurant: str         # Source restaurant/store
    search_terms: list[str] # Terms to search/match on each platform
    expected_price_range: tuple[float, float]  # MXN, for validation

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.restaurant})"


PRODUCTS: list[Product] = [
    Product(
        id="bigmac",
        name="Big Mac",
        category="fast_food",
        restaurant="McDonald's",
        search_terms=["Big Mac", "BigMac", "big mac"],
        expected_price_range=(75.0, 140.0),
    ),
    Product(
        id="combo_mediano",
        name="Combo Mediano (hamburguesa + papas + bebida)",
        category="fast_food",
        restaurant="McDonald's",
        search_terms=["McCombo Mediano", "Combo Mediano", "combo big mac mediano"],
        expected_price_range=(120.0, 200.0),
    ),
    Product(
        id="nuggets_10",
        name="McNuggets 10 piezas",
        category="fast_food",
        restaurant="McDonald's",
        search_terms=["McNuggets 10", "Nuggets 10", "10 McNuggets"],
        expected_price_range=(80.0, 150.0),
    ),
    Product(
        id="coca_500",
        name="Coca-Cola 500ml",
        category="retail",
        restaurant="Convenience / Tienda",
        search_terms=["Coca-Cola 500", "Coca Cola 500ml", "Coca-Cola Original 500"],
        expected_price_range=(15.0, 40.0),
    ),
]


# Helpers
def get_products_by_category(category: str) -> list[Product]:
    """Filter products by category."""
    return [p for p in PRODUCTS if p.category == category]


def get_product_by_id(product_id: str) -> Product | None:
    """Look up a single product by ID."""
    return next((p for p in PRODUCTS if p.id == product_id), None)


# For display/reporting
PRODUCT_SUMMARY = {
    "fast_food": "3 McDonald's items — standardized, available everywhere, range of price points",
    "retail": "1 Coca-Cola 500ml — tests convenience/retail vertical pricing",
}
