"""
Synthetic Data Generator for Competitive Intelligence.

Generates realistic scraped data based on known market patterns
in Guadalajara's delivery ecosystem. Used for:
1. Testing the full analysis + visualization pipeline
2. Backup data for presentation (in case live scraping fails)
3. Demonstrating the system's analytical capabilities

Pricing assumptions based on public observation of GDL delivery market:
- Rappi: mid-range pricing, competitive delivery fees
- Uber Eats: slightly higher product prices, lower delivery fees
- DiDi Food: aggressive pricing (lowest), higher delivery fees in periphery
"""

import json
import random
from datetime import datetime
from pathlib import Path

import numpy as np

from config.addresses import ADDRESSES
from config.products import PRODUCTS
from config.settings import settings


# ── Market parameters (calibrated to GDL reality) ────────────────

PLATFORM_PROFILES = {
    "rappi": {
        "price_multiplier": 1.00,       # Baseline
        "delivery_fee_base": 25,
        "delivery_fee_zone_delta": {     # Fee adjustment by zone
            "high_income": -5,           # Closer to dark stores
            "mid_income": 0,
            "commercial": -3,
            "university": +5,
            "low_income": +12,           # Peripheral zones = higher fees
        },
        "service_fee_pct": 0.10,         # 10% service fee
        "eta_base": 28,
        "eta_zone_delta": {
            "high_income": -6,
            "mid_income": -3,
            "commercial": -5,
            "university": +3,
            "low_income": +8,
        },
        "promo_probability": 0.35,
        "promos": [
            "Envío Gratis: Aplican TyC",
            "2x1 en combos seleccionados",
            "10% OFF primera orden",
            "$50 de descuento con RappiPrime",
        ],
        "availability_rate": 0.92,
    },
    "ubereats": {
        "price_multiplier": 1.05,        # ~5% more expensive
        "delivery_fee_base": 19,          # Lower base fee
        "delivery_fee_zone_delta": {
            "high_income": -4,
            "mid_income": 0,
            "commercial": -2,
            "university": +8,
            "low_income": +15,           # Much higher in periphery
        },
        "service_fee_pct": 0.15,          # 15% service fee (higher)
        "eta_base": 30,
        "eta_zone_delta": {
            "high_income": -5,
            "mid_income": -2,
            "commercial": -4,
            "university": +5,
            "low_income": +10,
        },
        "promo_probability": 0.25,
        "promos": [
            "Envío GRATIS en tu primer pedido",
            "$80 OFF con código UBERMX",
            "2x1 en McFlurry",
        ],
        "availability_rate": 0.88,
    },
    "didifood": {
        "price_multiplier": 0.93,         # ~7% cheaper (aggressive pricing)
        "delivery_fee_base": 22,
        "delivery_fee_zone_delta": {
            "high_income": -3,
            "mid_income": 0,
            "commercial": -2,
            "university": +6,
            "low_income": +18,            # Highest peripheral premium
        },
        "service_fee_pct": 0.08,           # Lower service fee
        "eta_base": 32,
        "eta_zone_delta": {
            "high_income": -4,
            "mid_income": -1,
            "commercial": -3,
            "university": +6,
            "low_income": +12,
        },
        "promo_probability": 0.45,         # Most aggressive promos
        "promos": [
            "Hasta 60% OFF en restaurantes",
            "Envío $9 en tu primer pedido",
            "$70 de descuento DiDi",
            "Combo + bebida GRATIS",
            "Flash Sale: 40% OFF",
        ],
        "availability_rate": 0.82,         # Lowest coverage
    },
}

# Base product prices (MXN) — realistic McDonald's GDL pricing
BASE_PRICES = {
    "bigmac": 95,
    "combo_mediano": 155,
    "nuggets_10": 109,
    "coca_500": 25,
}


def generate_synthetic_data(seed: int = 42) -> list[dict]:
    """Generate a complete set of realistic synthetic scraped data."""
    np.random.seed(seed)
    random.seed(seed)
    data_points = []

    for platform_name, profile in PLATFORM_PROFILES.items():
        for address in ADDRESSES:
            zone = address.zone_type

            # Determine if restaurant is available at this location
            is_available = random.random() < profile["availability_rate"]

            # Calculate zone-adjusted delivery fee
            base_fee = profile["delivery_fee_base"]
            zone_delta = profile["delivery_fee_zone_delta"].get(zone, 0)
            delivery_fee = max(0, base_fee + zone_delta + np.random.normal(0, 3))

            # Calculate zone-adjusted ETA
            base_eta = profile["eta_base"]
            eta_delta = profile["eta_zone_delta"].get(zone, 0)
            eta_min = max(10, int(base_eta + eta_delta + np.random.normal(0, 3)))
            eta_max = eta_min + random.choice([5, 10, 10, 15])

            # Determine promotion
            has_promo = random.random() < profile["promo_probability"]
            promo_text = random.choice(profile["promos"]) if has_promo else None
            platform_promos = [random.choice(profile["promos"])] if random.random() < 0.6 else []

            for product in PRODUCTS:
                base_price = BASE_PRICES[product.id]
                price = base_price * profile["price_multiplier"]
                # Add zone noise (+/- 5%)
                price *= (1 + np.random.normal(0, 0.03))
                price = round(price, 0)

                # Service fee based on product price
                service_fee = round(price * profile["service_fee_pct"] + np.random.normal(0, 1), 0)
                service_fee = max(0, service_fee)

                # Discount (when promo active, 10-25% off)
                discounted = None
                if has_promo and random.random() < 0.4:
                    discount_pct = random.uniform(0.10, 0.25)
                    discounted = round(price * (1 - discount_pct), 0)

                # Product availability (sometimes specific items are unavailable)
                product_avail = is_available and (random.random() < 0.95)

                effective = discounted if discounted else price
                total = effective + delivery_fee + service_fee

                data_points.append({
                    "platform": platform_name,
                    "address_id": address.id,
                    "address_name": address.name,
                    "zone_type": zone,
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_price_mxn": price if product_avail else None,
                    "discounted_price_mxn": discounted,
                    "delivery_fee_mxn": round(delivery_fee, 0),
                    "service_fee_mxn": service_fee,
                    "total_price_mxn": round(total, 0) if product_avail else None,
                    "estimated_minutes_min": eta_min,
                    "estimated_minutes_max": eta_max,
                    "restaurant_available": is_available,
                    "product_available": product_avail,
                    "discount_text": promo_text if discounted else None,
                    "platform_promotions": platform_promos,
                    "scraped_at": datetime.now().isoformat(),
                    "scrape_success": True,
                    "error_message": None,
                    "url_scraped": f"https://synthetic-data/{platform_name}/{address.id}",
                })

    return data_points


def save_synthetic_data() -> Path:
    """Generate and save synthetic data to the raw data directory."""
    data = generate_synthetic_data()
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = settings.raw_data_dir / f"scrape_{ts}.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(data)} data points → {path}")
    return path


if __name__ == "__main__":
    save_synthetic_data()
