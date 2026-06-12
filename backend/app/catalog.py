import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .arcteryx_scraper import scrape_arcteryx_products
from .rhone_scraper import scrape_rhone_products
from .scraper import scrape_strauss_products

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CACHE_PATH = DATA_DIR / "products.json"


async def scrape_products() -> dict[str, Any]:
    cached = load_cache() or {}
    cached_products = cached.get("products", [])
    cached_sources = {
        source.get("brand"): source
        for source in cached.get("sources", [])
        if source.get("brand")
    }
    scraped_results = await asyncio.gather(
        scrape_strauss_products(),
        scrape_rhone_products(),
        scrape_arcteryx_products(),
        return_exceptions=True,
    )
    brand_sources = (
        ("strauss", "Strauss", "https://us.strauss.com"),
        ("rhone", "Rhone", "https://www.rhone.com"),
        ("arcteryx", "Arc'teryx", "https://arcteryx.com/us/en"),
    )
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for (brand, label, source_url), result in zip(
        brand_sources, scraped_results
    ):
        if not isinstance(result, Exception):
            results.append(result)
            continue

        fallback_products = [
            product
            for product in cached_products
            if product.get("brand") == brand
        ]
        if not fallback_products:
            errors.append(f"{label}: {result}")
            continue
        cached_source = cached_sources.get(brand, {})
        results.append(
            {
                "source": cached_source.get("url", source_url),
                "scraped_at": cached_source.get("scraped_at")
                or cached.get("scraped_at"),
                "product_count": len(fallback_products),
                "products": fallback_products,
                "cached_fallback": True,
            }
        )
        errors.append(f"{label} used cached data: {result}")

    if not results:
        raise RuntimeError("; ".join(errors) or "No catalog source returned data")

    products = [
        product
        for result in results
        for product in result.get("products", [])
    ]
    products.sort(
        key=lambda item: (
            item.get("brand_label", "").lower(),
            item.get("title", "").lower(),
        )
    )
    payload = {
        "source": [result["source"] for result in results],
        "sources": [
            {
                "brand": result["products"][0]["brand"],
                "label": result["products"][0]["brand_label"],
                "url": result["source"],
                "product_count": result["product_count"],
                "scraped_at": result["scraped_at"],
            }
            for result in results
            if result.get("products")
        ],
        "scrape_warnings": errors,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "products": products,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def load_cache() -> dict[str, Any] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def normalize_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r",\s*", value) if part.strip()]
