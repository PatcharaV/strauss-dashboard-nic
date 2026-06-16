import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

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
    "Hike": "trail/hike",
    "Trail Run": "trail/trail-run",
    "Rock": "climb/rock",
    "Boulder": "climb/boulder",
    "Alpine": "climb/alpine",
    "Freeride": "ski-snowboard/freeride",
    "Touring": "ski-snowboard/touring",
    "Resort": "ski-snowboard/resort",
    "Sun Protection": "sun-protection/wid-1jwro0gl",
    "Veilance": "veilance",
    "System_A": "system_a",
}


async def _listing(
    client: httpx.AsyncClient, slug: str, offset: int = 0, limit: int = 100
) -> dict[str, Any]:
    page_url = f"{BASE_URL}/c/{slug}"
    payload = {
        "browserUserId": "1",
        "country": "us",
        "filters": {},
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
    client: httpx.AsyncClient, slug: str
) -> list[dict[str, Any]]:
    first = await _listing(client, slug)
    products = list(first.get("productList") or [])
    total = int(first.get("filterBar", {}).get("resultCount", len(products)))
    for offset in range(100, total, 100):
        page = await _listing(client, slug, offset)
        products.extend(page.get("productList") or [])
        await asyncio.sleep(0.2)
    return products


def _extra_clothing_categories(product: dict[str, Any]) -> set[str]:
    title = str(product.get("marketingName", "")).lower()
    slug = str(product.get("slug", "")).lower()
    if "dress" in title or "skirt" in title or "dress" in slug or "skirt" in slug:
        return {"Dresses and Skirts"}
    return set()


def _normalize(
    product: dict[str, Any],
    audiences: set[str],
    categories: set[str],
    collections: set[str],
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
        "subcategories": [],
        "collections": sorted(collections),
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
        collections_by_id: dict[str, set[str]] = {}

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
                        categories_by_id.setdefault(product_id, set()).update(
                            extra_categories
                        )
                await asyncio.sleep(0.2)

    products = [
        _normalize(
            product,
            audiences_by_id.get(product_id, set()),
            categories_by_id.get(product_id, set()),
            collections_by_id.get(product_id, set()),
        )
        for product_id, product in products_by_id.items()
        if product_id in clothing_product_ids
    ]
    products.sort(key=lambda item: item["title"].lower())
    return {
        "source": BASE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "products": products,
    }
