import asyncio
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://us.strauss.com"
USER_AGENT = "StraussDashboard/1.0 (+local product analytics dashboard)"
PAGE_SIZE = 250
REQUEST_DELAY_SECONDS = 0.65
MAX_COLLECTION_PAGES = 60
MAX_RETRIES = 5

COLLECTIONS = {
    "men": "Men",
    "women": "Women",
    "kids": "Kids",
}
PRODUCT_COLLECTION_FALLBACK_PATTERNS = (
    (r"\be\.s\.\s*motion\s+2020\b", "e.s.motion 2020"),
    (r"\be\.s\.\s*motion\s+ten\b", "e.s.motion ten"),
    (r"\be\.s\.\s*e:pic\b", "e.s.e:pic"),
    (r"\be\.s\.\s*t:aktik\b", "e.s.t:aktik"),
    (r"\be\.s\.\s*iconic\b", "e.s.iconic"),
    (r"\be\.s\.\s*ambition\b", "e.s.ambition"),
    (r"\be\.s\.\s*concrete\b", "e.s.concrete"),
    (r"\be\.s\.\s*vintage\b", "e.s.vintage"),
    (r"\be\.s\.\s*motion\b(?!\s+(?:2020|ten))", "e.s.motion"),
    (r"\be\.s\.\s*trail\b", "e.s.trail"),
)
COLLABORATION_COLLECTION_PATTERNS = (
    (
        r"\bSTRAUSS\s+x\s+STUNTMEN'?S\s+ASSOCIATION\b",
        "Strauss x Stuntmen's Association",
    ),
    (r"\bSTRAUSS\s+x\s+1620\b", "Strauss x 1620"),
    (r"\bLA\s+FC\b", "Strauss x LA FC"),
)
PRODUCT_FUNCTION_PATTERNS = (
    (r"\bbreathable\b|\bventilat(?:ed|ion)\b", "Breathable"),
    (r"\b4[- ]?way stretch\b|\bfour[- ]?way stretch\b", "4-way stretch"),
    (r"\beasy care\b", "Easy care"),
    (r"\beasy wear\b", "Easy wear"),
    (r"\bshape retention\b|\bretains? (?:its )?shape\b", "Shape retention"),
    (r"\bmoisture[- ]?wicking\b|\bwicks? moisture\b", "Moisture-wicking"),
    (r"\bquick[- ]?dry(?:ing)?\b|\bdries quickly\b", "Quick-drying"),
    (r"\bwater[- ]?repellent\b|\brepels water\b", "Water-repellent"),
    (r"\bwaterproof\b", "Waterproof"),
    (r"\bwindproof\b|\bwind resistant\b", "Windproof"),
    (r"\bupf\s*\d*\+?\b|\bsun protection\b", "UPF protection"),
    (r"\blightweight\b", "Lightweight"),
    (r"\bdurable\b|\bdurability\b", "Durable"),
    (r"\babrasion[- ]?resistant\b", "Abrasion-resistant"),
    (r"\binsulat(?:ed|ion)\b", "Insulated"),
    (r"\bthermal\b", "Thermal"),
    (r"\bstretch\b|\belastane\b|\bspandex\b", "Stretch"),
)
TOP_SELLERS_COLLECTION = "top-sellers"
CATEGORY_COLLECTIONS = {
    "Shirts": (
        ("shirts", "men"),
        ("shirts-women", "women"),
        ("shirts-kids", "kids"),
    ),
    "Pants": (
        ("pants-men", "men"),
        ("pants-women", "women"),
        ("pants-kids", "kids"),
        ("bibs-coveralls-overalls", "men"),
        ("bibs-coveralls-overalls-women", "women"),
    ),
    "Outerwear": (
        ("outerwear", "men"),
        ("outerwear-women", "women"),
        ("kids-jackets", "kids"),
    ),
    "Hoodies & Sweatshirts": (
        ("hoodies-sweatshirts", "men"),
        ("hoodies-sweatshirts-women", "women"),
    ),
    "Shorts": (("shorts", "men"), ("women-shorts", "women")),
    "Leggings": (("women-s-leggings", "women"),),
    "Thermal Layers": (
        ("mens-thermal-layers", "men"),
        ("womens-thermal-layers", "women"),
    ),
}
SUBCATEGORY_COLLECTIONS = {
    "T-Shirts": (
        ("t-shirts", "men"),
        ("women-t-shirts", "women"),
    ),
    "Polos": (("polos", "men"),),
    "Long Sleeves": (
        ("long-sleeves", "men"),
        ("women-long-sleeves", "women"),
    ),
    "Work Shirts": (("work-shirts", "men"),),
    "High-Vis Shirts": (("high-vis-shirts", "men"),),
    "Kids Shirts": (("shirts-kids", "kids"),),
    "Work Pants": (
        ("work-pants", "men"),
        ("women-work-pants", "women"),
    ),
    "Cargo Pants": (
        ("cargo-pants", "men"),
        ("cargo-pants-women", "women"),
    ),
    "Double-Front Pants": (
        ("double-front-pants", "men"),
        ("double-front-pants-women", "women"),
    ),
    "Jeans": (("jeans", "men"),),
    "Bibs, Coveralls & Overalls": (
        ("bibs-coveralls-overalls", "men"),
        ("bibs-coveralls-overalls-women", "women"),
    ),
    "Kids Pants": (("pants-kids", "kids"),),
    "Work Shorts": (("work-shorts", "men"),),
    "Cargo Shorts": (
        ("cargo-shorts", "men"),
        ("cargo-shorts-women", "women"),
    ),
    "Women's Shorts": (("women-shorts", "women"),),
    "Softshell Jackets": (
        ("softshell-jackets", "men"),
        ("softshell-jackets-women", "women"),
    ),
    "Lightweight Jackets": (
        ("lightweight-jackets", "men"),
        ("lightweight-jackets-women", "women"),
    ),
    "Winter Jackets": (
        ("mens-winter-jackets", "men"),
        ("womens-winter-jackets", "women"),
    ),
    "Work Jackets": (
        ("mens-work-jackets", "men"),
        ("womens-work-jackets", "women"),
    ),
    "Vests": (
        ("vests", "men"),
        ("vests-women", "women"),
    ),
    "High-Vis Outerwear": (("high-vis-outerwear", "men"),),
    "Kids Jackets": (("kids-jackets", "kids"),),
    "Hoodies": (("hoodie", "men"),),
    "Crewnecks": (
        ("crewneck", "men"),
        ("crewneck-women", "women"),
    ),
    "Full-Zip Sweatshirts": (("full-zip", "men"),),
    "Women's Hoodies & Sweatshirts": (
        ("hoodies-sweatshirts-women", "women"),
    ),
    "Men's Thermal Layers": (("mens-thermal-layers", "men"),),
    "Women's Thermal Layers": (("womens-thermal-layers", "women"),),
    "Women's Leggings": (("women-s-leggings", "women"),),
}

