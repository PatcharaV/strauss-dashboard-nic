import asyncio
import hashlib
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .analytics import build_dashboard, build_options, filter_products
from .catalog import (
    CACHE_PATH,
    HISTORY_START_MONTH,
    HISTORY_START_YEAR,
    available_periods,
    load_cache,
    load_period_cache,
    normalize_csv,
    scrape_products,
)

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
auto_scrape_task: asyncio.Task | None = None

DASHBOARD_USERS = {
    "NYKOversea": {
        "password": "Nanyang",
        "allowed_brands": ["strauss", "rhone", "arcteryx"],
    },
    "NIC": {
        "password": "Nicnanyang",
        "allowed_brands": ["*"],
    },
}
LIMITED_BRAND_ORDER = ["strauss", "rhone", "arcteryx"]


class LoginRequest(BaseModel):
    username: str
    password: str


def dashboard_token(username: str, password: str) -> str:
    payload = f"{username}:{password}:nic-dashboard"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def user_from_token(token: str) -> dict[str, Any] | None:
    for username, config in DASHBOARD_USERS.items():
        expected = dashboard_token(username, config["password"])
        if secrets.compare_digest(token, expected):
            return {"username": username, "allowed_brands": config["allowed_brands"]}
    return None


def require_dashboard_auth(
    x_dashboard_token: str | None = Header(default=None, alias="X-Dashboard-Token"),
) -> dict[str, Any]:
    if not x_dashboard_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = user_from_token(x_dashboard_token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def can_view_all_brands(user: dict[str, Any]) -> bool:
    return "*" in user.get("allowed_brands", [])


def allowed_brand_filter(brands: str | None, user: dict[str, Any]) -> list[str]:
    selected = normalize_csv(brands)
    if can_view_all_brands(user):
        return selected
    allowed = list(user.get("allowed_brands", LIMITED_BRAND_ORDER))
    allowed_set = set(allowed)
    if not selected:
        return allowed.copy()
    blocked = [brand for brand in selected if brand not in allowed_set]
    if blocked:
        raise HTTPException(status_code=403, detail="Brand is not available for this user")
    return selected


def visible_brand_options(options: list[dict[str, str]], user: dict[str, Any]) -> list[dict[str, str]]:
    if can_view_all_brands(user):
        return options
    allowed = set(user.get("allowed_brands", LIMITED_BRAND_ORDER))
    return [brand for brand in options if brand["value"] in allowed]


def make_scrape_period(month: str | None, year: int | None) -> dict[str, Any] | None:
    if not month or not year:
        return None
    month = month.upper()
    return {
        "month": month,
        "month_label": MONTH_LABELS[month],
        "year": year,
        "label": f"{month} {year}",
    }


def current_scrape_period() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    month = list(MONTH_LABELS)[now.month - 1]
    year = now.year
    if year < HISTORY_START_YEAR or (
        year == HISTORY_START_YEAR and now.month < HISTORY_START_MONTH
    ):
        month = "JUN"
        year = 2026
    return make_scrape_period(month, year) or {
        "month": "JUN",
        "month_label": "June",
        "year": 2026,
        "label": "JUN 2026",
    }


async def get_data(
    force: bool = False, scrape_period: dict[str, Any] | None = None
) -> dict[str, Any]:
    cache_key = f"data:{scrape_period.get('label')}" if scrape_period else "data"
    if not force and cache_key in store:
        return store[cache_key]

    async with scrape_lock:
        if force:
            store[cache_key] = await scrape_products(scrape_period=scrape_period)
            if not scrape_period:
                store["data"] = store[cache_key]
        elif cache_key not in store:
            cached = load_period_cache(scrape_period) if scrape_period else load_cache()
            store[cache_key] = cached or load_cache() or await scrape_products(
                scrape_period=scrape_period
            )
    return store[cache_key]


async def monthly_auto_scrape_loop() -> None:
    while True:
        now = datetime.now(timezone.utc)
        period = current_scrape_period()
        try:
            if now.day == 1 and load_period_cache(period) is None:
                await get_data(force=True, scrape_period=period)
        except Exception:
            pass
        await asyncio.sleep(60 * 60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global auto_scrape_task
    auto_scrape_task = asyncio.create_task(monthly_auto_scrape_loop())
    try:
        yield
    finally:
        if auto_scrape_task:
            auto_scrape_task.cancel()


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
        "available_periods": available_periods(),
    }


@app.get("/api/periods")
async def periods() -> dict[str, Any]:
    return {
        "start": {"month": "JUN", "year": 2026, "label": "JUN 2026"},
        "current": current_scrape_period(),
        "available": available_periods(),
    }


@app.post("/api/login")
async def login(credentials: LoginRequest) -> dict[str, Any]:
    user_config = DASHBOARD_USERS.get(credentials.username)
    if not user_config or not secrets.compare_digest(
        credentials.password,
        user_config["password"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "token": dashboard_token(credentials.username, user_config["password"]),
        "username": credentials.username,
        "allowed_brands": user_config["allowed_brands"],
    }


@app.get("/api/options")
async def options(
    month: str | None = Query(default=None, pattern="^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$"),
    year: int | None = Query(default=None, ge=2026, le=2100),
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
    user: dict[str, Any] = Depends(require_dashboard_auth),
) -> dict[str, Any]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price must not exceed max_price")

    scrape_period = make_scrape_period(month, year)
    data = await get_data(scrape_period=scrape_period)
    selected_categories = normalize_csv(categories)
    selected_brand_values = allowed_brand_filter(brands, user)
    products = filter_products(
        data["products"],
        search,
        brands=selected_brand_values,
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
    options["brands"] = visible_brand_options(
        build_options(data["products"])["brands"],
        user,
    )
    selected_brands = set(selected_brand_values)
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
    month: str | None = Query(default=None, pattern="^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$"),
    year: int | None = Query(default=None, ge=2026, le=2100),
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
    user: dict[str, Any] = Depends(require_dashboard_auth),
) -> dict[str, Any]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price must not exceed max_price")

    scrape_period = make_scrape_period(month, year)
    data = await get_data(scrape_period=scrape_period)
    selected_categories = normalize_csv(categories)
    selected_brand_values = allowed_brand_filter(brands, user)
    products = filter_products(
        data["products"],
        search=search,
        brands=selected_brand_values,
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
    month: str | None = Query(default=None, pattern="^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$"),
    year: int | None = Query(default=None, ge=2026, le=2100),
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
    user: dict[str, Any] = Depends(require_dashboard_auth),
) -> dict[str, Any]:
    scrape_period = make_scrape_period(month, year)
    data = await get_data(scrape_period=scrape_period)
    selected_brand_values = allowed_brand_filter(brands, user)
    rows = filter_products(
        data["products"],
        search=search,
        brands=selected_brand_values,
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
    year: int = Query(default=2026, ge=2020, le=2100),
    _: dict[str, Any] = Depends(require_dashboard_auth),
) -> dict[str, Any]:
    scrape_period = {
        "month": month,
        "month_label": MONTH_LABELS[month],
        "year": year,
        "label": f"{month} {year}",
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
