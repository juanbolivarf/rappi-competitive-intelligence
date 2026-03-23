import asyncio
import httpx
import json
import re
from bs4 import BeautifulSoup

async def test():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        url = "https://www.ubereats.com/mx-en/store/mcdonalds-centro/pVf6cMIlRtCP2DC0iy7t4w"
        response = await client.get(url)
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        for script in soup.find_all("script", {"type": "application/ld+json"}):
            if script.string:
                try:
                    data = json.loads(script.string)
                    if data.get("@type") == "Restaurant":
                        print(f"Restaurant: {data.get('name')}")

                        menu = data.get("hasMenu", {})
                        sections = menu.get("hasMenuSection", [])

                        all_products = []
                        for section in sections:
                            items = section.get("hasMenuItem", [])
                            for item in items:
                                name = item.get("name", "")
                                offers = item.get("offers", {})
                                price = None
                                if isinstance(offers, dict):
                                    price_str = offers.get("price", "")
                                    if price_str:
                                        try:
                                            price = float(re.sub(r"[^0-9.]", "", str(price_str)))
                                        except:
                                            pass
                                all_products.append({"name": name, "price": price})

                        print(f"Total products extracted: {len(all_products)}")

                        # Find matches
                        search_terms = {
                            "Big Mac": ["big mac"],
                            "McNuggets": ["nuggets", "mcnuggets"],
                            "McTrio": ["mctrio", "trio"],
                            "Coca-Cola": ["coca"],
                        }

                        for product_name, terms in search_terms.items():
                            for p in all_products:
                                name_lower = p["name"].lower()
                                for term in terms:
                                    if term in name_lower:
                                        safe_name = p["name"].encode("ascii", "replace").decode()
                                        print(f"  [OK] {product_name}: {safe_name} = ${p['price']}")
                                        break
                                else:
                                    continue
                                break

                except Exception as e:
                    print(f"Error: {e}")

asyncio.run(test())
