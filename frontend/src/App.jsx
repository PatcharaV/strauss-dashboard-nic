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

const DEFAULT_SECTIONS = {
  summary: true,
  audience: true,
  categoryDonut: true,
  treemap: true,
  products: true,
};

const formatNumber = new Intl.NumberFormat("en-US");
const formatMoney = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function formatPrice(product) {
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

function buildQuery(filters) {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.brands.length) {
    params.set("brands", filters.brands.join(","));
  }
  if (filters.audiences.length) {
    params.set("audiences", filters.audiences.join(","));
  }
  if (filters.categories.length) {
    params.set("categories", filters.categories.join(","));
  }
  if (filters.minPrice !== "") params.set("min_price", filters.minPrice);
  if (filters.maxPrice !== "") params.set("max_price", filters.maxPrice);
  if (filters.availability !== "all") {
    params.set("availability", filters.availability);
  }
  if (filters.topSeller !== "all") {
    params.set("top_seller", filters.topSeller);
  }
  if (filters.material !== "all") {
    params.set("material", filters.material);
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
            contentStyle={{ fontSize: 10, padding: "7px 9px" }}
            itemStyle={{ fontSize: 10 }}
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
            wrapperStyle={{ fontSize: 8, lineHeight: "13px" }}
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
        <text x={x + 8} y={y + 18} fill="#fff" fontSize={10} fontWeight={700}>
          {displayName}
        </text>
      )}
      {showValue && (
        <text x={x + 8} y={y + 34} fill="rgba(255,255,255,.82)" fontSize={9}>
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

function App() {
  const [options, setOptions] = useState(demoOptions);
  const [dashboard, setDashboard] = useState(demoDashboard);
  const [filters, setFilters] = useState({
    search: "",
    brands: ["strauss"],
    audiences: [],
    categories: [],
    minPrice: "",
    maxPrice: "",
    availability: "all",
    topSeller: "all",
    material: "all",
  });
  const [sections, setSections] = useState(DEFAULT_SECTIONS);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [message, setMessage] = useState("Connecting to Python API...");
  const [filtersOpen, setFiltersOpen] = useState(true);

  const query = useMemo(() => buildQuery(filters), [filters]);
  const productCategories = options.categories;

  async function loadDashboard() {
    setLoading(true);
    try {
      const brandQuery = filters.brands.length
        ? `?brands=${encodeURIComponent(filters.brands.join(","))}`
        : "";
      const [optionsResponse, dashboardResponse] = await Promise.all([
        fetch(`/api/options${brandQuery}`),
        fetch(`/api/dashboard${query ? `?${query}` : ""}`),
      ]);
      if (!optionsResponse.ok || !dashboardResponse.ok) {
        throw new Error("API response was not successful");
      }
      setOptions(await optionsResponse.json());
      setDashboard(await dashboardResponse.json());
      setMessage("Live data from Strauss, Rhone and Arc'teryx");
    } catch {
      setMessage("Demo preview: start the Python API for live data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = setTimeout(loadDashboard, 250);
    return () => clearTimeout(timer);
  }, [query]);

  async function scrapeLatest() {
    setScraping(true);
    setMessage("Scraping the latest catalog...");
    try {
      const response = await fetch("/api/scrape", { method: "POST" });
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
      categories: [],
      minPrice: "",
      maxPrice: "",
      availability: "all",
      topSeller: "all",
      material: "all",
    });
  }

  function selectBrand(brand) {
    setFilters({
      ...filters,
      brands: [brand],
      audiences: [],
      categories: [],
    });
  }

  function toggleCategory(category) {
    setFilters({
      ...filters,
      categories: filters.categories.includes(category)
        ? filters.categories.filter((item) => item !== category)
        : [...filters.categories, category],
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

  const selectedAudienceLabels = options.audiences
    .filter((item) => filters.audiences.includes(item.value))
    .map((item) => item.label);
  const activeFilterLabels = [
    filters.search.trim() ? `Search: ${filters.search.trim()}` : null,
    ...options.brands
      .filter((item) => filters.brands.includes(item.value))
      .map((item) => item.label),
    ...selectedAudienceLabels,
    ...filters.categories,
    filters.availability === "available" ? "Available only" : null,
    filters.availability === "unavailable" ? "Unavailable only" : null,
    filters.topSeller === "yes" ? "Top seller only" : null,
    filters.topSeller === "no" ? "Not top seller" : null,
    filters.material === "specified" ? "Material specified" : null,
    filters.material === "missing" ? "Material not specified" : null,
    filters.minPrice !== "" ? `Min $${filters.minPrice}` : null,
    filters.maxPrice !== "" ? `Max $${filters.maxPrice}` : null,
  ].filter(Boolean);

  return (
    <main>
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">M</div>
          <div>
            <p className="eyebrow">PUBLIC CATALOG ANALYTICS</p>
            <h1>Multi-Brand Product Dashboard</h1>
            <p className="page-description">
              Compare Strauss, Rhone and Arc&apos;teryx public product catalogs.
            </p>
          </div>
        </div>
        <div className="header-actions">
          <div className="status">
            <span className={message.startsWith("Live") ? "dot live" : "dot"} />
            <div>
              <strong>{message}</strong>
              <small>Updated {formatDate(dashboard.scraped_at)}</small>
            </div>
          </div>
          <button
            className="primary-button"
            type="button"
            onClick={scrapeLatest}
            disabled={scraping}
          >
            {scraping ? "Scraping..." : "Scrape latest data"}
          </button>
        </div>
      </header>

      <section className="brand-switcher" aria-label="Filter by brand">
        <div className="brand-switcher-copy">
          <span className="filter-title">Choose brand</span>
          <strong>Select one brand to view its dashboard</strong>
        </div>
        <div className="brand-switcher-buttons">
          <button
            className={filters.brands.includes("strauss") ? "active" : ""}
            type="button"
            onClick={() => selectBrand("strauss")}
          >
            Strauss
          </button>
          <button
            className={filters.brands.includes("rhone") ? "active" : ""}
            type="button"
            onClick={() => selectBrand("rhone")}
          >
            Rhone
          </button>
          <button
            className={filters.brands.includes("arcteryx") ? "active" : ""}
            type="button"
            onClick={() => selectBrand("arcteryx")}
          >
            Arc&apos;Teryx
          </button>
        </div>
      </section>

      <nav className="page-nav" aria-label="Dashboard sections">
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

        <div className="filter-content">
          <div className="primary-filter-grid">
            <label className="main-search">
              <span className="filter-title">Search products</span>
              <input
                type="search"
                placeholder="Product name, material or collection..."
                value={filters.search}
                onChange={(event) =>
                  setFilters({ ...filters, search: event.target.value })
                }
              />
            </label>

            <label>
              <span className="filter-title">Category</span>
              <select
                value={
                  filters.categories.length === 1 ? filters.categories[0] : "all"
                }
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    categories:
                      event.target.value === "all" ? [] : [event.target.value],
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

            <label>
              <span className="filter-title">Top seller</span>
              <select
                value={filters.topSeller}
                onChange={(event) =>
                  setFilters({ ...filters, topSeller: event.target.value })
                }
              >
                <option value="all">All products</option>
                <option value="yes">Top sellers</option>
                <option value="no">Not top sellers</option>
              </select>
            </label>

            <label>
              <span className="filter-title">Availability</span>
              <select
                value={filters.availability}
                onChange={(event) =>
                  setFilters({ ...filters, availability: event.target.value })
                }
              >
                <option value="all">All statuses</option>
                <option value="available">Available</option>
                <option value="unavailable">Unavailable</option>
              </select>
            </label>

            <label>
              <span className="filter-title">Material</span>
              <select
                value={filters.material}
                onChange={(event) =>
                  setFilters({ ...filters, material: event.target.value })
                }
              >
                <option value="all">All materials</option>
                <option value="specified">Material specified</option>
                <option value="missing">Not specified</option>
              </select>
            </label>
          </div>

          <FilterGroup
            title="Audience / collection"
            options={options.audiences}
            selected={filters.audiences}
            onChange={(audiences) => setFilters({ ...filters, audiences })}
          />
          <div className="filter-row">
            <div className="price-control">
              <span className="filter-title">Price range (USD)</span>
              <div className="price-inputs">
                <input
                  type="number"
                  min="0"
                  aria-label="Minimum price"
                  placeholder={`Min ${options.price.min}`}
                  value={filters.minPrice}
                  onChange={(event) =>
                    setFilters({ ...filters, minPrice: event.target.value })
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
                    setFilters({ ...filters, maxPrice: event.target.value })
                  }
                />
              </div>
            </div>
            <div className="section-control">
              <span className="filter-title">Visible sections</span>
              <div className="toggle-list">
                {Object.keys(sections).map((section) => (
                  <label key={section}>
                    <input
                      type="checkbox"
                      checked={sections[section]}
                      onChange={() =>
                        setSections({ ...sections, [section]: !sections[section] })
                      }
                    />
                    {section === "categoryDonut"
                      ? "Category donut"
                      : section.charAt(0).toUpperCase() + section.slice(1)}
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className={loading ? "loading-bar active" : "loading-bar"} />

      {activeFilterLabels.length > 0 && (
        <section className="active-filter-bar">
          <div>
            <span>Active dashboard filters</span>
            <strong>{activeFilterLabels.join(" / ")}</strong>
          </div>
          <button type="button" onClick={resetFilters}>
            Clear all
          </button>
        </section>
      )}

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
            onClick={() => setFilters({ ...filters, categories: [] })}
            title="Clear category selection"
          >
            <span>Product categories</span>
            <strong>{formatNumber.format(dashboard.summary.categories)}</strong>
            <small>Across the current brand selection</small>
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
        {sections.audience && (
          <article className="panel audience-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">COLLECTION MIX</p>
                <h2>Audience & collection</h2>
              </div>
              <span className="panel-tag">
                {formatNumber.format(dashboard.summary.collection_memberships)} memberships
              </span>
            </div>
            <p className="panel-help">
              {formatNumber.format(dashboard.summary.total_products)} unique
              products. {formatNumber.format(
                dashboard.summary.multi_collection_products,
              )} products appear in more than one collection, creating{" "}
              {formatNumber.format(dashboard.summary.overlap_memberships)} extra
              collection memberships.
            </p>
            <DonutChart
              data={dashboard.audiences}
              centerValue={dashboard.summary.total_products}
              centerLabel="unique products"
              onSelect={toggleAudienceLabel}
              selectedNames={selectedAudienceLabels}
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
                <p className="eyebrow">CATEGORY SHARE</p>
                <h2>Product category treemap</h2>
              </div>
              <span className="panel-tag">Click a block</span>
            </div>
            <ResponsiveContainer width="100%" height={410}>
              <Treemap
                data={dashboard.categories}
                dataKey="value"
                nameKey="name"
                stroke="#fff"
                content={
                  <TreemapContent
                    onSelect={toggleCategory}
                    selectedNames={filters.categories}
                  />
                }
              >
                <Tooltip
                  contentStyle={{ fontSize: 10, padding: "7px 9px" }}
                  itemStyle={{ fontSize: 10 }}
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
            <span className="panel-tag">
              Showing {dashboard.products.length} products
            </span>
          </div>

          {dashboard.products.length ? (
            <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Brand</th>
                      <th>Category</th>
                      <th>Collection</th>
                      <th>Color</th>
                      <th>Material</th>
                      <th>Top seller</th>
                      <th>Price range</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.products.map((product) => (
                      <tr key={product.id}>
                        <td>
                          <a href={product.url} target="_blank" rel="noreferrer">
                            {product.title}
                          </a>
                        </td>
                        <td>
                          <button
                            className="table-filter-button"
                            type="button"
                            onClick={() =>
                              setFilters({
                                ...filters,
                                brands: [product.brand],
                                categories: [],
                              })
                            }
                          >
                            {product.brand_label}
                          </button>
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
                        <td>{product.audience_labels.join(", ")}</td>
                        <td className="color-cell">
                          {product.color || "Not specified"}
                        </td>
                        <td className="material-cell">
                          <button
                            className="table-filter-button material-button"
                            type="button"
                            onClick={() =>
                              setFilters({
                                ...filters,
                                material: product.material
                                  ? "specified"
                                  : "missing",
                              })
                            }
                          >
                            {product.material || "Not specified"}
                          </button>
                        </td>
                        <td>
                          <button
                            type="button"
                            onClick={() =>
                              setFilters({
                                ...filters,
                                topSeller: product.top_seller ? "yes" : "no",
                              })
                            }
                            className={
                              product.top_seller
                                ? "seller-badge yes"
                                : "seller-badge no"
                            }
                          >
                            {product.top_seller ? "Top seller" : "No"}
                          </button>
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

      <footer>
        Public catalog analysis from{" "}
        <a href="https://us.strauss.com" target="_blank" rel="noreferrer">
          Strauss
        </a>
        ,{" "}
        <a href="https://www.rhone.com" target="_blank" rel="noreferrer">
          Rhone
        </a>{" "}
        and{" "}
        <a href="https://arcteryx.com/us/en" target="_blank" rel="noreferrer">
          Arc&apos;teryx
        </a>
        . Product names and data belong to their respective owners.
      </footer>
    </main>
  );
}

export default App;
