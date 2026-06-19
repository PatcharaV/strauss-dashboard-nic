from collections import Counter
from statistics import mean
from typing import Any

from .scraper import extract_product_collections
from .scraper import extract_product_functions

SUBCATEGORY_PARENTS = {
    "T-Shirts": [
        "Shirts",
        "Shirts and Tops",
        "Tees",
        "Tees/Tanks",
        "Base Layer",
        "Collection Only",
    ],
    "Polos": ["Polos", "Shirts", "Shirts and Tops", "Sweaters", "Collection Only"],
    "Long Sleeves": ["Shirts", "Shirts and Tops", "Base Layer", "Collection Only"],
    "Overshirts": ["Shirts and Tops", "Collection Only"],
    "One Pieces": "Shirts and Tops",
    "Shirts": ["Shirts", "Shirts and Tops"],
    "Button Downs": "Shirts",
    "Button ups": "Shirts",
    "Short Sleeve Shirts": "Shirts",
    "Short sleeves": ["Shirts", "Tees", "Tees/Tanks"],
    "Long sleeves": ["Shirts", "Tees", "Tees/Tanks", "Midlayers"],
    "Work Shirts": "Shirts",
    "High-Vis Shirts": "Shirts",
    "Kids Shirts": "Shirts",
    "Work Pants": "Pants",
    "Cargo Pants": ["Pants", "Collection Only"],
    "Double-Front Pants": "Pants",
    "Jeans": "Pants",
    "Bibs, Coveralls & Overalls": "Pants",
    "Kids Pants": "Pants",
    "Thermal Pants": "Thermal Layers",
    "Bib Pants": ["Pants", "Collection Only"],
    "Joggers": ["Pants", "Fleece"],
    "Wide Leg Pants": "Pants",
    "Work Shorts": "Shorts",
    "Cargo Shorts": "Shorts",
    "Women's Shorts": "Shorts",
    "Half Tights": "Shorts",
    "Liner Shorts": "Shorts",
    "Skorts": "Shorts",
    "Softshell Jackets": "Outerwear",
    "Lightweight Jackets": "Outerwear",
    "Winter Jackets": "Outerwear",
    "Work Jackets": "Outerwear",
    "Vests": ["Outerwear", "Vests", "Collection Only"],
    "High-Vis Outerwear": "Outerwear",
    "Kids Jackets": "Outerwear",
    "Hoodies": [
        "Hoodies & Sweatshirts",
        "Shirts and Tops",
        "Fleece",
        "Midlayers",
        "Base Layer",
        "Collection Only",
    ],
    "Crewnecks": ["Hoodies & Sweatshirts", "Fleece"],
    "Full-Zip Sweatshirts": "Hoodies & Sweatshirts",
    "Women's Hoodies & Sweatshirts": "Hoodies & Sweatshirts",
    "Women's Leggings": "Leggings",
    "Leggings": ["Pants", "Leggings/Tights"],
    "Tank Tops": ["Shirts and Tops", "Tanks", "Tees/Tanks", "Collection Only"],
    "Base Layer Bottoms": "Base Layer",
    "Base Layers": "Base Layer",
    "Fleece": "Fleece",
    "Fleece Jackets": "Fleece",
    "Zip Necks": ["Fleece", "Base Layer"],
    "Dresses": ["Dresses and Skirts", "Dresses/Jumpsuits", "Collection Only"],
    "Skirts": ["Dresses and Skirts", "Skirts", "Collection Only"],
    "Down Insulation": "Insulated Jackets",
    "Synthetic Insulation": "Insulated Jackets",
    "Insulated Jackets": "Insulated Jackets",
    "Hardshells": ["Shell Jackets", "Pants"],
    "Softshells": ["Shell Jackets", "Insulated Jackets", "Pants", "Shorts"],
    "Windshells": "Shell Jackets",
    "Shell Jackets": "Shell Jackets",
    "Pants": ["Pants", "Collection Only"],
    "Lifestyle pants": "Pants",
    "Dress pants": "Pants",
    "Trousers": "Pants",
    "Shorts": ["Shorts", "Fleece", "Collection Only"],
    "Lined Shorts": "Shorts",
    "Lifestyle shorts": "Shorts",
    "Athletic shorts": "Shorts",
    "Pullovers": ["Midlayers", "Sweaters"],
    "Hoodies & pullovers": ["Midlayers", "Sweaters"],
    "Quarter Zips": "Midlayers",
    "Midlayers": "Midlayers",
    "Jackets": ["Blazers/Jackets", "Outerwear", "Midlayers", "Collection Only"],
    "Jackets & vests": ["Midlayers", "Outerwear"],
    "Blazers": "Blazers/Jackets",
    "Outerwear": "Outerwear",
    "Tanks": ["Tanks", "Tees/Tanks"],
    "Sports Bras": ["Bras", "Sports bras"],
    "Sweaters": "Sweaters",
    "Swim": "Swim",
    "Swimwear": "Swim",
    "Underwear": "Underwear",
    "Down Vests": "Vests",
    "Insulated Vests": "Vests",
    "Collection Apparel": "Collection Only",
}

