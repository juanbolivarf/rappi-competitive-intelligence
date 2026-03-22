"""
JSON schemas for Cloudflare Browser Rendering /json endpoint.

These schemas define the EXACT structure we want the AI (Llama 3.3 70B)
to extract from each platform's webpage. The /json endpoint uses these
to return structured, typed data instead of raw HTML.

This is the key differentiator of our approach:
Instead of writing brittle CSS selectors per-platform, we define WHAT
we want and let the AI figure out WHERE it is on the page.
"""


# ── Extraction prompt templates ───────────────────────────────────

RESTAURANT_EXTRACTION_PROMPT = """
Extract the following information for the restaurant "{restaurant_name}" 
on this food delivery platform page:

For each menu item matching these names: {product_names}
- Product name (exact as shown)
- Price in MXN (numeric, before any discounts)
- Discounted price if there's an active promotion
- Any active discount or promotion text

Also extract:
- Delivery fee shown (in MXN, numeric)
- Service fee if visible (in MXN, numeric)  
- Estimated delivery time (in minutes, as a range or single number)
- Any platform-wide promotions or banners visible

If a value is not available or not visible on the page, return null.
"""

RETAIL_EXTRACTION_PROMPT = """
Extract pricing information for the product "{product_name}" from this 
delivery/convenience store page:

- Product name (exact as shown)
- Price in MXN (numeric)
- Discounted price if promotion active
- Delivery fee (in MXN)
- Service fee if visible (in MXN)
- Estimated delivery time (minutes)
- Store/source name
- Any active promotions or discount banners

If a value is not available, return null.
"""


# ── JSON response schemas ─────────────────────────────────────────

RESTAURANT_DATA_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "restaurant_name": {
                "type": ["string", "null"],
                "description": "Name of the restaurant as displayed"
            },
            "restaurant_available": {
                "type": "boolean",
                "description": "Whether the restaurant is currently open/available for orders"
            },
            "products": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": ["string", "null"],
                            "description": "Product name as displayed on the platform"
                        },
                        "price_mxn": {
                            "type": ["number", "null"],
                            "description": "Regular price in Mexican Pesos"
                        },
                        "discounted_price_mxn": {
                            "type": ["number", "null"],
                            "description": "Discounted price if promotion active, null otherwise"
                        },
                        "discount_text": {
                            "type": ["string", "null"],
                            "description": "Promotion or discount description if any"
                        },
                        "available": {
                            "type": "boolean",
                            "description": "Whether the product is currently available"
                        },
                    },
                    "required": ["name", "price_mxn", "discounted_price_mxn", "discount_text", "available"],
                },
            },
            "delivery_fee_mxn": {
                "type": ["number", "null"],
                "description": "Delivery fee in MXN before discounts"
            },
            "service_fee_mxn": {
                "type": ["number", "null"],
                "description": "Platform service fee in MXN"
            },
            "estimated_delivery_minutes_min": {
                "type": ["number", "null"],
                "description": "Minimum estimated delivery time in minutes"
            },
            "estimated_delivery_minutes_max": {
                "type": ["number", "null"],
                "description": "Maximum estimated delivery time in minutes"
            },
            "platform_promotions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of visible platform-wide promotions or banners"
            },
        },
        "required": [
            "restaurant_name", "restaurant_available", "products",
            "delivery_fee_mxn", "service_fee_mxn",
            "estimated_delivery_minutes_min", "estimated_delivery_minutes_max",
            "platform_promotions"
        ],
    },
}


# ── Helper to build extraction requests ───────────────────────────

def build_restaurant_prompt(restaurant_name: str, product_names: list[str]) -> str:
    """Build a formatted extraction prompt for restaurant data."""
    return RESTAURANT_EXTRACTION_PROMPT.format(
        restaurant_name=restaurant_name,
        product_names=", ".join(product_names),
    )


def build_retail_prompt(product_name: str) -> str:
    """Build a formatted extraction prompt for retail product data."""
    return RETAIL_EXTRACTION_PROMPT.format(product_name=product_name)
