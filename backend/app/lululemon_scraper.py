import asyncio
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
        "product_functions": [],
        "top_seller": False,
        "published_at": None,
        "updated_at": lastmod,
    }


async def scrape_lululemon_products() -> dict[str, Any]:
    headers = {
        "User-Agent": "MultiBrandCatalogDashboard/1.0 (+public sitemap analytics)",
        "Accept": "application/xml,text/xml,*/*",
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
