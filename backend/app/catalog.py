import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .arcteryx_scraper import scrape_arcteryx_products
from .rhone_scraper import scrape_rhone_products
from .scraper import extract_product_functions, scrape_strauss_products

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CACHE_PATH = DATA_DIR / "products.json"
PERIOD_SEASON_MONTHS = {
    "JAN": "S",
    "FEB": "S",
    "MAR": "S",
    "APR": "S",
    "MAY": "S",
    "JUN": "S",
    "JUL": "F",
    "AUG": "F",
    "SEP": "F",
    "OCT": "F",
    "NOV": "F",
    "DEC": "F",
}
PERIOD_MONTH_ORDER = list(PERIOD_SEASON_MONTHS)
CLOTHING_CATEGORIES = {
    "strauss": {
        "Shirts",
        "Pants",
        "Outerwear",
        "Hoodies & Sweatshirts",
        "Shorts",
        "Leggings",
        "Thermal Layers",
    },
    "rhone": {
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
    },
    "arcteryx": {
        "Shell Jackets",
        "Insulated Jackets",
        "Base Layer",
        "Pants",
        "Fleece",
        "Shirts and Tops",
        "Shorts",
        "Vests",
        "Dresses and Skirts",
        "Collection Only",
    },
}


def _clothing_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clothing: list[dict[str, Any]] = []
    for product in products:
        allowed = CLOTHING_CATEGORIES.get(str(product.get("brand")), set())
        categories = set(
            product.get("categories")
            or [str(product.get("category", "Other"))]
        )
        matched_categories = sorted(categories & allowed)
        if not matched_categories:
            continue
        shop_highlights = [
            str(highlight)
            for highlight in product.get("shop_highlights", [])
            if str(highlight).strip()
        ]
        features = [
            str(feature)
            for feature in product.get("features", [])
            if str(feature).strip()
        ]
        if product.get("top_seller") and "Topseller" not in shop_highlights:
            shop_highlights.append("Topseller")
        clothing.append(
            {
                **product,
                "category": matched_categories[0],
                "categories": matched_categories,
                "features": features,
                "shop_highlights": shop_highlights,
                "top_seller": "Topseller" in shop_highlights,
                "product_functions": product.get("product_functions")
                or extract_product_functions(
                    product.get("title", ""),
                    product.get("description", ""),
                    product.get("tags", []),
                    product.get("material", ""),
                ),
                "audiences": [
                    audience
                    for audience in product.get("audiences", [])
                    if audience not in {"footwear", "gear-accessories"}
                ],
                "audience_labels": [
                    label
                    for value, label in zip(
                        product.get("audiences", []),
                        product.get("audience_labels", []),
                    )
                    if value not in {"footwear", "gear-accessories"}
                ],
            }
        )
    return clothing


def _period_season_codes(scrape_period: dict[str, Any] | None) -> list[str]:
    if not scrape_period:
        return []
    month_from = str(
        scrape_period.get("month_from") or scrape_period.get("month") or ""
    ).upper()
    month_to = str(
        scrape_period.get("month_to") or scrape_period.get("month") or month_from
    ).upper()
    year = scrape_period.get("year")
    if (
        month_from not in PERIOD_SEASON_MONTHS
        or month_to not in PERIOD_SEASON_MONTHS
        or not year
    ):
        return []

    start = PERIOD_MONTH_ORDER.index(month_from)
    end = PERIOD_MONTH_ORDER.index(month_to)
    if start > end:
        start, end = end, start
    seasons = {
        f"{PERIOD_SEASON_MONTHS[month]}{int(year) % 100:02d}"
        for month in PERIOD_MONTH_ORDER[start : end + 1]
    }
    return sorted(seasons)


def _filter_period_products(
    products: list[dict[str, Any]],
    brand: str,
    scrape_period: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if brand != "arcteryx":
        return products
    season_codes = _period_season_codes(scrape_period)
    if not season_codes:
        return products
    return [
        product
        for product in products
        if product.get("season_code") in season_codes
    ]


def _normalize_strauss_categories(product: dict[str, Any]) -> dict[str, Any]:
    if product.get("brand") != "strauss":
        return product

    title = str(product.get("title", "")).lower()
    raw_categories = list(
        product.get("categories")
        or [str(product.get("category", "Other"))]
    )
    categories = [
        category
        for category in raw_categories
        if category != "Thermal Layers" or len(raw_categories) == 1
    ]
    subcategories = [
        subcategory
        for subcategory in product.get("subcategories", [])
        if subcategory not in {"Men's Thermal Layers", "Women's Thermal Layers"}
    ]

    categories = categories or ["Other"]
    features = [
        feature
        for feature in product.get("features", [])
        if feature
    ]
    if "Thermal Layers" in features and categories == ["Other"]:
        categories = ["Thermal Layers"]
        if "pant" in title:
            subcategories = ["Thermal Pants"]
    shop_highlights = [
        highlight
        for highlight in product.get("shop_highlights", [])
        if highlight
    ]
    if product.get("top_seller") and "Topseller" not in shop_highlights:
        shop_highlights.append("Topseller")
    return {
        **product,
        "category": categories[0],
        "categories": categories,
        "subcategories": subcategories,
        "features": features,
        "shop_highlights": shop_highlights,
        "top_seller": "Topseller" in shop_highlights,
    }


def _normalize_cached_payload(payload: dict[str, Any]) -> dict[str, Any]:
    products = _clothing_products(
        [_normalize_strauss_categories(product) for product in payload.get("products", [])]
    )
    return {
        **payload,
        "products": products,
        "product_count": len(products),
    }


async def scrape_products(scrape_period: dict[str, Any] | None = None) -> dict[str, Any]:
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
        scrape_arcteryx_products(scrape_period=scrape_period),
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
            result["products"] = _clothing_products(result.get("products", []))
            result["product_count"] = len(result["products"])
            results.append(result)
            continue

        fallback_products = _clothing_products(
            [
                product
                for product in cached_products
                if product.get("brand") == brand
            ]
        )
        fallback_products = _filter_period_products(
            fallback_products, brand, scrape_period
        )
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
                "collection_options": cached_source.get("collection_options", []),
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
                "collection_options": result.get("collection_options", []),
                "period_filter": result.get("period_filter", {}),
            }
            for result in results
            if result.get("products")
        ],
        "scrape_warnings": errors,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "scrape_period": scrape_period or {},
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
        return _normalize_cached_payload(
            json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, OSError):
        return None


def normalize_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r",\s*", value) if part.strip()]
