import asyncio
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote

import httpx

BASE_URL = "https://shop.lululemon.com"
PRODUCT_SITEMAP_URL = f"{BASE_URL}/sitemap/Product_Sitemap_en_US.xml"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

EXCLUDED_SEGMENT_KEYWORDS = {
    "accessories",
    "backpack",
    "bag",
    "belt-bags",
    "bottles",
    "crossbody",
    "duffle",
    "equipment",
    "gloves",
    "hair",
    "hats",
    "headbands",
    "keychains",
    "mat",
    "socks",
    "shoes",
    "sneakers",
    "towels",
    "visors",
    "wallets",
    "water-bottles",
    "yoga-mats",
}

FABRIC_KEYWORDS = [
    "Canvas",
    "Cotton",
    "Everlux",
    "Fleece",
    "French Terry",
    "Luon",
    "Luxtreme",
    "Mesh",
    "Nulu",
    "Nulux",
    "Pima Cotton",
    "Ripstop",
    "Softstreme",
    "Swift",
    "Ultralu",
    "Utilitech",
    "VersaTwill",
    "Warpstreme",
    "Wool",
]

COLLECTION_KEYWORDS = [
    "ABC",
    "Align",
    "Always In Motion",
    "Cityverse",
    "Dance Studio",
    "Define",
    "Fast and Free",
    "Fundamental",
    "Groove",
    "Hotty Hot",
    "License to Train",
    "Metal Vent Tech",
    "Pace Breaker",
    "Scuba",
    "ShowZero",
    "Soft Jersey",
    "Steady State",
    "Swiftly",
    "Unshaken",
    "Wunder Train",
    "Zeroed In",
]


def _append_unique(values: list[str], incoming: Any) -> None:
    if incoming is None:
        return
    items = incoming if isinstance(incoming, list) else [incoming]
    for item in items:
        value = str(item).strip()
        if value and value not in values:
            values.append(value)


def _parse_product_url(url: str) -> dict[str, str] | None:
    match = re.search(r"/p/([^/]+)/([^/]+)/_/([^/?#]+)", url)
    if not match:
        return None
    segment, title_slug, product_id = match.groups()
    return {
        "segment": unquote(segment),
        "title_slug": unquote(title_slug),
        "product_id": product_id,
    }


def _title_from_slug(slug: str) -> str:
    title = slug.replace("-", " ").strip()
    title = re.sub(r"\s+MD$", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title)
    return title


def _audience(segment: str) -> tuple[list[str], list[str]]:
    lower = segment.lower()
    if lower.startswith(("women", "womens", "w-")):
        return ["women"], ["Women"]
    if lower.startswith(("men", "mens")):
        return ["men"], ["Men"]
    if lower.startswith(
        (
            "jackets-and-hoodies",
            "jumpsuits-rompers",
            "skirts-and-dresses",
            "tops-long-sleeve",
            "tops-short-sleeve",
        )
    ):
        return ["women"], ["Women"]
    return ["unisex"], ["Unisex"]


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _fallback_category(segment: str, title: str) -> str:
    text = f"{segment} {title}".lower()
    if "sports-bra" in text or re.search(r"\bbra\b", text):
        return "Sports Bras"
    if "dress" in text or "jumpsuit" in text or "romper" in text:
        return "Dresses"
    if "skirt" in text or "skort" in text:
        return "Skirts"
    if "legging" in text or "tight" in text or "capri" in text:
        return "Leggings"
    if "jogger" in text or "sweatpant" in text:
        return "Pants"
    if "pant" in text or "trouser" in text:
        return "Pants"
    if "hoodie" in text or "sweatshirt" in text:
        return "Hoodies & Sweatshirts"
    if "pullover" in text and "shirt" not in text:
        return "Hoodies & Sweatshirts"
    if "short" in text and "shirt" not in text:
        return "Shorts"
    if "outerwear" in text or "jacket" in text or "coat" in text or "vest" in text:
        return "Coats & Jackets"
    if "sweater" in text or "quarter-zip" in text or "quarter zip" in text:
        return "Sweaters"
    if "tank" in text:
        return "Tank Tops"
    if (
        "shirt" in text
        or "tee" in text
        or "polo" in text
        or "ss-top" in text
        or "ls-top" in text
    ):
        return "Shirts"
    if "underwear" in text or "boxer" in text:
        return "Underwear"
    if "swim" in text:
        return "Swim"
    return "Other"


