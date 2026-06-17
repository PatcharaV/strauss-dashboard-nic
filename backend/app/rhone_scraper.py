import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from .scraper import _extract_material, _plain_text, extract_product_functions

BASE_URL = "https://www.rhone.com"
CATALOG_URL = "https://rhone.myshopify.com"
AUDIENCE_COLLECTIONS = {
    "men": "mens-view-all",
    "women": "womens-view-all",
}
TOP_SELLER_COLLECTIONS = ("mens-best-sellers", "womens-best-sellers")
PAGE_SIZE = 250
CLOTHING_CATEGORIES = {
    "Blazers/Jackets",
    "Bras",
    "Dresses/Jumpsuits",
    "Leggings/Tights",
    "Midlayers",
    "Outerwear",
    "Pants",
    "Polos",
    "Shirts",
    "Shorts",
    "Skirts",
    "Sports bras",
    "Sweaters",
    "Swim",
    "Tanks",
    "Tees",
    "Tees/Tanks",
    "Underwear",
}

COLLECTION_NAMES = {
    "commuter": "Commuter",
    "pursuit": "Pursuit",
    "reign": "Reign",
    "delta": "Delta",
    "makos": "Mako",
    "mako": "Mako",
    "resort": "Resort",
    "outpace": "Outpace",
    "spar": "Spar",
    "dreamglow": "DreamGlow",
    "dream glow": "DreamGlow",
    "revive": "Revive",
    "nomad": "Nomad",
    "course": "Course to Court",
    "swift": "Swift",
    "essentials": "Essentials",
    "clubhouse": "Clubhouse",
}


async def _collection_products(
    client: httpx.AsyncClient, collection: str
) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for page in range(1, 20):
        response = await client.get(
            f"{CATALOG_URL}/collections/{collection}/products.json",
            params={"limit": PAGE_SIZE, "page": page},
        )
        response.raise_for_status()
        batch = response.json().get("products", [])
        products.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        await asyncio.sleep(0.25)
    return products


def _color(product: dict[str, Any]) -> str:
    title = str(product.get("title", ""))
    if " -- " in title:
        return title.rsplit(" -- ", 1)[1].strip()
    for option in product.get("options", []):
        if str(option.get("name", "")).lower() in {"color", "colour"}:
            values = option.get("values") or []
            return " / ".join(str(value) for value in values[:3])
    return ""


def _tag_values(tags: list[str], prefix: str) -> list[str]:
    prefix_lower = prefix.lower()
    values: list[str] = []
    for tag in tags:
        if not tag.lower().startswith(prefix_lower):
            continue
        value = tag[len(prefix) :].strip()
        if value and value not in values:
            values.append(value)
    return values


