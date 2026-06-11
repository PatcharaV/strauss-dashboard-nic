from collections import Counter
from statistics import mean
from typing import Any

from .scraper import COLLECTIONS


def filter_products(
    products: list[dict[str, Any]],
    search: str | None = None,
    audiences: list[str] | None = None,
    categories: list[str] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    availability: str | None = None,
    top_seller: str | None = None,
    material: str | None = None,
) -> list[dict[str, Any]]:
    selected_audiences = set(audiences or [])
    selected_categories = set(categories or [])
    search_term = (search or "").strip().lower()

    def matches(product: dict[str, Any]) -> bool:
        if search_term:
            searchable_text = " ".join(
                [
                    str(product.get("title", "")),
                    " ".join(
                        product.get("categories")
                        or [str(product.get("category", ""))]
                    ),
                    str(product.get("material", "")),
                    str(product.get("color", "")),
                    " ".join(product.get("audience_labels", [])),
                ]
            ).lower()
            if search_term not in searchable_text:
                return False
        if selected_audiences and not (
            selected_audiences & set(product.get("audiences", []))
        ):
            return False
        product_categories = set(
            product.get("categories")
            or [product.get("category", "Uncategorized")]
        )
        if selected_categories and not (selected_categories & product_categories):
            return False
        price = float(product.get("price_min", 0))
        if min_price is not None and price < min_price:
            return False
        if max_price is not None and price > max_price:
            return False
        if availability == "available" and not product.get("available"):
            return False
        if availability == "unavailable" and product.get("available"):
            return False
        if top_seller == "yes" and not product.get("top_seller"):
            return False
        if top_seller == "no" and product.get("top_seller"):
            return False
        if material == "specified" and not product.get("material"):
            return False
        if material == "missing" and product.get("material"):
            return False
        return True

    return [product for product in products if matches(product)]


def _counter_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"name": name, "value": value}
        for name, value in sorted(
            counter.items(), key=lambda item: (-item[1], item[0].lower())
        )
    ]


def build_dashboard(
    products: list[dict[str, Any]], source: str, scraped_at: str | None
) -> dict[str, Any]:
    category_counts: Counter[str] = Counter()
    for product in products:
        category_counts.update(
            product.get("categories")
            or [product.get("category", "Uncategorized")]
        )
    audience_counts: Counter[str] = Counter()
    for product in products:
        for audience in product.get("audiences", []):
            audience_counts[COLLECTIONS.get(audience, audience.title())] += 1

    prices = [float(product.get("price_min", 0)) for product in products]
    available_count = sum(bool(product.get("available")) for product in products)
    collection_memberships = sum(
        len(product.get("audiences", [])) for product in products
    )
    multi_collection_products = sum(
        len(product.get("audiences", [])) > 1 for product in products
    )
    category_memberships = sum(
        len(
            product.get("categories")
            or [product.get("category", "Uncategorized")]
        )
        for product in products
    )
    multi_category_products = sum(
        len(
            product.get("categories")
            or [product.get("category", "Uncategorized")]
        )
        > 1
        for product in products
    )

    return {
        "source": source,
        "scraped_at": scraped_at,
        "summary": {
            "total_products": len(products),
            "categories": len(category_counts),
            "average_price": round(mean(prices), 2) if prices else 0,
            "available_products": available_count,
            "collection_memberships": collection_memberships,
            "multi_collection_products": multi_collection_products,
            "overlap_memberships": collection_memberships - len(products),
            "category_memberships": category_memberships,
            "multi_category_products": multi_category_products,
            "category_overlap_memberships": category_memberships - len(products),
            "availability_rate": round(
                available_count / len(products) * 100, 1
            )
            if products
            else 0,
        },
        "audiences": _counter_rows(audience_counts),
        "categories": _counter_rows(category_counts),
        "products": products,
    }


def build_options(products: list[dict[str, Any]]) -> dict[str, Any]:
    prices = [float(product.get("price_min", 0)) for product in products]
    return {
        "audiences": [
            {"value": key, "label": label} for key, label in COLLECTIONS.items()
        ],
        "categories": sorted(
            {
                category
                for product in products
                for category in (
                    product.get("categories")
                    or [product.get("category", "Uncategorized")]
                )
            }
        ),
        "price": {
            "min": min(prices, default=0),
            "max": max(prices, default=0),
        },
    }