def _website_category(segment: str, title: str, fallback_category: str) -> str:
    text = f"{segment} {title}".lower()
    rules = [
        ("Button Down Shirts", ("button-down", "button down")),
        ("Polo Shirts", ("polo",)),
        ("Long Sleeve Shirts", ("long-sleeve", "long sleeve", "ls-top", "ls tops")),
        ("Short Sleeve Shirts", ("short-sleeve", "short sleeve", "ss-top", "ss tops")),
        ("T-Shirts", ("t-shirt", "t shirt", "tee")),
        ("Tank Tops", ("tank", "cami")),
        ("Quarter Zips", ("quarter-zip", "quarter zip", "half zip", "1/2 zip")),
        ("Hoodies", ("hoodie",)),
        ("Sweatshirts", ("sweatshirt", "crewneck")),
        ("Sweatpants", ("sweatpant",)),
        ("Joggers", ("jogger",)),
        ("Dress Pants", ("dress pant",)),
        ("Trousers", ("trouser",)),
        ("Leggings", ("legging", "tight")),
        ("Capris", ("capri", "crop")),
        ("Athletic Shorts", ("running short", "training short", "athletic short")),
        ("Liner Shorts", ("liner short", "lined short")),
        ("Swim Trunks", ("swim trunk", "swim")),
        ("Sports Bras", ("sports-bra", "bra")),
        ("Dresses", ("dress",)),
        ("Skirts", ("skirt", "skort")),
        ("Vests", ("vest",)),
        ("Jackets", ("jacket",)),
    ]
    for label, needles in rules:
        if label in {"Jackets", "Vests"} and fallback_category != "Coats & Jackets":
            continue
        if label == "Skirts" and fallback_category != "Skirts":
            continue
        if label == "Dresses" and fallback_category != "Dresses":
            continue
        if any(needle in text for needle in needles):
            return label
    return fallback_category


def _keyword_values(title: str, keywords: list[str]) -> list[str]:
    title_lower = title.lower()
    return [
        keyword
        for keyword in keywords
        if keyword.lower().replace("™", "").strip() in title_lower
    ]


def _activities(title: str, category: str) -> list[str]:
    text = f"{title} {category}".lower()
    values: list[str] = []
    activity_rules = {
        "Running": ("run", "running"),
        "Training": ("train", "workout", "weightlifting"),
        "Yoga": ("yoga", "align", "mat"),
        "Golf": ("golf",),
        "Tennis": ("tennis", "court"),
        "Hiking": ("hike", "hiking"),
        "Swim": ("swim",),
        "Work": ("work", "office", "abc", "trouser"),
        "Casual": ("casual", "lounge", "soft jersey", "steady state"),
    }
    for label, needles in activity_rules.items():
        if any(needle in text for needle in needles):
            values.append(label)
    return values


def _panel_text_values(panel: dict[str, Any] | None) -> list[str]:
    values: list[str] = []
    if not isinstance(panel, dict):
        return values
    for section in panel.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for attribute in section.get("attributes") or []:
            if not isinstance(attribute, dict):
                continue
            text = str(attribute.get("text") or "").strip()
            if text:
                _append_unique(values, text)
            list_value = attribute.get("list")
            if isinstance(list_value, dict):
                title = str(list_value.get("title") or "").strip()
                items = [
                    str(item).strip()
                    for item in list_value.get("items") or []
                    if str(item).strip()
                ]
                if items:
                    label = f"{title}: {', '.join(items)}" if title else ", ".join(items)
                    _append_unique(values, label)
    return values


