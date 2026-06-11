import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from .scraper import _extract_material, _plain_text

BASE_URL = "https://www.rhone.com"
CATALOG_URL = "https://rhone.myshopify.com"
AUDIENCE_COLLECTIONS = {
    "men": "mens-view-all",
    "women": "womens-view-all",
}
TOP_SELLER_COLLECTIONS = ("mens-best-sellers", "womens-best-sellers")
PAGE_SIZE = 250


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
    audience_list = sorted(audiences)
    return {
        "id": f"rhone:{product.get('id', handle)}",
        "source_id": str(product.get("id", handle)),
        "product_id": str(product.get("id", handle)),
        "brand": "rhone",
        "brand_label": "Rhone",
        "source": BASE_URL,
        "title": str(product.get("title", "")).strip(),
        "handle": handle,
        "description": _plain_text(html),
        "category": category,
        "categories": [category],
        "subcategories": [],
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
        "material": _extract_material(html),
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

    products = [
        _normalize(
            product,
            audiences_by_handle.get(handle, set()),
            handle in top_seller_handles,
        )
        for handle, product in products_by_handle.items()
    ]
    products.sort(key=lambda item: item["title"].lower())
    return {
        "source": BASE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "products": products,
    }
