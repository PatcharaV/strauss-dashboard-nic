import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from .scraper import extract_product_functions

BASE_URL = "https://arcteryx.com/us/en"
API_URL = "https://arcteryx.com/api/catalog.getProductListingPage"
AUDIENCES = {"men": "mens", "women": "womens"}
CLOTHING_CATEGORY_SLUGS = {
    "Shell Jackets": "shell-jackets",
    "Insulated Jackets": "insulated-jackets",
    "Base Layer": "base-layer",
    "Pants": "pants",
    "Fleece": "fleece",
    "Shirts and Tops": "shirts-and-tops",
    "Shorts": "shorts",
    "Vests": "vests",
}
COLLECTION_SLUGS = {
    "Veilance": "veilance",
    "Arc'teryx PRO": "professional-use",
    "Mountain bike": "mountain-bike/wid-6j83rq6l",
}
STATIC_COLLECTIONS = ["Walk Gently"]
ACTIVITY_SLUGS = {
    "Trail Run": "trail/trail-run",
    "Hike": "trail/hike",
    "Alpine": "climb/alpine",
    "Rock": "climb/rock",
    "Boulder": "climb/boulder",
    "Ski & Snowboard": "ski-snowboard",
}
SUBCATEGORY_FILTERS = {
    "Hardshells": "Hardshell",
    "Windshells": "Windshell",
    "Softshells": "Softshell",
    "Down Insulation": "Down Fill",
    "Synthetic Insulation": "Synthetic Fill",
    "T-Shirts": "T-Shirts",
    "Long Sleeves": "Long Sleeve",
    "Tank Tops": "Tank Tops",
}
FEATURE_SLUGS = {
    "New Arrivals": "new-arrivals",
}
FEATURE_FILTERS = {
    "Summer Essentials": "Sun Protection",
    "Light Layers": "Lightweight",
    "Waterproof Gear": "GORE-TEX® (Waterproof)",
}


