from collections import Counter
from statistics import mean
from typing import Any

from .scraper import extract_product_collections


def _product_collections(product: dict[str, Any]) -> list[str]:
    collections = product.get("collections")
    if isinstance(collections, list):
        return [str(item) for item in collections if str(item).strip()]
    if product.get("brand") == "strauss":
        return extract_product_collections(str(product.get("title", "")))
    return []

def filter_products(
    products: list[dict[str, Any]],
    search: str | None = None,
    brands: list[str] | None = None,
    audiences: list[str] | None = None,
    collections: list[str] | None = None,
    categories: list[str] | None = None,
    subcategories: list[str] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    availability: str | None = None,
    top_seller: str | None = None,
    material: str | None = None,
) -> list[dict[str, Any]]:
    selected_brands = set(brands or [])
    selected_audiences = set(audiences or [])
    selected_collections = set(collections or [])
    selected_categories = set(categories or [])
    selected_subcategories = set(subcategories or [])
    search_term = (search or "").strip().lower()

    def matches(product: dict[str, Any]) -> bool:
        if search_term:
            searchable_text = " ".join(
                [
                    str(product.get("title", "")),
                    str(product.get("brand_label", "")),
                    " ".join(
                        product.get("categories")
                        or [str(product.get("category", ""))]
                    ),
                    " ".join(product.get("subcategories", [])),
                    str(product.get("material", "")),
                    str(product.get("color", "")),
                    " ".join(product.get("audience_labels", [])),
                    " ".join(_product_collections(product)),
                ]
            ).lower()
            if search_term not in searchable_text:
                return False
        if selected_brands and product.get("brand") not in selected_brands:
            return False
        if selected_audiences and not (
            selected_audiences & set(product.get("audiences", []))
        ):
            return False
        if selected_collections and not (
            selected_collections & set(_product_collections(product))
        ):
            return False
        product_categories = set(
            product.get("categories")
            or [product.get("category", "Uncategorized")]
        )
        if selected_categories and not (selected_categories & product_categories):
            return False
        if selected_subcategories and not (
            selected_subcategories & set(product.get("subcategories", []))
        ):
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
    products: list[dict[str, Any]], source: Any, scraped_at: str | None
) -> dict[str, Any]:
    brand_counts = Counter(
        product.get("brand_label", "Unknown") for product in products
    )
    category_counts: Counter[str] = Counter()
    for product in products:
        category_counts.update(
            product.get("categories")
            or [product.get("category", "Uncategorized")]
        )
    audience_counts: Counter[str] = Counter()
    for product in products:
        labels = product.get("audience_labels", [])
        for label in labels:
            audience_counts[label] += 1
    collection_counts: Counter[str] = Counter()
    for product in products:
        collection_counts.update(_product_collections(product))

    prices = [float(product.get("price_min", 0)) for product in products]
    available_count = sum(bool(product.get("available")) for product in products)
    collection_memberships = sum(
        len(_product_collections(product)) for product in products
    )
    named_collection_products = sum(
        bool(_product_collections(product)) for product in products
    )
    multi_collection_products = sum(
        len(_product_collections(product)) > 1 for product in products
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
            "brands": len(brand_counts),
            "categories": len(category_counts),
            "average_price": round(mean(prices), 2) if prices else 0,
            "available_products": available_count,
            "collection_memberships": collection_memberships,
            "named_collection_products": named_collection_products,
            "unassigned_collection_products": len(products)
            - named_collection_products,
            "multi_collection_products": multi_collection_products,
            "overlap_memberships": collection_memberships
            - named_collection_products,
            "category_memberships": category_memberships,
            "multi_category_products": multi_category_products,
            "category_overlap_memberships": category_memberships - len(products),
            "availability_rate": round(
                available_count / len(products) * 100, 1
            )
            if products
            else 0,
        },
        "brands": _counter_rows(brand_counts),
        "audiences": _counter_rows(audience_counts),
        "categories": _counter_rows(category_counts),
        "collections": _counter_rows(collection_counts),
        "products": [
            {**product, "collections": _product_collections(product)}
            for product in products
        ],
    }


def build_options(products: list[dict[str, Any]]) -> dict[str, Any]:
    prices = [float(product.get("price_min", 0)) for product in products]
    return {
        "brands": [
            {"value": brand, "label": label}
            for brand, label in sorted(
                {
                    (
                        product.get("brand", "unknown"),
                        product.get("brand_label", "Unknown"),
                    )
                    for product in products
                },
                key=lambda item: item[1].lower(),
            )
        ],
        "audiences": [
            {"value": value, "label": label}
            for value, label in sorted(
                {
                    (value, label)
                    for product in products
                    for value, label in zip(
                        product.get("audiences", []),
                        product.get("audience_labels", []),
                    )
                },
                key=lambda item: item[1].lower(),
            )
        ],
        "collections": sorted(
            {
                collection
                for product in products
                for collection in _product_collections(product)
            },
            key=str.lower,
        ),
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
        "subcategories": sorted(
            {
                subcategory
                for product in products
                for subcategory in product.get("subcategories", [])
            }
        ),
        "price": {
            "min": min(prices, default=0),
            "max": max(prices, default=0),
        },
    }
