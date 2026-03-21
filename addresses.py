"""
Geographic addresses for competitive scraping.

The project now supports three metro areas:
- Guadalajara
- Monterrey
- CDMX

Each metro area includes one representative address for each strategic zone:
- high_income
- mid_income
- low_income
- commercial
- university
"""

from dataclasses import dataclass


@dataclass
class Address:
    """A delivery address for scraping."""

    id: str
    name: str
    street: str
    city: str
    state: str
    metro_area: str
    zone_type: str
    lat: float
    lng: float

    @property
    def full_address(self) -> str:
        return f"{self.street}, {self.city}, {self.state}, Mexico"


ADDRESSES: list[Address] = [
    # Guadalajara
    Address(
        id="gdl_hi_01",
        name="Providencia",
        street="Av. Providencia 2577",
        city="Guadalajara",
        state="Jalisco",
        metro_area="guadalajara",
        zone_type="high_income",
        lat=20.6936,
        lng=-103.3894,
    ),
    Address(
        id="gdl_mi_01",
        name="Chapultepec",
        street="Av. Chapultepec 120",
        city="Guadalajara",
        state="Jalisco",
        metro_area="guadalajara",
        zone_type="mid_income",
        lat=20.6712,
        lng=-103.3635,
    ),
    Address(
        id="gdl_li_01",
        name="Tonala Centro",
        street="Av. Tonala 130",
        city="Tonala",
        state="Jalisco",
        metro_area="guadalajara",
        zone_type="low_income",
        lat=20.6250,
        lng=-103.2434,
    ),
    Address(
        id="gdl_co_01",
        name="Andares",
        street="Blvd. Puerta de Hierro 4965",
        city="Zapopan",
        state="Jalisco",
        metro_area="guadalajara",
        zone_type="commercial",
        lat=20.7063,
        lng=-103.4264,
    ),
    Address(
        id="gdl_un_01",
        name="ITESO",
        street="Periferico Sur Manuel Gomez Morin 8585",
        city="Tlaquepaque",
        state="Jalisco",
        metro_area="guadalajara",
        zone_type="university",
        lat=20.6081,
        lng=-103.4166,
    ),
    # Monterrey
    Address(
        id="mty_hi_01",
        name="San Pedro Garza Garcia",
        street="Av. Jose Vasconcelos 150",
        city="San Pedro Garza Garcia",
        state="Nuevo Leon",
        metro_area="monterrey",
        zone_type="high_income",
        lat=25.6516,
        lng=-100.4021,
    ),
    Address(
        id="mty_mi_01",
        name="Contry",
        street="Av. Alfonso Reyes 2800",
        city="Monterrey",
        state="Nuevo Leon",
        metro_area="monterrey",
        zone_type="mid_income",
        lat=25.6507,
        lng=-100.2750,
    ),
    Address(
        id="mty_li_01",
        name="Guadalupe Centro",
        street="Av. Benito Juarez 100",
        city="Guadalupe",
        state="Nuevo Leon",
        metro_area="monterrey",
        zone_type="low_income",
        lat=25.6774,
        lng=-100.2597,
    ),
    Address(
        id="mty_co_01",
        name="Valle Oriente",
        street="Av. Lazaro Cardenas 1000",
        city="San Pedro Garza Garcia",
        state="Nuevo Leon",
        metro_area="monterrey",
        zone_type="commercial",
        lat=25.6407,
        lng=-100.3170,
    ),
    Address(
        id="mty_un_01",
        name="Tec de Monterrey MTY",
        street="Av. Eugenio Garza Sada 2501",
        city="Monterrey",
        state="Nuevo Leon",
        metro_area="monterrey",
        zone_type="university",
        lat=25.6516,
        lng=-100.2895,
    ),
    # CDMX
    Address(
        id="cdmx_hi_01",
        name="Polanco",
        street="Av. Presidente Masaryk 111",
        city="Miguel Hidalgo",
        state="Ciudad de Mexico",
        metro_area="cdmx",
        zone_type="high_income",
        lat=19.4327,
        lng=-99.2007,
    ),
    Address(
        id="cdmx_mi_01",
        name="Del Valle",
        street="Av. Insurgentes Sur 1100",
        city="Benito Juarez",
        state="Ciudad de Mexico",
        metro_area="cdmx",
        zone_type="mid_income",
        lat=19.3828,
        lng=-99.1773,
    ),
    Address(
        id="cdmx_li_01",
        name="Iztapalapa Centro",
        street="Calzada Ermita Iztapalapa 800",
        city="Iztapalapa",
        state="Ciudad de Mexico",
        metro_area="cdmx",
        zone_type="low_income",
        lat=19.3574,
        lng=-99.0926,
    ),
    Address(
        id="cdmx_co_01",
        name="Reforma Centro",
        street="Paseo de la Reforma 222",
        city="Cuauhtemoc",
        state="Ciudad de Mexico",
        metro_area="cdmx",
        zone_type="commercial",
        lat=19.4273,
        lng=-99.1676,
    ),
    Address(
        id="cdmx_un_01",
        name="UNAM CU",
        street="Av. Universidad 3000",
        city="Coyoacan",
        state="Ciudad de Mexico",
        metro_area="cdmx",
        zone_type="university",
        lat=19.3320,
        lng=-99.1885,
    ),
]


def get_addresses_by_zone(zone_type: str) -> list[Address]:
    """Filter addresses by zone type."""
    return [a for a in ADDRESSES if a.zone_type == zone_type]


def get_addresses_by_market(metro_area: str) -> list[Address]:
    """Filter addresses by metro area."""
    return [a for a in ADDRESSES if a.metro_area == metro_area]


def get_address_by_id(address_id: str) -> Address | None:
    """Look up a single address by ID."""
    return next((a for a in ADDRESSES if a.id == address_id), None)


ZONE_TYPES = ["high_income", "mid_income", "low_income", "commercial", "university"]
MARKET_AREAS = ["guadalajara", "monterrey", "cdmx"]
MARKET_LABELS = {
    "guadalajara": "Guadalajara",
    "monterrey": "Monterrey",
    "cdmx": "CDMX",
}

ZONE_SUMMARY = {
    "high_income": "Affluent residential zones with high purchasing power",
    "mid_income": "Middle-class neighborhoods and mainstream demand",
    "low_income": "Price-sensitive peripheral or popular zones",
    "commercial": "High-traffic shopping and business corridors",
    "university": "Student-heavy, frequency-driven demand pockets",
}
