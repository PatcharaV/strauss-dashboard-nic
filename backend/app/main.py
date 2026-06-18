import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .analytics import build_dashboard, build_options, filter_products
from .catalog import CACHE_PATH, load_cache, normalize_csv, scrape_products

MONTH_LABELS = {
    "JAN": "January",
    "FEB": "February",
    "MAR": "March",
    "APR": "April",
    "MAY": "May",
    "JUN": "June",
    "JUL": "July",
    "AUG": "August",
    "SEP": "September",
    "OCT": "October",
    "NOV": "November",
    "DEC": "December",
}

store: dict[str, Any] = {}
scrape_lock = asyncio.Lock()


async def get_data(
    force: bool = False, scrape_period: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not force and "data" in store:
        return store["data"]

    async with scrape_lock:
        if force:
            store["data"] = await scrape_products(scrape_period=scrape_period)
        elif "data" not in store:
            store["data"] = load_cache() or await scrape_products()
    return store["data"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Strauss Product Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "cache_available": CACHE_PATH.exists(),
        "data_loaded": "data" in store,
    }


@app.get("/api/options")
async def options(
    search: str | None = None,
    brands: str | None = None,
    audiences: str | None = None,
    collections: str | None = None,
    activities: str | None = None,
    features: str | None = None,
    categories: str | None = None,
    subcategories: str | None = None,
    color: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None, pattern="^(available|unavailable)$"),
    top_seller: str | None = Query(default=None, pattern="^(yes|no)$"),
    shop_highlight: str | None = None,
    material: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price must not exceed max_price")

    data = await get_data()
    selected_categories = normalize_csv(categories)
    products = filter_products(
        data["products"],
        search,
        brands=normalize_csv(brands),
        audiences=normalize_csv(audiences),
        collections=normalize_csv(collections),
        activities=normalize_csv(activities),
        features=normalize_csv(features),
        categories=selected_categories,
        subcategories=normalize_csv(subcategories),
        color=color,
        min_price=min_price,
        max_price=max_price,
        availability=availability,
        top_seller=top_seller,
        shop_highlight=shop_highlight,
        material=material,
        season=season,
    )
    options = build_options(products, selected_categories)
    options["brands"] = build_options(data["products"])["brands"]
    selected_brands = set(normalize_csv(brands))
    extra_collections = {
        collection
        for source in data.get("sources", [])
        if not selected_brands or source.get("brand") in selected_brands
        for collection in source.get("collection_options", [])
    }
    if extra_collections:
        options["collections"] = sorted(
            set(options.get("collections", [])) | extra_collections,
            key=str.lower,
        )
    return options


@app.get("/api/dashboard")
async def dashboard(
    search: str | None = None,
    brands: str | None = None,
    audiences: str | None = None,
    collections: str | None = None,
    activities: str | None = None,
    features: str | None = None,
    categories: str | None = None,
    subcategories: str | None = None,
    color: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None, pattern="^(available|unavailable)$"),
    top_seller: str | None = Query(default=None, pattern="^(yes|no)$"),
    shop_highlight: str | None = None,
    material: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price must not exceed max_price")

    data = await get_data()
    selected_categories = normalize_csv(categories)
    products = filter_products(
        data["products"],
        search=search,
        brands=normalize_csv(brands),
        audiences=normalize_csv(audiences),
        collections=normalize_csv(collections),
        activities=normalize_csv(activities),
        features=normalize_csv(features),
        categories=selected_categories,
        subcategories=normalize_csv(subcategories),
        color=color,
        min_price=min_price,
        max_price=max_price,
        availability=availability,
        top_seller=top_seller,
        shop_highlight=shop_highlight,
        material=material,
        season=season,
    )
    return build_dashboard(
        products,
        data["source"],
        data.get("scraped_at"),
        data.get("scrape_period"),
        selected_categories,
    )


@app.get("/api/products")
async def products(
    search: str | None = None,
    brands: str | None = None,
    audiences: str | None = None,
    collections: str | None = None,
    activities: str | None = None,
    features: str | None = None,
    categories: str | None = None,
    subcategories: str | None = None,
    color: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None, pattern="^(available|unavailable)$"),
    top_seller: str | None = Query(default=None, pattern="^(yes|no)$"),
    shop_highlight: str | None = None,
    material: str | None = None,
    season: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    data = await get_data()
    rows = filter_products(
        data["products"],
        search=search,
        brands=normalize_csv(brands),
        audiences=normalize_csv(audiences),
        collections=normalize_csv(collections),
        activities=normalize_csv(activities),
        features=normalize_csv(features),
        categories=normalize_csv(categories),
        subcategories=normalize_csv(subcategories),
        color=color,
        min_price=min_price,
        max_price=max_price,
        availability=availability,
        top_seller=top_seller,
        shop_highlight=shop_highlight,
        material=material,
        season=season,
    )
    return {"total": len(rows), "products": rows[:limit]}


@app.post("/api/scrape")
async def scrape(
    month: str = Query(default="JAN", pattern="^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$"),
    month_from: str | None = Query(default=None, pattern="^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$"),
    month_to: str | None = Query(default=None, pattern="^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$"),
    year: int = Query(default=2026, ge=2020, le=2100),
) -> dict[str, Any]:
    selected_month_from = month_from or month
    selected_month_to = month_to or selected_month_from
    label = (
        f"{selected_month_from} {year}"
        if selected_month_from == selected_month_to
        else f"{selected_month_from}-{selected_month_to} {year}"
    )
    scrape_period = {
        "month": selected_month_from,
        "month_from": selected_month_from,
        "month_to": selected_month_to,
        "month_label": MONTH_LABELS[selected_month_from],
        "month_from_label": MONTH_LABELS[selected_month_from],
        "month_to_label": MONTH_LABELS[selected_month_to],
        "year": year,
        "label": label,
    }
    try:
        data = await get_data(force=True, scrape_period=scrape_period)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scraping failed: {exc}") from exc
    return {
        "status": "completed",
        "product_count": data["product_count"],
        "scraped_at": data["scraped_at"],
        "scrape_period": data.get("scrape_period", scrape_period),
    }


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
