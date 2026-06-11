import asyncio
import json
from pathlib import Path

import httpx

from app.scraper import (
    CATEGORY_COLLECTIONS,
    USER_AGENT,
    _fetch_collection_cards,
)

CACHE_PATH = Path(__file__).parent / "data" / "products.json"


async def main() -> None:
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    products = cache["products"]
    results = []

    async with httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
        timeout=30,
        follow_redirects=True,
    ) as client:
        for category, collections in CATEGORY_COLLECTIONS.items():
            website_ids = set()
            for collection, _audience in collections:
                website_ids.update(
                    await _fetch_collection_cards(client, collection)
                )
            cache_ids = {
                str(product["id"])
                for product in products
                if category
                in (
                    product.get("categories")
                    or [product.get("category", "Uncategorized")]
                )
            }
            results.append(
                {
                    "category": category,
                    "website": len(website_ids),
                    "cache": len(cache_ids),
                    "missing_ids": sorted(website_ids - cache_ids),
                    "extra_ids": sorted(cache_ids - website_ids),
                }
            )

    print(
        json.dumps(
            {
                "cache_products": len(products),
                "categories_match": all(
                    not row["missing_ids"] and not row["extra_ids"]
                    for row in results
                ),
                "categories": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
