import { useEffect, useMemo, useState } from "react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  Treemap,
} from "recharts";
import { demoDashboard, demoOptions } from "./demoData";

const COLORS = [
  "#ef3e42",
  "#101820",
  "#f5a623",
  "#4976ba",
  "#6f5bd3",
  "#2f9e74",
  "#d76596",
  "#866143",
  "#6c7a89",
  "#a8b400",
  "#00a3a3",
  "#9b59b6",
];

const AUTH_STORAGE_KEY = "nic-dashboard-session";
const DEFAULT_BRAND_OPTIONS = [
  { value: "strauss", label: "Strauss" },
  { value: "rhone", label: "Rhone" },
  { value: "arcteryx", label: "Arc'Teryx" },
  { value: "lululemon", label: "lululemon" },
];

const DEFAULT_SECTIONS = {
  summary: true,
  audience: true,
  categoryDonut: true,
  treemap: true,
  products: true,
};

const STRAUSS_PITCH_SLIDES = [
  "/strauss-pitch-slides/Slide1.PNG",
  "/strauss-pitch-slides/Slide2.PNG",
  "/strauss-pitch-slides/Slide3.PNG",
  "/strauss-pitch-slides/Slide4.PNG",
  "/strauss-pitch-slides/Slide5.PNG",
  "/strauss-pitch-slides/Slide6.PNG",
];

const ARCTERYX_COTTON_SLIDES = [
  "/arcteryx-cotton-slides/Slide1.PNG",
  "/arcteryx-cotton-slides/Slide2.PNG",
  "/arcteryx-cotton-slides/Slide3.PNG",
  "/arcteryx-cotton-slides/Slide4.PNG",
];

const SCRAPE_MONTHS = [
  "JAN",
  "FEB",
  "MAR",
  "APR",
  "MAY",
  "JUN",
  "JUL",
  "AUG",
  "SEP",
  "OCT",
  "NOV",
  "DEC",
];
const HISTORY_START = { month: "JUN", year: 2026 };
const CURRENT_PERIOD = {
  month: SCRAPE_MONTHS[new Date().getMonth()],
  year: new Date().getFullYear(),
};
const SCRAPE_YEARS = Array.from(
  { length: Math.max(HISTORY_START.year, CURRENT_PERIOD.year) - HISTORY_START.year + 1 },
  (_, index) => 2026 + index,
);

const formatNumber = new Intl.NumberFormat("en-US");
const formatMoney = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function formatPrice(product) {
  if (product.price_known === false) return "Not captured";
  const minimum = formatMoney.format(product.price_min);
  const maximum = formatMoney.format(product.price_max);
  return product.price_min === product.price_max
    ? minimum
    : `${minimum} - ${maximum}`;
}