def _plain_text(value: str | None) -> str:
    if not value:
        return ""
    return unescape(BeautifulSoup(value, "html.parser").get_text(" ", strip=True))


def _number(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def extract_product_collections(title: str) -> list[str]:
    collections: list[str] = []
    for pattern, label in (
        *PRODUCT_COLLECTION_FALLBACK_PATTERNS,
        *COLLABORATION_COLLECTION_PATTERNS,
    ):
        if re.search(pattern, title, re.I) and label not in collections:
            collections.append(label)
    return collections


def extract_product_functions(*values: Any) -> list[str]:
    text = " ".join(
        " ".join(str(item) for item in value)
        if isinstance(value, list)
        else str(value or "")
        for value in values
    )
    functions: list[str] = []
    for pattern, label in PRODUCT_FUNCTION_PATTERNS:
        if re.search(pattern, text, re.I) and label not in functions:
            functions.append(label)
    if "4-way stretch" in functions and "Stretch" in functions:
        functions.remove("Stretch")
    return functions


def _variant_color(product: dict[str, Any], variant: dict[str, Any]) -> str:
    values = [variant.get("option1"), variant.get("option2"), variant.get("option3")]
    colors: list[str] = []
    for index, option in enumerate(product.get("options", [])):
        if str(option.get("name", "")).lower() in {"color", "colour", "farbe"}:
            value = values[index] if index < len(values) else None
            if value and str(value) not in colors:
                colors.append(str(value))
    return " / ".join(colors)


def _normalize_product(
    product: dict[str, Any],
    card: dict[str, Any],
    audiences: list[str],
    categories: list[str],
    collections: list[str],
    top_seller: bool,
    material: str,
) -> dict[str, Any]:
    variants = product.get("variants") or []
    variant_id = str(card.get("variant_id", ""))
    variant = next(
        (item for item in variants if str(item.get("id", "")) == variant_id),
        None,
    )
    selected_variants = [variant] if variant else variants
    prices = [_number(item.get("price")) for item in selected_variants]
    prices = [price for price in prices if price >= 0]
    card_price = _number(card.get("price"))
    if card_price:
        prices = [card_price]

    image_url = str(card.get("image", ""))
    if not image_url:
        images = product.get("images") or []
        image = product.get("image") or (images[0] if images else {})
        image_url = image.get("src", "") if isinstance(image, dict) else ""

    tags = sorted(set(str(tag) for tag in product.get("tags", [])))
    description = _plain_text(product.get("body_html"))
    title = str(card.get("title") or product.get("title", "")).strip()
    return {
        "id": f"strauss:{variant_id or product.get('id', '')}",
        "source_id": variant_id or str(product.get("id", "")),
        "product_id": str(product.get("id", "")),
        "brand": "strauss",
        "brand_label": "Strauss",
        "source": BASE_URL,
        "title": title,
        "handle": str(product.get("handle", "")).strip(),
        "description": description,
        "category": categories[0],
        "categories": categories,
        "vendor": str(product.get("vendor", "")).strip(),
        "audiences": audiences,
        "audience_labels": [COLLECTIONS[audience] for audience in audiences],
        "collections": collections,
        "price_min": min(prices, default=0),
        "price_max": max(prices, default=0),
        "available": bool(variant.get("available")) if variant else any(
            bool(item.get("available")) for item in variants
        ),
        "variant_count": 1,
        "color": _variant_color(product, variant or {}),
        "tags": tags,
        "image": image_url,
        "url": urljoin(BASE_URL, str(card.get("href", ""))),
        "material": material,
        "product_functions": extract_product_functions(
            title,
            description,
            tags,
            material,
        ),
        "top_seller": top_seller,
        "published_at": product.get("published_at"),
        "updated_at": product.get("updated_at"),
    }


async def _robots_allows(client: httpx.AsyncClient) -> None:
    response = await _get(client, f"{BASE_URL}/robots.txt")
    response.raise_for_status()
    parser = RobotFileParser()
    parser.set_url(f"{BASE_URL}/robots.txt")
    parser.parse(response.text.splitlines())
    target = f"{BASE_URL}/collections/men/products.json?limit=1"
    if not parser.can_fetch(USER_AGENT, target):
        raise RuntimeError("robots.txt does not allow the public collection endpoint.")


async def _get(
    client: httpx.AsyncClient, url: str, **kwargs: Any
) -> httpx.Response:
    for attempt in range(MAX_RETRIES):
        response = await client.get(url, **kwargs)
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            return response
        retry_after = response.headers.get("Retry-After")
        wait_seconds = (
            float(retry_after)
            if retry_after and retry_after.replace(".", "", 1).isdigit()
            else min(2 ** (attempt + 1), 16)
        )
        await asyncio.sleep(wait_seconds)
    response.raise_for_status()
    return response


def _card_identity(href: str) -> tuple[str, str]:
    parsed = urlparse(href)
    path = parsed.path
    if "/products/" not in path:
        return "", ""
    handle = path.split("/products/", 1)[1].strip("/")
    variant_id = parse_qs(parsed.query).get("variant", [""])[0]
    return variant_id or handle, handle


async def _fetch_collection_cards(
    client: httpx.AsyncClient,
    handle: str,
    filters: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    cards_by_id: dict[str, dict[str, Any]] = {}

    for page in range(1, MAX_COLLECTION_PAGES + 1):
        response = await _get(
            client,
            f"{BASE_URL}/collections/{handle}",
            params={**(filters or {}), "page": page},
        )
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("product-card")
        if not cards:
            break

        for card in cards:
            link = next(
                (
                    anchor.get("href", "")
                    for anchor in card.select("a[href]")
                    if "/products/" in anchor.get("href", "")
                ),
                "",
            )
            identity, product_handle = _card_identity(link)
            if not identity or not product_handle:
                continue

            title = card.select_one(".product-card-title")
            price = card.select_one(".price")
            price_match = re.search(
                r"\$([0-9,]+(?:\.\d{2})?)",
                price.get_text(" ", strip=True) if price else "",
            )
            image = card.select_one(".product-card-featured-image img, img")
            image_url = image.get("src", "") if image else ""
            if image_url.startswith("//"):
                image_url = f"https:{image_url}"

            cards_by_id[identity] = {
                "identity": identity,
                "variant_id": parse_qs(urlparse(link).query).get("variant", [""])[0],
                "handle": product_handle,
                "href": link,
                "title": title.get_text(" ", strip=True) if title else "",
                "price": (
                    float(price_match.group(1).replace(",", ""))
                    if price_match
                    else 0
                ),
                "image": image_url,
            }

        await asyncio.sleep(REQUEST_DELAY_SECONDS)

    return cards_by_id


async def _fetch_product_collection_memberships(
    client: httpx.AsyncClient,
) -> dict[str, set[str]]:
    response = await _get(client, f"{BASE_URL}/collections/all")
    soup = BeautifulSoup(response.text, "html.parser")
    heading = next(
        (
            node
            for node in soup.find_all("p")
            if node.get_text(" ", strip=True).lower() == "e.s. collection lines"
        ),
        None,
    )
    if heading is None:
        return {}

    container = heading.find_parent("div", class_="first-level-filter")
    if container is None:
        return {}

    memberships: dict[str, set[str]] = {}
    for filter_value in container.select("filter-value[value]"):
        label = filter_value.get_text(" ", strip=True)
        query = parse_qs(urlparse(str(filter_value.get("value", ""))).query)
        if not label or not query:
            continue
        filter_name, values = next(iter(query.items()))
        if not values:
            continue
        cards = await _fetch_collection_cards(
            client,
            "all",
            {filter_name: values[0]},
        )
        for identity in cards:
            memberships.setdefault(identity, set()).add(label)
        await asyncio.sleep(REQUEST_DELAY_SECONDS)
    return memberships


async def _fetch_category_memberships(
    client: httpx.AsyncClient,
) -> tuple[
    dict[str, set[str]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    memberships: dict[str, set[str]] = {}
    category_cards: dict[str, dict[str, Any]] = {}
    category_products: dict[str, dict[str, Any]] = {}
    for category, collections in CATEGORY_COLLECTIONS.items():
        for collection, audience in collections:
            cards = await _fetch_collection_cards(client, collection)
            for identity, card in cards.items():
                memberships.setdefault(identity, set()).add(category)
                if identity in category_cards:
                    category_cards[identity]["audiences"].add(audience)
                else:
                    category_cards[identity] = {
                        **card,
                        "audiences": {audience},
                    }
            for product in await _fetch_collection_products(client, collection):
                category_products[str(product.get("handle", ""))] = product
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
    return memberships, category_cards, category_products


async def _fetch_subcategory_memberships(
    client: httpx.AsyncClient,
) -> dict[str, set[str]]:
    memberships: dict[str, set[str]] = {}
    for subcategory, collections in SUBCATEGORY_COLLECTIONS.items():
        for collection, _audience in collections:
            cards = await _fetch_collection_cards(client, collection)
            for identity in cards:
                memberships.setdefault(identity, set()).add(subcategory)
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
    return memberships


async def _fetch_collection_products(
    client: httpx.AsyncClient, handle: str
) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    page = 1

    while True:
        response = await _get(
            client,
            f"{BASE_URL}/collections/{handle}/products.json",
            params={"limit": PAGE_SIZE, "page": page},
        )
        batch = response.json().get("products", [])
        products.extend(batch)

        if len(batch) < PAGE_SIZE:
            break
        page += 1
        await asyncio.sleep(REQUEST_DELAY_SECONDS)

    return products


async def _fetch_canonical_product(
    client: httpx.AsyncClient, handle: str
) -> dict[str, Any]:
    response = await _get(client, f"{BASE_URL}/products/{handle}.js")
    product = response.json()
    variants = []
    for variant in product.get("variants", []):
        variants.append(
            {
                **variant,
                "price": _number(variant.get("price")) / 100,
            }
        )
    featured_image = product.get("featured_image", "")
    if isinstance(featured_image, str) and featured_image.startswith("//"):
        featured_image = f"https:{featured_image}"
    return {
        "id": product.get("id"),
        "title": product.get("title", ""),
        "handle": product.get("handle", handle),
        "body_html": product.get("description", ""),
        "product_type": product.get("type", ""),
        "vendor": product.get("vendor", ""),
        "variants": variants,
        "options": product.get("options", []),
        "image": {"src": featured_image},
        "images": [{"src": image} for image in product.get("images", [])],
        "tags": product.get("tags", []),
        "published_at": None,
        "updated_at": None,
    }


def _extract_material(html: str) -> str:
    def clean_material(value: str) -> str:
        material = re.sub(r"\s+", " ", value).strip()
        composition = re.search(
            r"(?i)(?:\b(?:shell|lining|padding|palm|back of hand|belt|buckle|upper|sole)\b\s*:?\s*|\d+(?:[.,]\d+)?\s*%)",
            material,
        )
        if composition and composition.start() > 0:
            material = material[composition.start() :].strip()
        return material

    soup = BeautifulSoup(html, "html.parser")
    for label in soup.find_all(["strong", "b"]):
        if not re.match(r"^material\s*:", label.get_text(" ", strip=True), re.I):
            continue

        parts: list[str] = []
        for node in label.next_siblings:
            if getattr(node, "name", None) in {"strong", "b"}:
                break
            text = (
                node.get_text(" ", strip=True)
                if hasattr(node, "get_text")
                else str(node).strip()
            )
            if text:
                parts.append(text)
        material = clean_material(" ".join(parts))
        if material:
            return material

    plain_text = soup.get_text(" ", strip=True)
    match = re.search(
        r"\bmaterials?\s*:\s*(.+?)(?=\b(?:size and fit|care instructions?)\s*:|$)",
        plain_text,
        re.I,
    )
    if match:
        return clean_material(match.group(1))
    return ""


def _fallback_classification(
    title: str,
    categories: list[str],
    subcategories: list[str],
) -> tuple[list[str], list[str]]:
    if subcategories:
        return categories, subcategories

    normalized_title = title.lower()
    if categories == ["Other"]:
        if "t-shirt" in normalized_title or re.search(r"\btee\b", normalized_title):
            return ["Shirts"], ["T-Shirts"]
        if "hooded sweatjacket" in normalized_title:
            return ["Hoodies & Sweatshirts"], ["Full-Zip Sweatshirts"]
        if "jacket" in normalized_title:
            return ["Outerwear"], ["Lightweight Jackets"]

    if categories == ["Backpacks & Bags"]:
        return categories, ["Backpacks & Bags"]
    return categories, subcategories


async def scrape_strauss_products() -> dict[str, Any]:
    timeout = httpx.Timeout(30.0, connect=15.0)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
    }

    async with httpx.AsyncClient(
        headers=headers, timeout=timeout, follow_redirects=True
    ) as client:
        await _robots_allows(client)

        listings: dict[str, dict[str, Any]] = {}
        raw_products: dict[str, dict[str, Any]] = {}
        for handle in COLLECTIONS:
            collection_cards = await _fetch_collection_cards(client, handle)
            for identity, card in collection_cards.items():
                current = listings.setdefault(
                    identity,
                    {**card, "audiences": set()},
                )
                current["audiences"].add(handle)

            for product in await _fetch_collection_products(client, handle):
                product_handle = str(product.get("handle", ""))
                if any(
                    card["handle"] == product_handle
                    for card in collection_cards.values()
                ):
                    raw_products[product_handle] = product
            await asyncio.sleep(REQUEST_DELAY_SECONDS)

        top_seller_ids = set(
            await _fetch_collection_cards(client, TOP_SELLERS_COLLECTION)
        )
        (
            category_memberships,
            category_cards,
            category_products,
        ) = await _fetch_category_memberships(client)
        subcategory_memberships = await _fetch_subcategory_memberships(client)
        product_collection_memberships = (
            await _fetch_product_collection_memberships(client)
        )
        raw_products.update(category_products)
        for identity, card in category_cards.items():
            if identity in listings:
                listings[identity]["audiences"].update(card["audiences"])
            else:
                listings[identity] = card

        missing_handles = sorted(
            {
                card["handle"]
                for card in listings.values()
                if card["handle"] not in raw_products
            }
        )
        for product_handle in missing_handles:
            raw_products[product_handle] = await _fetch_canonical_product(
                client, product_handle
            )
            await asyncio.sleep(REQUEST_DELAY_SECONDS)

    products: list[dict[str, Any]] = []
    mapped_categories = set(CATEGORY_COLLECTIONS)
    for identity, card in listings.items():
        product = raw_products.get(card["handle"])
        if not product:
            continue
        categories = sorted(category_memberships.get(identity, set()))
        subcategories = sorted(subcategory_memberships.get(identity, set()))
        product_type = str(product.get("product_type") or "Other").strip()
        if not categories:
            categories = [
                product_type if product_type not in mapped_categories else "Other"
            ]
        categories, subcategories = _fallback_classification(
            str(card.get("title") or product.get("title", "")),
            categories,
            subcategories,
        )
        title = str(card.get("title") or product.get("title", ""))
        collections = sorted(product_collection_memberships.get(identity, set()))
        for collection in extract_product_collections(title):
            if collection.startswith("Strauss x ") and collection not in collections:
                collections.append(collection)
        normalized = _normalize_product(
                product,
                card,
                sorted(card["audiences"]),
                categories,
                collections,
                identity in top_seller_ids,
                _extract_material(str(product.get("body_html", ""))),
            )
        normalized["subcategories"] = subcategories
        products.append(normalized)
    products.sort(key=lambda item: (item["title"].lower(), item["color"].lower()))
    return {
        "source": BASE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(products),
        "products": products,
    }