MATERIAL_KEYWORDS = [
    "Cotton",
    "Nylon",
    "Polyester",
    "Elastane",
    "Polyamide",
    "Polyurethane",
    "Wool",
    "Merino",
    "Down",
    "GORE-TEX",
    "Cellulose",
    "Polyarylate",
    "Leather",
]

FEATURE_HIGHLIGHT_LABELS = {
    "best sellers": "Best Sellers",
    "bestsellers": "Best Sellers",
    "best seller": "Best Sellers",
    "new arrivals": "New Arrivals",
    "new arrival": "New Arrivals",
}


def _product_shop_highlights(product: dict[str, Any]) -> list[str]:
    highlights: list[str] = []
    seen: set[str] = set()

    for highlight in product.get("shop_highlights", []):
        label = str(highlight).strip()
        if not label:
            continue
        key = label.lower()
        if key not in seen:
            seen.add(key)
            highlights.append(label)

    for feature in product.get("features", []):
        label = FEATURE_HIGHLIGHT_LABELS.get(str(feature).strip().lower())
        if not label:
            continue
        key = label.lower()
        if key not in seen:
            seen.add(key)
            highlights.append(label)

    return highlights


def _product_collections(product: dict[str, Any]) -> list[str]:
    collections = product.get("collections")
    if isinstance(collections, list):
        return [str(item) for item in collections if str(item).strip()]
    if product.get("brand") == "strauss":
        return extract_product_collections(str(product.get("title", "")))
    return []


def _product_functions(product: dict[str, Any]) -> list[str]:
    functions = product.get("product_functions")
    if isinstance(functions, list):
        return [str(item) for item in functions if str(item).strip()]
    return extract_product_functions(
        product.get("title", ""),
        product.get("description", ""),
        product.get("tags", []),
        product.get("material", ""),
    )


def _material_text(product: dict[str, Any]) -> str:
    return " ".join(
        [
            str(product.get("material", "")),
            " ".join(product.get("material_details", [])),
        ]
    )


def _season_value(product: dict[str, Any]) -> str:
    return str(product.get("season_range") or "").strip()


def _visible_categories(
    product: dict[str, Any], selected_categories: set[str]
) -> list[str]:
    categories = list(
        product.get("categories")
        or [product.get("category", "Uncategorized")]
    )
    if selected_categories:
        categories = [category for category in categories if category in selected_categories]
    return categories or ["Uncategorized"]


def _visible_subcategories(
    product: dict[str, Any], selected_categories: set[str]
) -> list[str]:
    subcategories = list(product.get("subcategories", []))
    if selected_categories:
        subcategories = [
            subcategory
            for subcategory in subcategories
            if _subcategory_has_selected_parent(subcategory, selected_categories)
        ]
        if not subcategories:
            subcategories = _visible_categories(product, selected_categories)
    return subcategories


def _subcategory_has_selected_parent(
    subcategory: str, selected_categories: set[str]
) -> bool:
    parents = SUBCATEGORY_PARENTS.get(subcategory)
    if not parents:
        return False
    if isinstance(parents, str):
        return parents in selected_categories
    return bool(set(parents) & selected_categories)


