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
    results = await asyncio.gather(
        scrape_strauss_products(),
        scrape_rhone_products(),
        scrape_arcteryx_products(),
    )
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
