import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .analytics import build_dashboard, build_options, filter_products
from .catalog import load_cache, normalize_csv, scrape_products

store: dict[str, Any] = {}
scrape_lock = asyncio.Lock()


async def get_data(force: bool = False) -> dict[str, Any]:
    if not force and "data" in store:
        return store["data"]

    async with scrape_lock:
        if force:
            store["data"] = await scrape_products()
        elif "data" not in store:
            store["data"] = load_cache() or await scrape_products()
    return store["data"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    cached = load_cache()
    if cached:
        store["data"] = cached
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
    cached = load_cache()
    return {
        "status": "ok",
        "cache_available": cached is not None,
        "scraped_at": cached.get("scraped_at") if cached else None,
    }


@app.get("/api/options")
async def options(
    brands: str | None = None,
    categories: str | None = None,
) -> dict[str, Any]:
    data = await get_data()
    products = filter_products(
        data["products"],
        brands=normalize_csv(brands),
        categories=normalize_csv(categories),
    )
    options = build_options(products)
    options["brands"] = build_options(data["products"])["brands"]
    return options


@app.get("/api/dashboard")
async def dashboard(
    search: str | None = None,
    brands: str | None = None,
    audiences: str | None = None,
    categories: str | None = None,
    subcategories: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None, pattern="^(available|unavailable)$"),
    top_seller: str | None = Query(default=None, pattern="^(yes|no)$"),
    material: str | None = Query(default=None, pattern="^(specified|missing)$"),
) -> dict[str, Any]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price must not exceed max_price")

    data = await get_data()
    products = filter_products(
        data["products"],
        search,
        normalize_csv(brands),
        normalize_csv(audiences),
        normalize_csv(categories),
        normalize_csv(subcategories),
        min_price,
        max_price,
        availability,
        top_seller,
        material,
    )
    return build_dashboard(products, data["source"], data.get("scraped_at"))


@app.get("/api/products")
async def products(
    search: str | None = None,
    brands: str | None = None,
    audiences: str | None = None,
    categories: str | None = None,
    subcategories: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None, pattern="^(available|unavailable)$"),
    top_seller: str | None = Query(default=None, pattern="^(yes|no)$"),
    material: str | None = Query(default=None, pattern="^(specified|missing)$"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    data = await get_data()
    rows = filter_products(
        data["products"],
        search,
        normalize_csv(brands),
        normalize_csv(audiences),
        normalize_csv(categories),
        normalize_csv(subcategories),
        min_price,
        max_price,
        availability,
        top_seller,
        material,
    )
    return {"total": len(rows), "products": rows[:limit]}


@app.post("/api/scrape")
async def scrape() -> dict[str, Any]:
    try:
        data = await get_data(force=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scraping failed: {exc}") from exc
    return {
        "status": "completed",
        "product_count": data["product_count"],
        "scraped_at": data["scraped_at"],
    }


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