def _rhone_material(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""

    section_match = re.search(
        r"\bFabric\s*&\s*care\s*:\s*(.+?)(?=\b(?:Model info|You may also like|Shipping|Returns)\b|$)",
        text,
        flags=re.I,
    )
    fabric_text = section_match.group(1).strip() if section_match else text

    care_pattern = (
        r"\b(?:Machine\s+wash|Wash\s+cold|Dry\s+clean|Do\s+not|"
        r"Tumble\s+dry|Only\s+non-chlorine|Cool\s+iron|Imported)\b"
    )
    fabric_text = re.split(care_pattern, fabric_text, maxsplit=1, flags=re.I)[0]

    composition_pattern = (
        r"(?:\d+(?:\.\d+)?%\s+(?:Recycled\s+)?"
        r"(?:Polyester|Polyamide|Elastane|Nylon|Cotton|Linen|Wool|Merino\s+Wool|"
        r"Spandex|Modal|Viscose|Rayon|Acrylic|Polyurethane|Tencel|Lyocell)"
        r"(?:,\s*|\s+and\s+)?)+"
    )

    match = re.search(
        r"\bMade\s+(?:of|with)\s+(.+?)$",
        fabric_text,
        flags=re.I,
    )
    if not match:
        match = re.search(rf"\b({composition_pattern})", fabric_text, flags=re.I)
    if not match:
        return ""

    material = re.sub(r"\s+", " ", match.group(1)).strip(" .")
    composition = re.search(rf"^({composition_pattern})", material, flags=re.I)
    if composition:
        material = composition.group(1).strip(" ,.")
    elif not re.search(composition_pattern, material, flags=re.I):
        return ""
    return material


def _rhone_collections(title: str, handle: str, tags: list[str]) -> list[str]:
    text = f"{title} {handle}".lower()
    collections: list[str] = []
    for tag in tags:
        if tag.lower().startswith("pack:"):
            key = tag.split(":", 1)[1].strip().lower()
            label = COLLECTION_NAMES.get(key, key.replace("-", " ").title())
            if label not in collections:
                collections.append(label)
    for key, label in COLLECTION_NAMES.items():
        if key in text and label not in collections:
            collections.append(label)
    return collections


def _rhone_subcategories(
    title: str, handle: str, category: str, tags: list[str]
) -> list[str]:
    text = f"{title} {handle}".lower()
    subcategories = _tag_values(tags, "filter:Type:")

    def add(value: str) -> None:
        if value not in subcategories:
            subcategories.append(value)

    if "shirt" in text and "button" in text:
        add("Button Downs")
    if "button up" in text or "button-up" in text:
        add("Button ups")
    if "short sleeve" in text or "short-sleeve" in text:
        add("Short sleeves")
    if "long sleeve" in text or "long-sleeve" in text:
        add("Long sleeves")
    if "polo" in text:
        add("Polos")
    if "tee" in text or "t-shirt" in text:
        add("T-Shirts")
    if "tank" in text:
        add("Tanks")
    if "hoody" in text or "hoodie" in text:
        add("Hoodies")
    if "pullover" in text:
        add("Pullovers")
    if "jacket" in text:
        add("Jackets")
    if "blazer" in text:
        add("Blazers")
    if "short" in text:
        add("Lined Shorts" if "lined" in text else "Shorts")
    if "pant" in text:
        add("Pants")
    if "jogger" in text:
        add("Joggers")
    if "legging" in text or "tight" in text:
        add("Leggings")
    if "sweater" in text:
        add("Sweaters")
    if "dress" in text:
        add("Dresses")
    if "skirt" in text or "skort" in text:
        add("Skirts")
    if "bra" in text:
        add("Sports Bras")
    if not subcategories and category:
        add(category)
    if category in {"Shirts", "Tees", "Tees/Tanks"} and (
        "short sleeve" in text or "short-sleeve" in text
    ):
        subcategories = [
            subcategory for subcategory in subcategories if subcategory != "Shorts"
        ]
    return subcategories


def _rhone_features(tags: list[str], top_seller: bool) -> list[str]:
    features = [
        *_tag_values(tags, "filter:Activity:"),
        *_tag_values(tags, "filter:Feature:"),
    ]
    if top_seller or any("best-seller" in tag.lower() for tag in tags):
        features.append("Bestsellers")
    if any(tag.lower() == "flag:new" for tag in tags):
        features.append("New Arrivals")
    return sorted(dict.fromkeys(feature for feature in features if feature))


def _normalize(
    product: dict[str, Any], audiences: set[str], top_seller: bool
) -> dict[str, Any]:
    variants = product.get("variants") or []
    prices = [
        float(variant.get("price", 0))
        for variant in variants
        if variant.get("price") is not None
    ]
    images = product.get("images") or []
    image = product.get("image") or (images[0] if images else {})
    image_url = image.get("src", "") if isinstance(image, dict) else ""
    tags = sorted(set(str(tag) for tag in product.get("tags", [])))
    tagged_type = next(
        (
            tag.split(":", 2)[2]
            for tag in tags
            if tag.lower().startswith("filter:type:")
        ),
        "",
    )
    category = str(product.get("product_type") or tagged_type or "Other").strip()
    handle = str(product.get("handle", ""))
    html = str(product.get("body_html", ""))
    description = _plain_text(html)
    title = str(product.get("title", "")).strip()
    material = _rhone_material(description) or _extract_material(html)
    audience_list = sorted(audiences)
    subcategories = _rhone_subcategories(title, handle, category, tags)
    collections = _rhone_collections(title, handle, tags)
    features = _rhone_features(tags, top_seller)
    return {
        "id": f"rhone:{product.get('id', handle)}",
        "source_id": str(product.get("id", handle)),
        "product_id": str(product.get("id", handle)),
        "brand": "rhone",
        "brand_label": "Rhone",
        "source": BASE_URL,
        "title": title,
        "handle": handle,
        "description": description,
        "category": category,
        "categories": [category],
        "subcategories": subcategories,
        "collections": collections,
        "features": features,
        "vendor": str(product.get("vendor") or "Rhone"),
        "audiences": audience_list,
        "audience_labels": [audience.title() for audience in audience_list],
        "price_min": min(prices, default=0),
        "price_max": max(prices, default=0),
        "available": any(bool(variant.get("available")) for variant in variants),
        "variant_count": len(variants),
        "color": _color(product),
        "tags": tags,
        "image": image_url,
        "url": f"{BASE_URL}/products/{handle}",
        "material": material,
        "material_details": [material] if material else [],
        "product_functions": extract_product_functions(
            title,
            description,
            tags,
            material,
        ),
        "top_seller": top_seller,
        "published_at": product.get("published_at"),
        "updated_at": product.get("updated_at"),
    }


async def scrape_rhone_products() -> dict[str, Any]:
    headers = {
        "User-Agent": "MultiBrandCatalogDashboard/1.0 (+public product analytics)",
        "Accept": "application/json,text/plain,*/*",
    }
    timeout = httpx.Timeout(45.0, connect=15.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        robots = await client.get(f"{CATALOG_URL}/robots.txt")
        robots.raise_for_status()

        products_by_handle: dict[str, dict[str, Any]] = {}
        audiences_by_handle: dict[str, set[str]] = {}
        for audience, collection in AUDIENCE_COLLECTIONS.items():
            for product in await _collection_products(client, collection):
                handle = str(product.get("handle", ""))
                if not handle:
                    continue
                products_by_handle[handle] = product
                audiences_by_handle.setdefault(handle, set()).add(audience)

        top_seller_handles: set[str] = set()
        for collection in TOP_SELLER_COLLECTIONS:
            top_seller_handles.update(
                str(product.get("handle", ""))
                for product in await _collection_products(client, collection)
            )

    products = []
    for handle, product in products_by_handle.items():
        normalized = _normalize(
            product,
            audiences_by_handle.get(handle, set()),
            handle in top_seller_handles,
        )
        if normalized["category"] in CLOTHING_CATEGORIES:
            products.append(normalized)
    products.sort(key=lambda item: item["title"].lower())
    return {
        "source": BASE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "products": products,
    }