def _material_values(color_attributes: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for attribute in color_attributes:
        care = attribute.get("careAndContent")
        for value in _panel_text_values(care):
            if re.search(r"\d+\s*%|cotton|polyester|nylon|elastane|lycra|wool|modal|viscose", value, re.I):
                _append_unique(values, value)
    return values


def _innovation_values(color_attributes: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for attribute in color_attributes:
        fabric = attribute.get("fabricOrBenefits")
        if isinstance(fabric, dict):
            _append_unique(values, fabric.get("title"))
            _append_unique(values, _panel_text_values(fabric))
        _append_unique(values, _panel_text_values(attribute.get("featuresOrIngredients")))
        _append_unique(values, _panel_text_values(attribute.get("fitOrHowToUse")))
    return values


def _extract_next_data(html: str) -> dict[str, Any] | None:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        flags=re.S,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_json_ld(html_text: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html_text,
        flags=re.I | re.S,
    ):
        raw = html.unescape(match.group(1)).strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            values.append(parsed)
        elif isinstance(parsed, list):
            values.extend(item for item in parsed if isinstance(item, dict))
    return values


def _find_product_group(values: list[dict[str, Any]]) -> dict[str, Any] | None:
    for value in values:
        if value.get("@type") == "ProductGroup":
            return value
    return None


def _schema_availability(variant: dict[str, Any]) -> bool:
    offers = variant.get("offers")
    if isinstance(offers, dict):
        offers = [offers]
    if not isinstance(offers, list):
        return False
    return any(
        "InStock" in str(offer.get("availability", ""))
        for offer in offers
        if isinstance(offer, dict)
    )


def _schema_price(variant: dict[str, Any]) -> float | None:
    offers = variant.get("offers")
    if isinstance(offers, dict):
        offers = [offers]
    if not isinstance(offers, list):
        return None
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        try:
            return float(offer.get("price"))
        except (TypeError, ValueError):
            continue
    return None


def _schema_style_number(image: str) -> str:
    match = re.search(r"/([^/?]+)_\d+_", image)
    return match.group(1) if match else ""


def _apply_schema_details(product: dict[str, Any], product_group: dict[str, Any]) -> None:
    variants = product_group.get("hasVariant") or []
    if not isinstance(variants, list):
        variants = []

    by_color: dict[str, dict[str, Any]] = {}
    prices: list[float] = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        color = str(variant.get("color") or "").strip()
        image = _image_url(str(variant.get("image") or "").strip())
        available = _schema_availability(variant)
        price = _schema_price(variant)
        if price is not None:
            prices.append(price)
        if not color:
            continue
        row = by_color.setdefault(
            color,
            {
                "color": color,
                "image": image,
                "url": product.get("url", ""),
                "available": False,
            },
        )
        if image and not row.get("image"):
            row["image"] = image
        row["available"] = bool(row.get("available")) or available

    color_variants = list(by_color.values())
    available_colors = [item["color"] for item in color_variants if item["available"]]
    unavailable_colors = [
        item["color"] for item in color_variants if not item["available"]
    ]
    all_colors = [item["color"] for item in color_variants]
    image = _image_url(str(product_group.get("image") or "").strip())
    if image and not product.get("style_number"):
        product["style_number"] = _schema_style_number(image)
    if image:
        product["image"] = image
    elif color_variants:
        product["image"] = color_variants[0].get("image", product.get("image", ""))
    if color_variants:
        product["color_variants"] = color_variants
        product["available_colors"] = available_colors
        product["unavailable_colors"] = unavailable_colors
        product["all_colors"] = all_colors
        product["color"] = " / ".join(available_colors or all_colors)
        product["variant_count"] = max(1, len(color_variants))
        product["available"] = bool(available_colors)
    if prices:
        product["price_min"] = min(prices)
        product["price_max"] = max(prices)
        product["price_known"] = True


def _find_pdp_data(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        if isinstance(obj.get("colorAttributes"), list) and isinstance(
            obj.get("productCarousel"), list
        ):
            return obj
        for value in obj.values():
            found = _find_pdp_data(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_pdp_data(value)
            if found:
                return found
    return None


def _style_number(color_attributes: list[dict[str, Any]]) -> str:
    for attribute in color_attributes:
        style_color = str(attribute.get("styleColorId") or "").strip()
        if "-" in style_color:
            return style_color.split("-", 1)[0]
    return ""


def _image_url(url: str) -> str:
    if not url:
        return ""
    if "?" in url:
        return url
    return f"{url}?wid=240&hei=300&fmt=webp"


def _apply_pdp_details(product: dict[str, Any], pdp_data: dict[str, Any]) -> None:
    color_attributes = [
        item for item in pdp_data.get("colorAttributes") or [] if isinstance(item, dict)
    ]
    carousel = [
        item for item in pdp_data.get("productCarousel") or [] if isinstance(item, dict)
    ]

    color_variants: list[dict[str, Any]] = []
    available_colors: list[str] = []
    all_colors: list[str] = []
    for item in carousel:
        color = item.get("color") if isinstance(item.get("color"), dict) else {}
        color_name = str(color.get("name") or "").strip()
        images = item.get("imageInfo") or []
        image = _image_url(str(images[0]).strip() if images else "")
        if color_name:
            _append_unique(available_colors, color_name)
            _append_unique(all_colors, color_name)
            color_variants.append(
                {
                    "color": color_name,
                    "image": image,
                    "url": product.get("url", ""),
                    "available": True,
                }
            )

    materials = _material_values(color_attributes)
    innovations = _innovation_values(color_attributes)
    style_number = _style_number(color_attributes)
    product["style_number"] = style_number or product.get("style_number", "")
    product["available_colors"] = available_colors
    product["all_colors"] = all_colors
    product["color"] = " / ".join(available_colors)
    product["color_variants"] = color_variants
    product["image"] = color_variants[0]["image"] if color_variants else product.get("image", "")
    product["variant_count"] = max(1, len(color_variants))
    product["material_details"] = materials or product.get("material_details", [])
    product["material"] = " | ".join(product["material_details"])
    product["innovations"] = innovations


async def _enrich_product(client: httpx.AsyncClient, product: dict[str, Any]) -> dict[str, Any]:
    try:
        response = await client.get(product["url"])
        response.raise_for_status()
    except httpx.HTTPError:
        return product
    product_group = _find_product_group(_extract_json_ld(response.text))
    if product_group:
        _apply_schema_details(product, product_group)
    next_data = _extract_next_data(response.text)
    pdp_data = _find_pdp_data(next_data) if next_data else None
    if pdp_data:
        _apply_pdp_details(product, pdp_data)
    return product


def _normalize(url: str, lastmod: str | None = None) -> dict[str, Any] | None:
    parsed = _parse_product_url(url)
    if not parsed:
        return None
    segment = parsed["segment"]
    segment_lower = segment.lower()
    if _contains_any(segment_lower, EXCLUDED_SEGMENT_KEYWORDS):
        return None

    title = _title_from_slug(parsed["title_slug"])
    fallback_category = _fallback_category(segment, title)
    category = _website_category(segment, title, fallback_category)
    if category == "Other":
        return None

    audiences, audience_labels = _audience(segment)
    collections = _keyword_values(title, COLLECTION_KEYWORDS)
    fabrics = _keyword_values(title, FABRIC_KEYWORDS)
    activities = _activities(title, category)
    product_id = parsed["product_id"]
    material = ", ".join(fabrics)

    return {
        "id": f"lululemon:{product_id}",
        "source_id": product_id,
        "product_id": product_id,
        "brand": "lululemon",
        "brand_label": "lululemon",
        "source": BASE_URL,
        "title": title,
        "handle": parsed["title_slug"],
        "description": "",
        "category": category,
        "categories": [category],
        "subcategories": [],
        "collections": collections,
        "features": [],
        "shop_highlights": [],
        "activities": activities,
        "vendor": "lululemon athletica",
        "audiences": audiences,
        "audience_labels": audience_labels,
        "price_min": 0,
        "price_max": 0,
        "price_known": False,
        "available": True,
        "variant_count": 1,
        "color": "",
        "available_colors": [],
        "unavailable_colors": [],
        "all_colors": [],
        "tags": [segment],
        "image": "",
        "url": url,
        "material": material,
        "material_details": fabrics,
        "technical_features": [],
        "fabric_treatment": [],
        "construction": [],
        "innovations": [],
        "product_functions": [],
        "top_seller": False,
        "published_at": None,
        "updated_at": lastmod,
    }


async def scrape_lululemon_products() -> dict[str, Any]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    timeout = httpx.Timeout(60.0, connect=20.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        robots = await client.get(f"{BASE_URL}/robots.txt")
        robots.raise_for_status()
        response = await client.get(PRODUCT_SITEMAP_URL)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    products: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in root.findall(".//sm:url", SITEMAP_NS):
        loc = node.find("sm:loc", SITEMAP_NS)
        lastmod = node.find("sm:lastmod", SITEMAP_NS)
        if loc is None or not loc.text:
            continue
        normalized = _normalize(
            loc.text.strip(),
            lastmod.text.strip() if lastmod is not None and lastmod.text else None,
        )
        if not normalized or normalized["product_id"] in seen:
            continue
        seen.add(normalized["product_id"])
        products.append(normalized)
        if len(products) % 500 == 0:
            await asyncio.sleep(0)

    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(10)

        async def enrich_with_limit(product: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                return await _enrich_product(client, product)

        enriched: list[dict[str, Any]] = []
        for index in range(0, len(products), 100):
            batch = products[index : index + 100]
            enriched.extend(await asyncio.gather(*(enrich_with_limit(item) for item in batch)))
            await asyncio.sleep(0)
        products = enriched

    products.sort(key=lambda item: item["title"].lower())
    return {
        "source": BASE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "products": products,
        "collection_options": sorted(
            {
                collection
                for product in products
                for collection in product.get("collections", [])
            },
            key=str.lower,
        ),
    }
