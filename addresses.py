"""
Geographic addresses for competitive scraping.

Selection methodology:
- 25 addresses across the Guadalajara Metropolitan Area (ZMG)
- Stratified by income level, commercial activity, and population density
- Covers 5 zone types: high income, mid income, low income/peripheral,
  commercial corridors, and university/student areas
- Each address is a real, recognizable location that delivery platforms serve

Justification:
Pricing, delivery fees, and availability vary significantly by zone.
A representative sample lets us identify WHERE Rappi is competitive
vs where it loses ground — the key input for Pricing and Ops teams.
"""

from dataclasses import dataclass


@dataclass
class Address:
    """A delivery address for scraping."""
    id: str
    name: str
    street: str
    city: str
    zone_type: str  # high_income | mid_income | low_income | commercial | university
    lat: float
    lng: float

    @property
    def full_address(self) -> str:
        return f"{self.street}, {self.city}, Jalisco, México"


ADDRESSES: list[Address] = [
    # ── High Income Zones ──────────────────────────────────────────
    Address(
        id="hi_01", name="Providencia",
        street="Av. Providencia 2577",
        city="Guadalajara", zone_type="high_income",
        lat=20.6936, lng=-103.3894,
    ),
    Address(
        id="hi_02", name="Puerta de Hierro",
        street="Av. Puerta de Hierro 5065",
        city="Zapopan", zone_type="high_income",
        lat=20.7073, lng=-103.4284,
    ),
    Address(
        id="hi_03", name="Colinas de San Javier",
        street="Paseo San Arturo 1850",
        city="Zapopan", zone_type="high_income",
        lat=20.6757, lng=-103.4143,
    ),
    Address(
        id="hi_04", name="Country Club",
        street="Av. de las Rosas 820",
        city="Zapopan", zone_type="high_income",
        lat=20.6816, lng=-103.3979,
    ),
    Address(
        id="hi_05", name="Valle Real",
        street="Av. Valle Real 1000",
        city="Zapopan", zone_type="high_income",
        lat=20.7205, lng=-103.4411,
    ),

    # ── Mid Income Zones ───────────────────────────────────────────
    Address(
        id="mi_01", name="Chapultepec",
        street="Av. Chapultepec 120",
        city="Guadalajara", zone_type="mid_income",
        lat=20.6712, lng=-103.3635,
    ),
    Address(
        id="mi_02", name="Centro Histórico",
        street="Av. Juárez 638",
        city="Guadalajara", zone_type="mid_income",
        lat=20.6737, lng=-103.3474,
    ),
    Address(
        id="mi_03", name="Ciudad del Sol",
        street="Av. López Mateos Sur 2375",
        city="Zapopan", zone_type="mid_income",
        lat=20.6437, lng=-103.3990,
    ),
    Address(
        id="mi_04", name="Jardines del Bosque",
        street="Av. Niños Héroes 2890",
        city="Guadalajara", zone_type="mid_income",
        lat=20.6573, lng=-103.3749,
    ),
    Address(
        id="mi_05", name="La Estancia",
        street="Av. Patria 1891",
        city="Zapopan", zone_type="mid_income",
        lat=20.7030, lng=-103.3722,
    ),

    # ── Low Income / Peripheral Zones ──────────────────────────────
    Address(
        id="li_01", name="Tonalá Centro",
        street="Av. Tonalá 130",
        city="Tonalá", zone_type="low_income",
        lat=20.6250, lng=-103.2434,
    ),
    Address(
        id="li_02", name="Tlaquepaque Centro",
        street="Calle Independencia 202",
        city="San Pedro Tlaquepaque", zone_type="low_income",
        lat=20.6403, lng=-103.3129,
    ),
    Address(
        id="li_03", name="Miravalle",
        street="Av. 8 de Julio 3090",
        city="Guadalajara", zone_type="low_income",
        lat=20.6189, lng=-103.3483,
    ),
    Address(
        id="li_04", name="Oblatos",
        street="Calz. Independencia Norte 2950",
        city="Guadalajara", zone_type="low_income",
        lat=20.7014, lng=-103.3211,
    ),
    Address(
        id="li_05", name="Tetlán",
        street="Av. Revolución 1580",
        city="Guadalajara", zone_type="low_income",
        lat=20.6675, lng=-103.2988,
    ),

    # ── Commercial Corridors ───────────────────────────────────────
    Address(
        id="co_01", name="Andares",
        street="Blvd. Puerta de Hierro 4965",
        city="Zapopan", zone_type="commercial",
        lat=20.7063, lng=-103.4264,
    ),
    Address(
        id="co_02", name="Plaza del Sol",
        street="Av. López Mateos Sur 2375",
        city="Guadalajara", zone_type="commercial",
        lat=20.6485, lng=-103.3945,
    ),
    Address(
        id="co_03", name="Av. Vallarta Poniente",
        street="Av. Vallarta 6503",
        city="Zapopan", zone_type="commercial",
        lat=20.6819, lng=-103.4177,
    ),
    Address(
        id="co_04", name="Galerías",
        street="Av. Vallarta 3959",
        city="Zapopan", zone_type="commercial",
        lat=20.6806, lng=-103.3906,
    ),
    Address(
        id="co_05", name="Plaza Patria",
        street="Av. Patria 2085",
        city="Zapopan", zone_type="commercial",
        lat=20.7089, lng=-103.3781,
    ),

    # ── University / Student Zones ─────────────────────────────────
    Address(
        id="un_01", name="ITESO",
        street="Periférico Sur Manuel Gómez Morín 8585",
        city="Tlaquepaque", zone_type="university",
        lat=20.6081, lng=-103.4166,
    ),
    Address(
        id="un_02", name="UDG CUCEI",
        street="Blvd. Gral. Marcelino García Barragán 1421",
        city="Guadalajara", zone_type="university",
        lat=20.6548, lng=-103.3258,
    ),
    Address(
        id="un_03", name="Tec de Monterrey GDL",
        street="Av. Gral. Ramón Corona 2514",
        city="Zapopan", zone_type="university",
        lat=20.7354, lng=-103.4554,
    ),
    Address(
        id="un_04", name="UAG",
        street="Av. Patria 1201",
        city="Zapopan", zone_type="university",
        lat=20.6971, lng=-103.3694,
    ),
    Address(
        id="un_05", name="UDG CUCEA",
        street="Periférico Norte 799",
        city="Zapopan", zone_type="university",
        lat=20.7399, lng=-103.3812,
    ),
]


# Quick access helpers
def get_addresses_by_zone(zone_type: str) -> list[Address]:
    """Filter addresses by zone type."""
    return [a for a in ADDRESSES if a.zone_type == zone_type]


def get_address_by_id(address_id: str) -> Address | None:
    """Look up a single address by ID."""
    return next((a for a in ADDRESSES if a.id == address_id), None)


ZONE_TYPES = ["high_income", "mid_income", "low_income", "commercial", "university"]

# Summary for documentation
ZONE_SUMMARY = {
    "high_income": "5 addresses — affluent residential zones with high purchasing power",
    "mid_income": "5 addresses — middle-class neighborhoods, mainstream consumer base",
    "low_income": "5 addresses — peripheral/popular zones, price-sensitive consumers",
    "commercial": "5 addresses — shopping corridors and malls, high delivery volume",
    "university": "5 addresses — student areas, price-sensitive but tech-savvy",
}