function formatDate(value) {
  if (!value) return "Demo data";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatList(values, fallback = "Not specified") {
  return values?.length ? values.join(", ") : fallback;
}

function formatMultilineList(values, fallback = "Not specified") {
  return values?.length ? values.join("\n") : fallback;
}

function emptyDashboardForPeriod(month, year) {
  return {
    source: [],
    scraped_at: null,
    scrape_period: { month, year, label: `${month} ${year}` },
    summary: {
      total_products: 0,
      brands: 0,
      categories: 0,
      average_price: 0,
      available_products: 0,
      collection_memberships: 0,
      named_collection_products: 0,
      unassigned_collection_products: 0,
      multi_collection_products: 0,
      overlap_memberships: 0,
      category_memberships: 0,
      multi_category_products: 0,
      category_overlap_memberships: 0,
      availability_rate: 0,
    },
    brands: [],
    audiences: [],
    collections: [],
    categories: [],
    subcategories: [],
    activities: [],
    products: [],
  };
}

function getMaterialValues(product) {
  if (product.material_details?.length) return product.material_details;
  return product.material ? [product.material] : [];
}

function DetailList({ values, fallback = "Not specified" }) {
  if (!values?.length) return <span className="muted-detail">{fallback}</span>;
  return (
    <ul className="detail-list">
      {values.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </ul>
  );
}

function SlideDeckPanel({
  id,
  eyebrow,
  title,
  downloadHref,
  downloadLabel = "Download PPTX",
  extraDownloads = [],
  slides,
  slideIndex,
  setSlideIndex,
  altPrefix,
}) {
  const currentSlide = slides[slideIndex];
  return (
    <section className="panel document-panel" id={id}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        <div className="document-downloads">
          <a
            className="export-button"
            href={downloadHref}
            target="_blank"
            rel="noreferrer"
            download
          >
            {downloadLabel}
          </a>
          {extraDownloads.map((item) => (
            <a
              className="secondary-link"
              href={item.href}
              target="_blank"
              rel="noreferrer"
              download
              key={item.href}
            >
              {item.label}
            </a>
          ))}
        </div>
      </div>
      <p className="panel-help">
        Slide preview rendered from the attached PowerPoint deck.
      </p>
      <div className="slide-viewer">
        <div className="slide-toolbar">
          <div>
            <span className="document-type">PPTX PREVIEW</span>
            <strong>
              Slide {slideIndex + 1} of {slides.length}
            </strong>
          </div>
          <div className="slide-actions">
            <button
              type="button"
              className="secondary-link"
              onClick={() =>
                setSlideIndex((index) =>
                  index === 0 ? slides.length - 1 : index - 1,
                )
              }
            >
              Previous
            </button>
            <button
              type="button"
              className="secondary-link"
              onClick={() =>
                setSlideIndex((index) =>
                  index === slides.length - 1 ? 0 : index + 1,
                )
              }
            >
              Next
            </button>
          </div>
        </div>
        <div className="slide-stage">
          <img src={currentSlide} alt={`${altPrefix} slide ${slideIndex + 1}`} />
        </div>
        <div className="slide-thumbnails" aria-label={`Select ${title} slide`}>
          {slides.map((slide, index) => (
            <button
              type="button"
              key={slide}
              className={index === slideIndex ? "active" : ""}
              onClick={() => setSlideIndex(index)}
              aria-label={`Show slide ${index + 1}`}
            >
              <img
                src={slide}
                alt={`${altPrefix} slide ${index + 1} thumbnail`}
                loading="lazy"
              />
              <span>{index + 1}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

async function exportProductsToExcel(products) {
  const XLSX = await import("xlsx");
  const rows = products.map((product) => ({
    Product: product.title,
    Brand: product.brand_label,
    "Series Number": product.series_number || product.product_id || "",
    "Style Number": product.style_number || "",
    "Season Code": product.season_code || "",
    "Season Range": product.season_range || "",
    Category: (product.categories || [product.category]).join(", "),
    "Sub Category": (product.subcategories || []).join(", "),
    Collection: (product.collections || []).join(", "),
    "Available Colors": (product.available_colors || []).join(", ") || "None",
    "Unavailable Colors": (product.unavailable_colors || []).join(", "),
    Material: formatMultilineList(getMaterialValues(product)),
    "Technical Features": formatMultilineList(product.technical_features),
    "Fabric Treatment": formatMultilineList(product.fabric_treatment),
    Construction: formatMultilineList(product.construction),
    "Shop Highlights": (product.shop_highlights || []).join(", "),
    "Price Min": product.price_min,
    "Price Max": product.price_max,
    "Price Range": formatPrice(product),
    Status: product.available ? "Available" : "Unavailable",
    URL: product.url,
  }));
  const worksheet = XLSX.utils.json_to_sheet(rows);
  worksheet["!cols"] = [
    { wch: 42 },
    { wch: 14 },
    { wch: 18 },
    { wch: 14 },
    { wch: 12 },
    { wch: 18 },
    { wch: 24 },
    { wch: 28 },
    { wch: 28 },
    { wch: 32 },
    { wch: 32 },
    { wch: 50 },
    { wch: 40 },
    { wch: 42 },
    { wch: 50 },
    { wch: 12 },
    { wch: 10 },
    { wch: 10 },
    { wch: 18 },
    { wch: 12 },
    { wch: 64 },
  ];
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Product Details");
  const today = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(workbook, `brand-analysis-products-${today}.xlsx`);
}

function buildQuery(filters, period) {
  const params = new URLSearchParams();
  if (period?.month && period?.year) {
    params.set("month", period.month);
    params.set("year", String(period.year));
  }
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.brands.length) {
    params.set("brands", filters.brands.join(","));
  }
  if (filters.audiences.length) {
    params.set("audiences", filters.audiences.join(","));
  }
  if (filters.collections.length) {
    params.set("collections", filters.collections.join(","));
  }
  if (filters.activities.length) {
    params.set("activities", filters.activities.join(","));
  }
  if (filters.categories.length) {
    params.set("categories", filters.categories.join(","));
  }
  if (filters.subcategories.length) {
    params.set("subcategories", filters.subcategories.join(","));
  }
  if (filters.minPrice !== "") params.set("min_price", filters.minPrice);
  if (filters.maxPrice !== "") params.set("max_price", filters.maxPrice);
  if (filters.availability !== "all") {
    params.set("availability", filters.availability);
  }
  if (filters.shopHighlight !== "all") {
    params.set("shop_highlight", filters.shopHighlight);
  }
  if (filters.material !== "all") {
    params.set("material", filters.material);
  }
  if (filters.season !== "all") {
    params.set("season", filters.season);
  }
  return params.toString();
}

function DonutChart({
  data,
  centerLabel,
  centerValue,
  onSelect,
  selectedNames = [],
}) {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  return (
    <div className="chart-shell">
      <ResponsiveContainer width="100%" height={330}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="37%"
            cy="50%"
            innerRadius={68}
            outerRadius={104}
            paddingAngle={1}
            onClick={(entry) => onSelect?.(entry.name)}
            className="clickable-chart"
          >
            {data.map((entry, index) => (
              <Cell
                key={entry.name}
                fill={COLORS[index % COLORS.length]}
                opacity={
                  selectedNames.length === 0 || selectedNames.includes(entry.name)
                    ? 1
                    : 0.28
                }
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ fontSize: 11, padding: "7px 9px" }}
            itemStyle={{ fontSize: 11 }}
            formatter={(value, name) => [
              `${formatNumber.format(value)} (${total ? ((value / total) * 100).toFixed(1) : 0}%)`,
              name,
            ]}
          />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            iconType="circle"
            iconSize={7}
            wrapperStyle={{ fontSize: 9, lineHeight: "14px" }}
            onClick={(entry) => onSelect?.(entry.value)}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="donut-center">
        <strong>{formatNumber.format(centerValue ?? total)}</strong>
        <span>{centerLabel}</span>
      </div>
    </div>
  );
}

function TreemapContent(props) {
  const {
    depth,
    x,
    y,
    width,
    height,
    index,
    name,
    value,
    onSelect,
    selectedNames = [],
  } = props;
  if (depth !== 1) return null;
  const showValue = width > 105 && height > 54;
  const maxLabelLength = Math.max(5, Math.floor(width / 7));
  const displayName =
    name.length > maxLabelLength
      ? `${name.slice(0, Math.max(4, maxLabelLength - 3))}...`
      : name;
  const selected = selectedNames.length === 0 || selectedNames.includes(name);
  return (
    <g className="clickable-chart" onClick={() => onSelect?.(name)}>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={COLORS[index % COLORS.length]}
        stroke="#fff"
        strokeWidth={3}
        opacity={selected ? 1 : 0.32}
      />
      {width > 62 && height > 30 && (
        <text x={x + 8} y={y + 19} fill="#fff" fontSize={11} fontWeight={700}>
          {displayName}
        </text>
      )}
      {showValue && (
        <text x={x + 8} y={y + 35} fill="rgba(255,255,255,.82)" fontSize={10}>
          {formatNumber.format(value)} products
        </text>
      )}
    </g>
  );
}

function FilterGroup({ title, options, selected, onChange }) {
  return (
    <div className="filter-group">
      <span className="filter-title">{title}</span>
      <div className="chip-list">
        {options.map((option) => {
          const value = typeof option === "string" ? option : option.value;
          const label = typeof option === "string" ? option : option.label;
          const active = selected.includes(value);
          return (
            <button
              className={active ? "filter-chip active" : "filter-chip"}
              key={value}
              type="button"
              onClick={() =>
                onChange(
                  active
                    ? selected.filter((item) => item !== value)
                    : [...selected, value],
                )
              }
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        throw new Error("Invalid username or password");
      }
      const session = await response.json();
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
      onLogin(session);
    } catch {
      setError("Username หรือ Password ไม่ถูกต้อง");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="brand-mark">N</div>
        <p className="eyebrow">NAN YANG TEXTILE</p>
        <h1>NIC Dashboard Login</h1>
        <p className="page-description">
          Sign in to view the dashboards available to your account.
        </p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            <span className="filter-title">Username</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter username"
              required
            />
          </label>
          <label>
            <span className="filter-title">Password</span>
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
              required
            />
          </label>
          {error && <p className="login-error">{error}</p>}
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}

function App() {
  const [session, setSession] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY));
    } catch {
      return null;
    }
  });
  const [options, setOptions] = useState(demoOptions);
  const [dashboard, setDashboard] = useState(demoDashboard);
  const [filters, setFilters] = useState({
    search: "",
    brands: ["strauss"],
    audiences: [],
    collections: [],
    activities: [],
    categories: [],
    subcategories: [],
    color: "",
    minPrice: "",
    maxPrice: "",
    availability: "all",
    shopHighlight: "all",
    material: "all",
    season: "all",
  });
  const sections = DEFAULT_SECTIONS;
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [message, setMessage] = useState("Connecting to Python API...");
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [productPage, setProductPage] = useState(1);
  const [productsPerPage, setProductsPerPage] = useState(50);
  const [pitchSlideIndex, setPitchSlideIndex] = useState(0);
  const [arcteryxSlideIndex, setArcteryxSlideIndex] = useState(0);
  const [scrapeMonth, setScrapeMonth] = useState(CURRENT_PERIOD.month);
  const [scrapeYear, setScrapeYear] = useState(CURRENT_PERIOD.year);

  const selectedPeriod = useMemo(
    () => ({ month: scrapeMonth, year: scrapeYear }),
    [scrapeMonth, scrapeYear],
  );
  const availableMonths = useMemo(() => {
    let months = SCRAPE_MONTHS;
    if (scrapeYear === HISTORY_START.year) {
      months = months.slice(SCRAPE_MONTHS.indexOf(HISTORY_START.month));
    }
    if (scrapeYear === CURRENT_PERIOD.year) {
      months = months.slice(0, SCRAPE_MONTHS.indexOf(CURRENT_PERIOD.month) + 1);
    }
    return months;
  }, [scrapeYear]);
  const query = useMemo(
    () => buildQuery(filters, selectedPeriod),
    [filters, selectedPeriod],
  );
  const authHeaders = useMemo(
    () => (session?.token ? { "X-Dashboard-Token": session.token } : {}),
    [session],
  );
  const canViewAllBrands = session?.allowed_brands?.includes("*");
  const brandOptions = canViewAllBrands
    ? options.brands?.length
      ? options.brands
      : DEFAULT_BRAND_OPTIONS
    : DEFAULT_BRAND_OPTIONS.filter((brand) =>
        session?.allowed_brands?.includes(brand.value),
      );
  const productCategories = options.categories;
  const availableShopHighlights = options.shop_highlights || [];
  const activityOptions = options.activities || [];
  const materialKeywords = options.material_keywords || [];
  const seasonOptions = options.seasons || [];
  const showStraussPitch = filters.brands.includes("strauss");
  const showArcteryxDeck = filters.brands.includes("arcteryx");
  const showCategoryTreemap = filters.brands.includes("lululemon");
  const treemapRows = showCategoryTreemap
    ? dashboard.categories || []
    : dashboard.subcategories || [];
  const treemapSelectedNames = showCategoryTreemap
    ? filters.categories
    : filters.subcategories;
  const treemapSelectHandler = showCategoryTreemap
    ? toggleCategory
    : toggleSubcategory;
  const hasCollectionData =
    (dashboard.collections || []).length > 0 ||
    dashboard.products.some((product) => product.collections?.length);
  const hasSubcategoryData = dashboard.products.some(
    (product) => product.subcategories?.length,
  );
  const hasMaterialData = dashboard.products.some(
    (product) =>
      Boolean(String(product.material || "").trim()) ||
      Boolean(product.material_details?.length),
  );
  const hasTechnicalFeatureData = dashboard.products.some(
    (product) => product.technical_features?.length,
  );
  const hasFabricTreatmentData = dashboard.products.some(
    (product) => product.fabric_treatment?.length,
  );
  const hasConstructionData = dashboard.products.some(
    (product) => product.construction?.length,
  );
  const hasSeriesData = dashboard.products.some(
    (product) =>
      product.series_number ||
      product.style_number ||
      product.season_code ||
      product.season_range,
  );
  const hasSubcategoryFilter =
    (options.subcategories || []).length > 0 || filters.subcategories.length > 0;
  const hasCollectionFilter =
    (options.collections || []).length > 0 || filters.collections.length > 0;
  const hasActivityFilter =
    activityOptions.length > 0 || filters.activities.length > 0;
  const hasShopHighlightFilter =
    availableShopHighlights.length > 0 || filters.shopHighlight !== "all";
  const hasMaterialFilter =
    filters.material !== "all" || materialKeywords.length > 0;
  const hasSeasonFilter =
    filters.season !== "all" || seasonOptions.length > 0;
  const hasUnavailableProducts = dashboard.products.some(
    (product) => !product.available,
  ) || filters.availability !== "all";
  const totalProductPages = Math.max(
    1,
    Math.ceil(dashboard.products.length / productsPerPage),
  );
  const currentProductPage = Math.min(productPage, totalProductPages);
  const paginatedProducts = dashboard.products.slice(
    (currentProductPage - 1) * productsPerPage,
    currentProductPage * productsPerPage,
  );

  function handleLogin(nextSession) {
    setSession(nextSession);
    setMessage("Connecting to Python API...");
  }

  function handleLogout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setSession(null);
    setOptions(demoOptions);
    setDashboard(demoDashboard);
    setMessage("Please sign in to view live data");
  }

  function authorizedFetch(url, options = {}) {
    return fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...authHeaders,
      },
    });
  }

  async function loadDashboard() {
    if (!session?.token) return;
    setLoading(true);
    try {
      const [optionsResponse, dashboardResponse] = await Promise.all([
        authorizedFetch(`/api/options${query ? `?${query}` : ""}`),
        authorizedFetch(`/api/dashboard${query ? `?${query}` : ""}`),
      ]);
      if (optionsResponse.status === 401 || dashboardResponse.status === 401) {
        handleLogout();
        return;
      }
      if (optionsResponse.status === 404 || dashboardResponse.status === 404) {
        setDashboard(emptyDashboardForPeriod(scrapeMonth, scrapeYear));
        setMessage(`No saved snapshot for ${scrapeMonth} ${scrapeYear}. Run scrape once for this month.`);
        return;
      }
      if (!optionsResponse.ok || !dashboardResponse.ok) {
        throw new Error("API response was not successful");
      }
      setOptions(await optionsResponse.json());
      setDashboard(await dashboardResponse.json());
      setMessage(
        canViewAllBrands
          ? "Live data for all authorized brands"
          : `Live data from ${brandOptions.map((brand) => brand.label).join(", ")}`,
      );
    } catch {
      setMessage("Demo preview: start the Python API for live data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session?.token) return;
    const timer = setTimeout(loadDashboard, 250);
    return () => clearTimeout(timer);
  }, [query, session?.token]);

  useEffect(() => {
    if (
      scrapeYear === HISTORY_START.year &&
      SCRAPE_MONTHS.indexOf(scrapeMonth) < SCRAPE_MONTHS.indexOf(HISTORY_START.month)
    ) {
      setScrapeMonth(HISTORY_START.month);
      return;
    }
    if (
      scrapeYear === CURRENT_PERIOD.year &&
      SCRAPE_MONTHS.indexOf(scrapeMonth) > SCRAPE_MONTHS.indexOf(CURRENT_PERIOD.month)
    ) {
      setScrapeMonth(CURRENT_PERIOD.month);
    }
  }, [scrapeMonth, scrapeYear]);

  useEffect(() => {
    setProductPage(1);
  }, [query, productsPerPage]);

  useEffect(() => {
    if (productPage > totalProductPages) {
      setProductPage(totalProductPages);
    }
  }, [productPage, totalProductPages]);

  async function scrapeLatest() {
    setScraping(true);
    const periodLabel = `${scrapeMonth} ${scrapeYear}`;
    setMessage(`Scraping ${periodLabel} clothing snapshot...`);
    try {
      const params = new URLSearchParams({
        month: scrapeMonth,
        year: String(scrapeYear),
      });
      const response = await authorizedFetch(`/api/scrape?${params.toString()}`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Scrape failed");
      await loadDashboard();
    } catch {
      setMessage("Could not scrape. Check the Python API and network connection.");
    } finally {
      setScraping(false);
    }
  }

  function resetFilters() {
    setFilters({
      search: "",
      brands: filters.brands,
      audiences: [],
      collections: [],
      activities: [],
      categories: [],
      subcategories: [],
      color: "",
      minPrice: "",
      maxPrice: "",
      availability: "all",
      shopHighlight: "all",
      material: "all",
      season: "all",
    });
  }

  function selectBrand(brand) {
    setFilters({
      ...filters,
      brands: [brand],
      audiences: [],
      collections: [],
      activities: [],
      categories: [],
      subcategories: [],
      color: "",
      minPrice: "",
      maxPrice: "",
      availability: "all",
      shopHighlight: "all",
      material: "all",
      season: "all",
    });
  }

  function toggleCategory(category) {
    setFilters({
      ...filters,
      categories: filters.categories.includes(category)
        ? filters.categories.filter((item) => item !== category)
        : [...filters.categories, category],
      subcategories: [],
    });
  }

  function toggleSubcategory(subcategory) {
    setFilters({
      ...filters,
      subcategories: filters.subcategories.includes(subcategory)
        ? filters.subcategories.filter((item) => item !== subcategory)
        : [subcategory],
    });
  }

  function toggleAudienceLabel(label) {
    const option = options.audiences.find((item) => item.label === label);
    if (!option) return;
    setFilters({
      ...filters,
      audiences: filters.audiences.includes(option.value)
        ? filters.audiences.filter((item) => item !== option.value)
        : [...filters.audiences, option.value],
    });
  }

  function toggleCollection(collection) {
    setFilters({
      ...filters,
      collections: filters.collections.includes(collection)
        ? filters.collections.filter((item) => item !== collection)
        : [...filters.collections, collection],
    });
  }

  if (!session?.token) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">M</div>
          <div>
            <p className="eyebrow">PUBLIC CLOTHING CATALOG ANALYTICS</p>
            <h1>Multi-Brand Clothing Dashboard</h1>
            <p className="page-description">
              Compare clothing from Strauss, Rhone and Arc&apos;teryx. Footwear and
              gear are excluded.
            </p>
          </div>
        </div>
        <div className="header-actions">
          <button className="secondary-link logout-button" type="button" onClick={handleLogout}>
            Logout
          </button>
          <div className="status">
            <span className={message.startsWith("Live") ? "dot live" : "dot"} />
            <div>
              <strong>{message}</strong>
              <small>Updated {formatDate(dashboard.scraped_at)}</small>
              {dashboard.scrape_period?.label && (
                <small>Scrape period {dashboard.scrape_period.label}</small>
              )}
            </div>
          </div>
          <div className="scrape-scheduler" aria-label="Select scrape period">
            <label>
              Month
              <select
                value={scrapeMonth}
                onChange={(event) => setScrapeMonth(event.target.value)}
                disabled={scraping}
              >
                {availableMonths.map((month) => (
                  <option key={month} value={month}>
                    {month}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Year
              <select
                value={scrapeYear}
                onChange={(event) => setScrapeYear(Number(event.target.value))}
                disabled={scraping}
              >
                {SCRAPE_YEARS.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
            <small>
              View or refresh monthly catalog snapshots from JUN 2026 onward.
            </small>
          </div>
          <button
            className="primary-button"
            type="button"
            onClick={scrapeLatest}
            disabled={scraping}
          >
            {scraping ? "Scraping..." : "Refresh selected month"}
          </button>
        </div>
      </header>

      <section className="brand-switcher" aria-label="Filter by brand">
        <div className="brand-switcher-copy">
          <span className="filter-title">Choose brand</span>
          <strong>Select one brand to view its dashboard</strong>
        </div>
        <div className="brand-switcher-buttons">
          {brandOptions.map((brand) => (
            <button
              className={filters.brands.includes(brand.value) ? "active" : ""}
              type="button"
              key={brand.value}
              onClick={() => selectBrand(brand.value)}
            >
              {brand.label}
            </button>
          ))}
        </div>
      </section>

      <nav className="page-nav" aria-label="Page navigation">
        <a href="#overview">Overview</a>
        <a href="#charts">Charts</a>
        <a href="#products">Product details</a>
        <span>Click any chart or table label to filter the dashboard</span>
      </nav>

      <section
        className={filtersOpen ? "control-panel" : "control-panel collapsed"}
      >
        <div className="control-heading">
          <div>
            <p className="eyebrow">DASHBOARD CONTROLS</p>
            <h2>Filter your view</h2>
            <p className="section-description">
              Select one or more options. All cards, charts and products update
              together.
            </p>
          </div>
          <div className="control-actions">
            <button className="text-button" type="button" onClick={resetFilters}>
              Reset filters
            </button>
            <button
              className="collapse-button"
              type="button"
              onClick={() => setFiltersOpen(!filtersOpen)}
              aria-expanded={filtersOpen}
            >
              {filtersOpen ? "Hide filters" : "Show filters"}
            </button>
          </div>
        </div>

        <div className="filter-content streamlined-filters">
          <div className="filter-quick-row">
            <label className="search-filter">
              <span className="filter-title">Search</span>
              <input
                type="search"
                placeholder="Search product, material, collection..."
                value={filters.search}
                onChange={(event) =>
                  setFilters({ ...filters, search: event.target.value })
                }
              />
            </label>

            <section className="audience-filter">
              <FilterGroup
                title="Audience"
                options={options.audiences}
                selected={filters.audiences}
                onChange={(audiences) => setFilters({ ...filters, audiences })}
              />
            </section>
          </div>

          <div className="filter-select-grid">
            <label>
              <span className="filter-title">Category</span>
              <select
                value={
                  filters.categories.length === 1
                    ? filters.categories[0]
                    : "all"
                }
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    categories:
                      event.target.value === "all" ? [] : [event.target.value],
                    subcategories: [],
                  })
                }
              >
                <option value="all">All categories</option>
                {productCategories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </label>

            {hasSubcategoryFilter && (
              <label>
                <span className="filter-title">Sub category</span>
                <select
                  value={
                    filters.subcategories.length === 1
                      ? filters.subcategories[0]
                      : "all"
                  }
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      subcategories:
                        event.target.value === "all" ? [] : [event.target.value],
                    })
                  }
                >
                  <option value="all">All sub categories</option>
                  {options.subcategories.map((subcategory) => (
                    <option key={subcategory} value={subcategory}>
                      {subcategory}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {hasCollectionFilter && (
              <label>
                <span className="filter-title">Collection</span>
                <select
                  value={
                    filters.collections.length === 1
                      ? filters.collections[0]
                      : "all"
                  }
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      collections:
                        event.target.value === "all" ? [] : [event.target.value],
                    })
                  }
                >
                  <option value="all">All collections</option>
                  {(options.collections || []).map((collection) => (
                    <option key={collection} value={collection}>
                      {collection}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {hasActivityFilter && (
              <label>
                <span className="filter-title">Activities</span>
                <select
                  value={
                    filters.activities.length === 1
                      ? filters.activities[0]
                      : "all"
                  }
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      activities:
                        event.target.value === "all" ? [] : [event.target.value],
                    })
                  }
                >
                  <option value="all">All activities</option>
                  {activityOptions.map((activity) => (
                    <option key={activity} value={activity}>
                      {activity}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {hasShopHighlightFilter && (
              <label>
                <span className="filter-title">Shop Highlights</span>
                <select
                  value={filters.shopHighlight}
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      shopHighlight: event.target.value,
                    })
                  }
                >
                  <option value="all">All products</option>
                  {availableShopHighlights.map((highlight) => (
                    <option key={highlight} value={highlight}>
                      {highlight}
                    </option>
                  ))}
                  <option value="none">No highlights</option>
                </select>
              </label>
            )}

            {hasUnavailableProducts && (
              <label>
                <span className="filter-title">Availability</span>
                <select
                  value={filters.availability}
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      availability: event.target.value,
                    })
                  }
                >
                  <option value="all">All statuses</option>
                  <option value="available">Available</option>
                  <option value="unavailable">Unavailable</option>
                </select>
              </label>
            )}

            {hasMaterialFilter && (
              <label>
                <span className="filter-title">Material</span>
                <select
                  value={filters.material}
                  onChange={(event) =>
                    setFilters({ ...filters, material: event.target.value })
                  }
                >
                  <option value="all">All materials</option>
                  {materialKeywords.map((keyword) => (
                    <option key={keyword} value={keyword}>
                      {keyword}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {hasSeasonFilter && (
              <label>
                <span className="filter-title">Season</span>
                <select
                  value={filters.season}
                  onChange={(event) =>
                    setFilters({ ...filters, season: event.target.value })
                  }
                >
                  <option value="all">All seasons</option>
                  {seasonOptions.map((season) => (
                    <option key={season} value={season}>
                      {season}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="price-control compact-price">
              <span className="filter-title">Price range (USD)</span>
              <div className="price-inputs">
                <input
                  type="number"
                  min="0"
                  aria-label="Minimum price"
                  placeholder={`Min ${options.price.min}`}
                  value={filters.minPrice}
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      minPrice: event.target.value,
                    })
                  }
                />
                <span>to</span>
                <input
                  type="number"
                  min="0"
                  aria-label="Maximum price"
                  placeholder={`Max ${options.price.max}`}
                  value={filters.maxPrice}
                  onChange={(event) =>
                    setFilters({
                      ...filters,
                      maxPrice: event.target.value,
                    })
                  }
                />
              </div>
            </div>
          </div>

        </div>
      </section>

      <div className={loading ? "loading-bar active" : "loading-bar"} />

      {sections.summary && (
        <section className="kpi-grid" id="overview">
          <button
            className="kpi-card accent interactive-card"
            type="button"
            onClick={resetFilters}
            title="Clear all dashboard filters"
          >
            <span>Total products</span>
            <strong>{formatNumber.format(dashboard.summary.total_products)}</strong>
            <small>Unique product IDs after filters</small>
          </button>
          <button
            className="kpi-card interactive-card"
            type="button"
            onClick={() =>
              setFilters({
                ...filters,
                maxPrice:
                  filters.maxPrice === ""
                    ? String(Math.ceil(dashboard.summary.average_price))
                    : "",
              })
            }
            title="Toggle products priced up to the current average"
          >
            <span>Average starting price</span>
            <strong>{formatMoney.format(dashboard.summary.average_price)}</strong>
            <small>Across the current selection</small>
          </button>
          <button
            className="kpi-card dark interactive-card"
            type="button"
            onClick={() =>
              setFilters({
                ...filters,
                availability:
                  filters.availability === "available" ? "all" : "available",
              })
            }
            title="Toggle available products"
          >
            <span>Available products</span>
            <strong>{dashboard.summary.availability_rate}%</strong>
            <small>
              {formatNumber.format(dashboard.summary.available_products)} available
            </small>
          </button>
        </section>
      )}

      <section className="dashboard-grid" id="charts">
        {sections.audience && hasCollectionData && (
          <article className="panel audience-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">COLLECTION MIX</p>
                <h2>Product collection</h2>
              </div>
              <span className="panel-tag">
                {formatNumber.format(dashboard.summary.collection_memberships)} memberships
              </span>
            </div>
            <p className="panel-help">
              {formatNumber.format(
                dashboard.summary.named_collection_products ?? 0,
              )} products have a named collection. {formatNumber.format(
                dashboard.summary.unassigned_collection_products ?? 0,
              )} have no named collection, and {formatNumber.format(
                dashboard.summary.multi_collection_products,
              )} appear in more than one collection, creating{" "}
              {formatNumber.format(dashboard.summary.overlap_memberships)} extra
              collection memberships.
            </p>
            <DonutChart
              data={dashboard.collections || []}
              centerValue={dashboard.summary.named_collection_products ?? 0}
              centerLabel="named products"
              onSelect={toggleCollection}
              selectedNames={filters.collections}
            />
          </article>
        )}

        {sections.categoryDonut && (
          <article className="panel category-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">PRODUCT MIX</p>
                <h2>Product category</h2>
              </div>
              <span className="panel-tag">
                {formatNumber.format(dashboard.summary.category_memberships)} memberships
              </span>
            </div>
            <p className="panel-help">
              {formatNumber.format(dashboard.summary.total_products)} unique
              product cards. {formatNumber.format(
                dashboard.summary.multi_category_products,
              )} cards appear in more than one product category.
            </p>
            <DonutChart
              data={dashboard.categories}
              centerValue={dashboard.summary.total_products}
              centerLabel="product cards"
              onSelect={toggleCategory}
              selectedNames={filters.categories}
            />
          </article>
        )}

        {sections.treemap && (
          <article className="panel treemap-panel">
            <div className="panel-heading">
              <div>
                <h2>{showCategoryTreemap ? "Product category treemap" : "Sub category treemap"}</h2>
              </div>
              <span className="panel-tag">Click a block</span>
            </div>
            <ResponsiveContainer width="100%" height={410}>
              <Treemap
                data={treemapRows}
                dataKey="value"
                nameKey="name"
                stroke="#fff"
                content={
                  <TreemapContent
                    onSelect={treemapSelectHandler}
                    selectedNames={treemapSelectedNames}
                  />
                }
              >
                <Tooltip
                  contentStyle={{ fontSize: 11, padding: "7px 9px" }}
                  itemStyle={{ fontSize: 11 }}
                  formatter={(value) => `${value} products`}
                />
              </Treemap>
            </ResponsiveContainer>
          </article>
        )}
      </section>

      {sections.products && (
        <section className="panel product-panel" id="products">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">PRODUCT DETAILS</p>
              <h2>Product details</h2>
              <p className="section-description">
                Search the current selection or refine it with the controls below.
              </p>
            </div>
            <div className="panel-actions">
              <button
                className="export-button"
                type="button"
                onClick={() => exportProductsToExcel(dashboard.products)}
                disabled={!dashboard.products.length}
              >
                Export Excel
              </button>
              <span className="panel-tag">
                Showing {dashboard.products.length} products
              </span>
            </div>
          </div>

          <div className="product-pagination">
            <div>
              Page {currentProductPage} of {totalProductPages}
              <span>
                Showing{" "}
                {dashboard.products.length
                  ? (currentProductPage - 1) * productsPerPage + 1
                  : 0}
                -
                {Math.min(
                  currentProductPage * productsPerPage,
                  dashboard.products.length,
                )}{" "}
                of {dashboard.products.length}
              </span>
            </div>
            <label>
              Rows
              <select
                value={productsPerPage}
                onChange={(event) =>
                  setProductsPerPage(Number(event.target.value))
                }
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={250}>250</option>
              </select>
            </label>
            <button
              type="button"
              onClick={() => setProductPage(Math.max(1, currentProductPage - 1))}
              disabled={currentProductPage === 1}
            >
              Prev
            </button>
            <input
              type="number"
              min="1"
              max={totalProductPages}
              value={currentProductPage}
              aria-label="Product page number"
              onChange={(event) =>
                setProductPage(
                  Math.min(
                    totalProductPages,
                    Math.max(1, Number(event.target.value) || 1),
                  ),
                )
              }
            />
            <button
              type="button"
              onClick={() =>
                setProductPage(Math.min(totalProductPages, currentProductPage + 1))
              }
              disabled={currentProductPage === totalProductPages}
            >
              Next
            </button>
          </div>

          {dashboard.products.length ? (
            <div className="table-wrap">
                <table>
                  <thead>
                    <tr className="table-heading-row">
                      <th>No.</th>
                      {showStraussPitch && <th>Image</th>}
                      <th>Product</th>
                      {hasSeriesData && <th>Series</th>}
                      {hasSeriesData && <th>Season</th>}
                      <th>Gender</th>
                      <th>Category</th>
                      {hasSubcategoryData && <th>Sub category</th>}
                      {hasCollectionData && <th>Collection</th>}
                      <th>Color</th>
                      {hasMaterialData && <th>Material</th>}
                      {hasTechnicalFeatureData && <th>Technical features</th>}
                      {hasFabricTreatmentData && <th>Fabric treatment</th>}
                      {hasConstructionData && <th>Construction</th>}
                      <th>Shop Highlights</th>
                      <th>Price range</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedProducts.map((product, index) => (
                      <tr key={product.id}>
                        <td className="number-cell">
                          {(currentProductPage - 1) * productsPerPage + index + 1}
                        </td>
                        {showStraussPitch && (
                          <td className="product-image-cell">
                            {product.color_variants?.length ? (
                              <div className="product-image-gallery">
                                {product.color_variants.map((variant) => (
                                  <a
                                    key={`${variant.color}-${variant.url}`}
                                    href={variant.url || product.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    aria-label={`Open ${product.title} in ${variant.color}`}
                                    title={`${variant.color}${
                                      variant.available
                                        ? " - Available"
                                        : " - Unavailable"
                                    }`}
                                  >
                                    <img
                                      src={variant.image || product.image}
                                      alt={`${product.title} - ${variant.color}`}
                                      loading="lazy"
                                      decoding="async"
                                    />
                                    <span>{variant.color}</span>
                                  </a>
                                ))}
                              </div>
                            ) : product.image ? (
                              <a href={product.url} target="_blank" rel="noreferrer">
                                <img src={product.image} alt={product.title} />
                              </a>
                            ) : (
                              <span className="product-image-placeholder">
                                No image
                              </span>
                            )}
                          </td>
                        )}
                        <td className="product-title-cell">
                          <a href={product.url} target="_blank" rel="noreferrer">
                            {product.title}
                          </a>
                        </td>
                        {hasSeriesData && (
                          <td className="detail-cell">
                            <DetailList
                              values={[
                                product.series_number
                                  ? `Series: ${product.series_number}`
                                  : "",
                                product.style_number
                                  ? `Style: ${product.style_number}`
                                  : "",
                              ].filter(Boolean)}
                            />
                          </td>
                        )}
                        {hasSeriesData && (
                          <td className="detail-cell">
                            <DetailList
                              values={[
                                product.season_code
                                  ? `Code: ${product.season_code}`
                                  : "",
                                product.season_range
                                  ? product.season_range
                                  : "",
                              ].filter(Boolean)}
                            />
                          </td>
                        )}
                        <td>
                          {product.audience_labels?.length
                            ? product.audience_labels.map((label, labelIndex) => {
                                const option = options.audiences.find(
                                  (item) => item.label === label,
                                );
                                return (
                                  <span key={label}>
                                    {labelIndex > 0 && ", "}
                                    <button
                                      className="table-filter-button"
                                      type="button"
                                      onClick={() =>
                                        option &&
                                        setFilters({
                                          ...filters,
                                          audiences: [option.value],
                                        })
                                      }
                                    >
                                      {label}
                                    </button>
                                  </span>
                                );
                              })
                            : "Not specified"}
                        </td>
                        <td>
                          {(product.categories || [product.category]).map(
                            (category, index) => (
                              <span key={category}>
                                {index > 0 && ", "}
                                <button
                                  className="table-filter-button"
                                  type="button"
                                  onClick={() => toggleCategory(category)}
                                >
                                  {category}
                                </button>
                              </span>
                            ),
                          )}
                        </td>
                        {hasSubcategoryData && (
                          <td>
                            {product.subcategories?.length
                              ? product.subcategories.map((subcategory, index) => (
                                  <span key={subcategory}>
                                    {index > 0 && ", "}
                                    <button
                                      className="table-filter-button"
                                      type="button"
                                      onClick={() =>
                                        setFilters({
                                          ...filters,
                                          subcategories: [subcategory],
                                        })
                                      }
                                    >
                                      {subcategory}
                                    </button>
                                  </span>
                                ))
                              : "Not specified"}
                          </td>
                        )}
                        {hasCollectionData && (
                          <td className="collection-cell">
                            {product.collections?.length
                              ? product.collections.map((collection, index) => (
                                  <span key={collection}>
                                    {index > 0 && ", "}
                                    <button
                                      className="table-filter-button"
                                      type="button"
                                      onClick={() => toggleCollection(collection)}
                                    >
                                      {collection}
                                    </button>
                                  </span>
                                ))
                              : "No named collection"}
                          </td>
                        )}
                        <td className="color-cell">
                          <DetailList
                            values={
                              product.available_colors ||
                              (product.color ? [product.color] : [])
                            }
                            fallback="No available colors"
                          />
                          {product.unavailable_colors?.length ? (
                            <div className="unavailable-colors">
                              <span>Unavailable:</span>{" "}
                              {product.unavailable_colors.join(", ")}
                            </div>
                          ) : null}
                        </td>
                        {hasMaterialData && (
                          <td className="material-cell">
                            <DetailList values={getMaterialValues(product)} />
                          </td>
                        )}
                        {hasTechnicalFeatureData && (
                          <td className="detail-cell">
                            <DetailList values={product.technical_features} />
                          </td>
                        )}
                        {hasFabricTreatmentData && (
                          <td className="detail-cell">
                            <DetailList values={product.fabric_treatment} />
                          </td>
                        )}
                        {hasConstructionData && (
                          <td className="detail-cell">
                            <DetailList values={product.construction} />
                          </td>
                        )}
                        <td>
                          {product.shop_highlights?.length ? (
                            product.shop_highlights.map((highlight) => (
                              <button
                                key={highlight}
                                type="button"
                                onClick={() =>
                                  setFilters({
                                    ...filters,
                                    shopHighlight: highlight,
                                  })
                                }
                                className="seller-badge yes"
                              >
                                {highlight}
                              </button>
                            ))
                          ) : (
                            <button
                              type="button"
                              onClick={() =>
                                setFilters({
                                  ...filters,
                                  shopHighlight: "none",
                                })
                              }
                              className="seller-badge no"
                            >
                              No highlights
                            </button>
                          )}
                        </td>
                        <td className="price-cell">{formatPrice(product)}</td>
                        <td>
                          <button
                            type="button"
                            onClick={() =>
                              setFilters({
                                ...filters,
                                availability: product.available
                                  ? "available"
                                  : "unavailable",
                              })
                            }
                            className={
                              product.available
                                ? "availability yes"
                                : "availability no"
                            }
                          >
                            {product.available ? "Available" : "Unavailable"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
          ) : (
            <div className="empty-state">
              <strong>No product rows in preview mode</strong>
              <span>Start the Python API to load the live product table.</span>
            </div>
          )}
        </section>
      )}

      {showStraussPitch && (
        <SlideDeckPanel
          id="strauss-pitch"
          eyebrow="NAN YANG TEXTILE"
          title="NAN YANG STRAUSS PITCH"
          downloadHref="/nanyang-strauss-pitch.pptx"
          extraDownloads={[
            { href: "/nictrend-ss28.pdf", label: "Download Trend PDF" },
          ]}
          slides={STRAUSS_PITCH_SLIDES}
          slideIndex={pitchSlideIndex}
          setSlideIndex={setPitchSlideIndex}
          altPrefix="NAN YANG STRAUSS PITCH"
        />
      )}

      {showArcteryxDeck && (
        <SlideDeckPanel
          id="arcteryx-cotton-groups"
          eyebrow="NAN YANG TEXTILE"
          title="NAN YANG ARC'TERYX COTTON GROUPS"
          downloadHref="/nanyang-arcteryx-cotton-groups.pptx"
          slides={ARCTERYX_COTTON_SLIDES}
          slideIndex={arcteryxSlideIndex}
          setSlideIndex={setArcteryxSlideIndex}
          altPrefix="NAN YANG ARC'TERYX COTTON GROUPS"
        />
      )}

      <footer>
        Public clothing catalog analysis from{" "}
        <a href="https://us.strauss.com" target="_blank" rel="noreferrer">
          Strauss
        </a>
        ,{" "}
        <a href="https://www.rhone.com" target="_blank" rel="noreferrer">
          Rhone
        </a>{" "}
        ,{" "}
        <a href="https://arcteryx.com/us/en" target="_blank" rel="noreferrer">
          Arc&apos;teryx
        </a>
        {" "}and{" "}
        <a href="https://shop.lululemon.com" target="_blank" rel="noreferrer">
          lululemon
        </a>
        . Product names and data belong to their respective owners.
      </footer>
    </main>
  );
}

export default App;