async def _listing(
    client: httpx.AsyncClient,
    slug: str,
    offset: int = 0,
    limit: int = 100,
    filters: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    page_url = f"{BASE_URL}/c/{slug}"
    payload = {
        "browserUserId": "1",
        "country": "us",
        "filters": filters or {},
        "language": "en",
        "limit": limit,
        "offset": offset,
        "refUrl": "",
        "slug": slug,
        "sort": "",
        "url": page_url,
    }
    encoded = quote(json.dumps({"json": payload}, separators=(",", ":")))
    response = await client.get(
        f"{API_URL}?input={encoded}",
        headers={"Referer": page_url},
    )
    response.raise_for_status()
    return response.json()["result"]["data"]["json"]


async def _all_listing_products(
    client: httpx.AsyncClient, slug: str, filters: dict[str, list[str]] | None = None
) -> list[dict[str, Any]]:
    first = await _listing(client, slug, filters=filters)
    products = list(first.get("productList") or [])
    total = int(first.get("filterBar", {}).get("resultCount", len(products)))
    for offset in range(100, total, 100):
        page = await _listing(client, slug, offset, filters=filters)
        products.extend(page.get("productList") or [])
        await asyncio.sleep(0.2)
    return products


def _feature_values(features: list[dict[str, Any]], label: str) -> list[str]:
    for feature in features:
        if str(feature.get("label", "")).strip().lower() == label.lower():
            return [
                str(value).strip()
                for value in feature.get("value", [])
                if str(value).strip()
            ]
    return []


async def _product_details(
    client: httpx.AsyncClient, slug: str
) -> dict[str, list[str]]:
    response = await client.get(f"{BASE_URL}/shop/{slug}")
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return {}
    data = json.loads(script.string)
    product_json = data.get("props", {}).get("pageProps", {}).get("product")
    if not product_json:
        return {}
    product = json.loads(product_json)
    feature_groups = product.get("features") or []
    materials = [
        str(material).strip()
        for material in product.get("materials", [])
        if str(material).strip().lower().startswith("body:")
    ]
    return {
        "material_details": materials,
        "technical_features": _feature_values(feature_groups, "Technical features"),
        "fabric_treatment": _feature_values(feature_groups, "Fabric treatment"),
        "construction": _feature_values(feature_groups, "Construction"),
    }


def _extra_clothing_categories(product: dict[str, Any]) -> set[str]:
    title = str(product.get("marketingName", "")).lower()
    slug = str(product.get("slug", "")).lower()
    blocked_terms = (
        "pack",
        "shoe",
        "boot",
        "sock",
        "glove",
        "cap",
        "hat",
        "beanie",
        "chalk",
        "harness",
    )
    if any(term in title or term in slug for term in blocked_terms):
        return set()
    categories: set[str] = set()
    if "dress" in title or "skirt" in title or "dress" in slug or "skirt" in slug:
        categories.add("Dresses and Skirts")
    if "pant" in title or "bib" in title or "pant" in slug or "bib" in slug:
        categories.add("Pants")
    if "short" in title or "short" in slug:
        categories.add("Shorts")
    if "vest" in title or "vest" in slug:
        categories.add("Vests")
    if "jacket" in title or "shell" in title or "jacket" in slug or "shell" in slug:
        categories.add("Shell Jackets")
    if "hoody" in title or "hoodie" in title or "hoody" in slug or "hoodie" in slug:
        categories.add("Insulated Jackets")
    if "shirt" in title or "tee" in title or "tank" in title:
        categories.add("Shirts and Tops")
    return categories


def _extra_clothing_subcategories(product: dict[str, Any]) -> set[str]:
    title = str(product.get("marketingName", "")).lower()
    slug = str(product.get("slug", "")).lower()
    subcategories: set[str] = set()
    if "dress" in title or "dress" in slug:
        subcategories.add("Dresses")
    if "skirt" in title or "skirt" in slug:
        subcategories.add("Skirts")
    return subcategories


def _normalize(
    product: dict[str, Any],
    audiences: set[str],
    categories: set[str],
    subcategories: set[str],
    collections: set[str],
    activities: set[str],
    features: set[str],
) -> dict[str, Any]:
    price = product.get("priceRange") or {}
    colours = product.get("colourOptions") or []
    selected = next(
        (colour for colour in colours if colour.get("selected")),
        colours[0] if colours else {},
    )
    badges = [
        badge
        for colour in colours
        for badge in (colour.get("badges") or [])
    ]
    audience_list = sorted(audiences)
    category_list = sorted(categories) or ["Other"]
    slug = str(product.get("slug", ""))
    image = selected.get("image") or selected.get("thumbnail") or {}
    title = str(product.get("marketingName", "")).strip()
    description = str(product.get("shortDescription", "")).strip()
    tags = sorted(
        {
            str(badge.get("label", ""))
            for badge in badges
            if badge.get("label")
        }
    )
    return {
        "id": f"arcteryx:{product.get('id', slug)}",
        "source_id": str(product.get("id", slug)),
        "product_id": str(product.get("id", slug)),
        "brand": "arcteryx",
        "brand_label": "Arc'teryx",
        "source": BASE_URL,
        "title": title,
        "handle": slug,
        "description": description,
        "category": category_list[0],
        "categories": category_list,
        "subcategories": sorted(subcategories),
        "collections": sorted(collections),
        "activities": sorted(activities),
        "features": sorted(features),
        "vendor": "Arc'teryx",
        "audiences": audience_list,
        "audience_labels": [audience.title() for audience in audience_list],
        "price_min": float(
            price.get("minDiscountPrice") or price.get("regularPrice") or 0
        ),
        "price_max": float(
            price.get("maxDiscountPrice") or price.get("regularPrice") or 0
        ),
        "available": True,
        "variant_count": len(colours),
        "color": str(selected.get("label", "")),
        "tags": tags,
        "image": str(image.get("url", "")),
        "url": f"{BASE_URL}/shop/{slug}",
        "material": "",
        "material_details": [],
        "technical_features": [],
        "fabric_treatment": [],
        "construction": [],
        "product_functions": extract_product_functions(title, description, tags),
        "top_seller": any(
            badge.get("code") == "bestseller" for badge in badges
        ),
        "published_at": None,
        "updated_at": None,
    }


async def scrape_arcteryx_products() -> dict[str, Any]:
    headers = {
        "User-Agent": "MultiBrandCatalogDashboard/1.0 (+public product analytics)",
        "Accept": "application/json,text/plain,*/*",
    }
    timeout = httpx.Timeout(45.0, connect=15.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        robots = await client.get("https://arcteryx.com/robots.txt")
        robots.raise_for_status()

        products_by_id: dict[str, dict[str, Any]] = {}
        audiences_by_id: dict[str, set[str]] = {}
        categories_by_id: dict[str, set[str]] = {}
        subcategories_by_id: dict[str, set[str]] = {}
        collections_by_id: dict[str, set[str]] = {}
        activities_by_id: dict[str, set[str]] = {}
        features_by_id: dict[str, set[str]] = {}

        for audience, audience_slug in AUDIENCES.items():
            for product in await _all_listing_products(client, audience_slug):
                product_id = str(product.get("id", ""))
                if not product_id:
                    continue
                products_by_id.setdefault(product_id, product)
                audiences_by_id.setdefault(product_id, set()).add(audience)
            await asyncio.sleep(0.2)

        clothing_product_ids: set[str] = set()
        for audience, audience_slug in AUDIENCES.items():
            for category, category_slug in CLOTHING_CATEGORY_SLUGS.items():
                slug = f"{audience_slug}/{category_slug}"
                for product in await _all_listing_products(client, slug):
                    product_id = str(product.get("id", ""))
                    if not product_id:
                        continue
                    clothing_product_ids.add(product_id)
                    categories_by_id.setdefault(product_id, set()).add(category)
                await asyncio.sleep(0.2)

        for audience, audience_slug in AUDIENCES.items():
            for subcategory, facet in SUBCATEGORY_FILTERS.items():
                for product in await _all_listing_products(
                    client, audience_slug, {"sub_categories": [facet]}
                ):
                    product_id = str(product.get("id", ""))
                    if not product_id:
                        continue
                    if product_id in clothing_product_ids:
                        subcategories_by_id.setdefault(product_id, set()).add(
                            subcategory
                        )
                await asyncio.sleep(0.2)

        for audience, audience_slug in AUDIENCES.items():
            for collection, collection_slug in COLLECTION_SLUGS.items():
                slug = f"{audience_slug}/{collection_slug}"
                for product in await _all_listing_products(client, slug):
                    product_id = str(product.get("id", ""))
                    if not product_id:
                        continue
                    products_by_id.setdefault(product_id, product)
                    audiences_by_id.setdefault(product_id, set()).add(audience)
                    collections_by_id.setdefault(product_id, set()).add(collection)
                    extra_categories = _extra_clothing_categories(product)
                    if extra_categories:
                        clothing_product_ids.add(product_id)
                await asyncio.sleep(0.2)

        for audience, audience_slug in AUDIENCES.items():
            for activity, activity_slug in ACTIVITY_SLUGS.items():
                slug = f"{audience_slug}/{activity_slug}"
                for product in await _all_listing_products(client, slug):
                    product_id = str(product.get("id", ""))
                    if not product_id or product_id not in clothing_product_ids:
                        continue
                    activities_by_id.setdefault(product_id, set()).add(activity)
                await asyncio.sleep(0.2)

        for audience, audience_slug in AUDIENCES.items():
            for feature, feature_slug in FEATURE_SLUGS.items():
                slug = f"{audience_slug}/{feature_slug}"
                for product in await _all_listing_products(client, slug):
                    product_id = str(product.get("id", ""))
                    if not product_id or product_id not in clothing_product_ids:
                        continue
                    features_by_id.setdefault(product_id, set()).add(feature)
                await asyncio.sleep(0.2)

            for feature, facet in FEATURE_FILTERS.items():
                for product in await _all_listing_products(
                    client, audience_slug, {"sub_categories": [facet]}
                ):
                    product_id = str(product.get("id", ""))
                    if not product_id or product_id not in clothing_product_ids:
                        continue
                    features_by_id.setdefault(product_id, set()).add(feature)
                await asyncio.sleep(0.2)

    products = [
        _normalize(
            product,
            audiences_by_id.get(product_id, set()),
            categories_by_id.get(product_id, set()),
            subcategories_by_id.get(product_id, set()),
            collections_by_id.get(product_id, set()),
            activities_by_id.get(product_id, set()),
            features_by_id.get(product_id, set())
            | ({"Bestsellers"} if product.get("id") and any(
                badge.get("code") == "bestseller"
                for colour in product.get("colourOptions", [])
                for badge in (colour.get("badges") or [])
            ) else set()),
        )
        for product_id, product in products_by_id.items()
        if product_id in clothing_product_ids
    ]
    detail_semaphore = asyncio.Semaphore(8)

    async def enrich_details(
        details_client: httpx.AsyncClient, product: dict[str, Any]
    ) -> None:
        async with detail_semaphore:
            try:
                details = await _product_details(
                    details_client, str(product.get("handle", ""))
                )
            except (
                httpx.HTTPError,
                KeyError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                details = {}
            for key in (
                "material_details",
                "technical_features",
                "fabric_treatment",
                "construction",
            ):
                product[key] = details.get(key, [])
            product["material"] = " | ".join(product.get("material_details", []))

    async with httpx.AsyncClient(headers=headers, timeout=timeout) as details_client:
        await asyncio.gather(
            *(enrich_details(details_client, product) for product in products)
        )
    products.sort(key=lambda item: item["title"].lower())
    return {
        "source": BASE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "collection_options": sorted([*COLLECTION_SLUGS, *STATIC_COLLECTIONS]),
        "products": products,
    }