def filter_products(
    products: list[dict[str, Any]],
    search: str | None = None,
    brands: list[str] | None = None,
    audiences: list[str] | None = None,
    collections: list[str] | None = None,
    activities: list[str] | None = None,
    features: list[str] | None = None,
    categories: list[str] | None = None,
    subcategories: list[str] | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    availability: str | None = None,
    top_seller: str | None = None,
    shop_highlight: str | None = None,
    material: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    selected_brands = set(brands or [])
    selected_audiences = set(audiences or [])
    selected_collections = set(collections or [])
    selected_activities = set(activities or [])
    selected_features = set(features or [])
    selected_categories = set(categories or [])
    selected_subcategories = set(subcategories or [])
    search_term = (search or "").strip().lower()
    color_term = (color or "").strip().lower()
    selected_season = (season or "").strip()

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
                    str(product.get("series_number", "")),
                    str(product.get("style_number", "")),
                    str(product.get("season_code", "")),
                    str(product.get("season_range", "")),
                    " ".join(product.get("audience_labels", [])),
                    " ".join(_product_collections(product)),
                    " ".join(product.get("features", [])),
                    " ".join(product.get("material_details", [])),
                    " ".join(product.get("technical_features", [])),
                    " ".join(product.get("fabric_treatment", [])),
                    " ".join(product.get("construction", [])),
                    " ".join(_product_functions(product)),
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
        if selected_activities and not (
            selected_activities & set(product.get("activities", []))
        ):
            return False
        if selected_features and not (
            selected_features & set(product.get("features", []))
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
        if color_term and color_term not in str(product.get("color", "")).lower():
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
        if shop_highlight and shop_highlight != "all":
            product_highlights = _product_shop_highlights(product)
            if shop_highlight == "none":
                if product_highlights:
                    return False
            elif shop_highlight not in product_highlights:
                return False
        material_text = _material_text(product)
        if material == "specified" and not material_text.strip():
            return False
        if material == "missing" and material_text.strip():
            return False
        if (
            material
            and material not in {"all", "specified", "missing"}
            and material.lower() not in material_text.lower()
        ):
            return False
        if selected_season and selected_season != "all":
            if _season_value(product) != selected_season:
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
    products: list[dict[str, Any]],
    source: Any,
    scraped_at: str | None,
    scrape_period: dict[str, Any] | None = None,
    selected_categories: list[str] | None = None,
) -> dict[str, Any]:
    selected_category_set = set(selected_categories or [])
    brand_counts = Counter(
        product.get("brand_label", "Unknown") for product in products
    )
    category_counts: Counter[str] = Counter()
    for product in products:
        category_counts.update(_visible_categories(product, selected_category_set))
    audience_counts: Counter[str] = Counter()
    for product in products:
        labels = product.get("audience_labels", [])
        for label in labels:
            audience_counts[label] += 1
    collection_counts: Counter[str] = Counter()
    for product in products:
        collection_counts.update(_product_collections(product))
    activity_counts: Counter[str] = Counter()
    for product in products:
        activity_counts.update(product.get("activities", []))
    subcategory_counts: Counter[str] = Counter()
    for product in products:
        subcategory_counts.update(
            _visible_subcategories(product, selected_category_set)
        )

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
        len(_visible_categories(product, selected_category_set))
        for product in products
    )
    multi_category_products = sum(
        len(_visible_categories(product, selected_category_set)) > 1
        for product in products
    )

    return {
        "source": source,
        "scraped_at": scraped_at,
        "scrape_period": scrape_period or {},
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
        "subcategories": _counter_rows(subcategory_counts),
        "collections": _counter_rows(collection_counts),
        "activities": _counter_rows(activity_counts),
        "products": [
            {
                **product,
                "category": _visible_categories(product, selected_category_set)[0],
                "categories": _visible_categories(product, selected_category_set),
                "subcategories": _visible_subcategories(
                    product, selected_category_set
                ),
                "collections": _product_collections(product),
                "activities": product.get("activities", []),
                "product_functions": _product_functions(product),
                "shop_highlights": _product_shop_highlights(product),
            }
            for product in products
        ],
    }


def build_options(
    products: list[dict[str, Any]],
    selected_categories: list[str] | None = None,
) -> dict[str, Any]:
    prices = [float(product.get("price_min", 0)) for product in products]
    selected_category_set = set(selected_categories or [])
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
        "activities": sorted(
            {
                activity
                for product in products
                for activity in product.get("activities", [])
            },
            key=str.lower,
        ),
        "features": sorted(
            {
                feature
                for product in products
                for feature in product.get("features", [])
            },
            key=str.lower,
        ),
        "shop_highlights": sorted(
            {
                highlight
                for product in products
                for highlight in _product_shop_highlights(product)
            },
            key=str.lower,
        ),
        "material_keywords": [
            keyword
            for keyword in MATERIAL_KEYWORDS
            if any(
                keyword.lower() in _material_text(product).lower()
                for product in products
            )
        ],
        "seasons": sorted(
            {
                _season_value(product)
                for product in products
                if _season_value(product)
            },
            key=str.lower,
        ),
        "colors": sorted(
            {
                str(product.get("color", "")).strip()
                for product in products
                if str(product.get("color", "")).strip()
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
                if not selected_category_set
                or _subcategory_has_selected_parent(
                    subcategory, selected_category_set
                )
            }
        ),
        "price": {
            "min": min(prices, default=0),
            "max": max(prices, default=0),
        },
    }
