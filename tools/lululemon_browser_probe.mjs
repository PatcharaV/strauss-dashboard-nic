import { spawn } from "node:child_process";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const DEFAULT_CHROME_PATHS = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
];

const DEFAULT_URLS = [
  "https://shop.lululemon.com/p/men-ss-tops/Zeroed-In-Short-Sleeve-Shirt/_/prod11680098",
  "https://shop.lululemon.com/p/men-pants/ABC-Cargo-Pant-Warpstreme-MD/_/prod11800821",
  "https://shop.lululemon.com/p/skirts-and-dresses-dresses/2-in-1-Maxi-Dress-MD/_/prod20002014",
];

function argValue(name, fallback = "") {
  const prefix = `${name}=`;
  const hit = process.argv.find((arg) => arg.startsWith(prefix));
  return hit ? hit.slice(prefix.length) : fallback;
}

function productIdFromUrl(url) {
  const match = String(url).match(/\/_\/([^/?#]+)/);
  return match ? match[1] : "";
}

async function exists(filePath) {
  try {
    await readFile(filePath);
    return true;
  } catch {
    return false;
  }
}

async function chromePath() {
  if (process.env.CHROME_PATH && (await exists(process.env.CHROME_PATH))) {
    return process.env.CHROME_PATH;
  }
  for (const candidate of DEFAULT_CHROME_PATHS) {
    if (await exists(candidate)) return candidate;
  }
  throw new Error("Chrome executable not found. Set CHROME_PATH to chrome.exe.");
}

async function urlsFromArgs() {
  const explicit = process.argv.filter((arg) => arg.startsWith("https://"));
  if (explicit.length) return explicit;

  const input = argValue("--input");
  if (input) {
    const data = JSON.parse(await readFile(input, "utf8"));
    const products = Array.isArray(data) ? data : data.products || [];
    return products
      .filter((product) => product.brand === "lululemon" && product.url)
      .slice(0, Number(argValue("--limit", "10")))
      .map((product) => product.url);
  }

  return DEFAULT_URLS;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForJson(port, timeoutMs = 30000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return;
    } catch {
      // Chrome is still starting.
    }
    await delay(500);
  }
  throw new Error("Timed out waiting for Chrome remote debugging port.");
}

async function openTab(port, url) {
  const response = await fetch(
    `http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`,
    { method: "PUT" },
  );
  if (!response.ok) {
    throw new Error(`Failed to open tab: ${response.status}`);
  }
  return response.json();
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let nextId = 1;
  const pending = new Map();

  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  });

  return new Promise((resolve, reject) => {
    ws.addEventListener("open", () => {
      resolve({
        send(method, params = {}) {
          const id = nextId++;
          ws.send(JSON.stringify({ id, method, params }));
          return new Promise((commandResolve, commandReject) => {
            pending.set(id, {
              resolve: commandResolve,
              reject: commandReject,
            });
          });
        },
        close() {
          ws.close();
        },
      });
    });
    ws.addEventListener("error", reject);
  });
}

const EXTRACT_SCRIPT = String.raw`
(() => {
  function cleanText(value) {
    return String(value || "")
      .replace(/โข/g, "TM")
      .replace(/™/g, "TM")
      .replace(/\s+/g, " ")
      .trim();
  }

  function findPdp(obj) {
    if (!obj || typeof obj !== "object") return null;
    if (Array.isArray(obj.colorAttributes) && Array.isArray(obj.productCarousel)) {
      return obj;
    }
    for (const value of Object.values(obj)) {
      const found = findPdp(value);
      if (found) return found;
    }
    return null;
  }

  function panelTexts(panel) {
    const values = [];
    for (const section of panel?.sections || []) {
      for (const attr of section?.attributes || []) {
        if (attr.text) values.push(cleanText(attr.text));
        if (attr.list?.items?.length) {
          values.push(cleanText((attr.list.title ? attr.list.title + ": " : "") + attr.list.items.join(", ")));
        }
      }
    }
    return values;
  }

  function pushUnique(values, incoming) {
    if (!incoming) return;
    const items = Array.isArray(incoming) ? incoming : [incoming];
    for (const item of items) {
      const value = cleanText(item);
      if (value && !values.includes(value)) values.push(value);
    }
  }

  const nextData = JSON.parse(document.querySelector("#__NEXT_DATA__")?.textContent || "{}");
  const pdp = findPdp(nextData);
  const productGroup = [...document.querySelectorAll('script[type="application/ld+json"]')]
    .map((script) => {
      try { return JSON.parse(script.textContent); } catch { return null; }
    })
    .filter(Boolean)
    .find((item) => item["@type"] === "ProductGroup") || {};

  const variants = Array.isArray(productGroup.hasVariant) ? productGroup.hasVariant : [];
  const byColor = new Map();
  for (const variant of variants) {
    const color = cleanText(variant.color);
    if (!color) continue;
    const offers = Array.isArray(variant.offers) ? variant.offers : [variant.offers];
    const available = offers.some((offer) => String(offer?.availability || "").includes("InStock"));
    const row = byColor.get(color) || {
      color,
      image: variant.image || "",
      available: false,
      sizes: [],
    };
    row.available = row.available || available;
    if (variant.size && !row.sizes.includes(variant.size)) row.sizes.push(cleanText(variant.size));
    if (!row.image && variant.image) row.image = variant.image;
    byColor.set(color, row);
  }

  for (const item of pdp?.productCarousel || []) {
    const color = cleanText(item?.color?.name);
    if (!color || byColor.has(color)) continue;
    const image = Array.isArray(item?.imageInfo) ? item.imageInfo[0] || "" : "";
    byColor.set(color, {
      color,
      image,
      available: true,
      sizes: [],
    });
  }

  const bodyMaterials = [];
  const innovations = [];
  for (const attr of pdp?.colorAttributes || []) {
    for (const value of panelTexts(attr.careAndContent)) {
      if (value.toLowerCase().startsWith("body:") && !bodyMaterials.includes(value)) {
        bodyMaterials.push(value);
      }
    }
    pushUnique(innovations, attr.fabricOrBenefits?.title);
    pushUnique(innovations, panelTexts(attr.fabricOrBenefits));
    pushUnique(innovations, panelTexts(attr.featuresOrIngredients));
    pushUnique(innovations, panelTexts(attr.fitOrHowToUse));
  }

  const colors = [...byColor.values()];
  return {
    url: location.href,
    title: cleanText(productGroup.name || pdp?.productSummary?.displayName || document.title),
    status: colors.length || bodyMaterials.length ? "captured" : "missing-detail",
    color_count: colors.length,
    available_colors: colors.filter((color) => color.available).map((color) => color.color),
    unavailable_colors: colors.filter((color) => !color.available).map((color) => color.color),
    color_variants: colors,
    body_materials: bodyMaterials,
    innovations,
    pdp_color_attributes: pdp?.colorAttributes?.length || 0,
    pdp_carousel_colors: pdp?.productCarousel?.length || 0,
    schema_variants: variants.length,
  };
})()
`;

async function extractFromTab(tab) {
  const client = await connect(tab.webSocketDebuggerUrl);
  try {
    await client.send("Runtime.enable");
    const timeoutMs = Number(argValue("--wait", "15000"));
    const startedAt = Date.now();
    let lastValue = null;
    while (Date.now() - startedAt < timeoutMs) {
      const result = await client.send("Runtime.evaluate", {
        expression: EXTRACT_SCRIPT,
        awaitPromise: true,
        returnByValue: true,
      });
      lastValue = result.result.value;
      if (lastValue?.status === "captured") {
        return lastValue;
      }
      await delay(1000);
    }
    return lastValue;
  } finally {
    client.close();
  }
}

async function main() {
  const port = Number(argValue("--port", "9224"));
  const profileDir = path.join(tmpdir(), `lululemon-browser-probe-${Date.now()}`);
  await mkdir(profileDir, { recursive: true });

  const chrome = spawn(await chromePath(), [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--start-minimized",
    "about:blank",
  ], {
    stdio: "ignore",
    detached: false,
  });

  try {
    await waitForJson(port);
    const results = [];
    for (const url of await urlsFromArgs()) {
      const tab = await openTab(port, url);
      const result = await extractFromTab(tab);
      results.push({
        product_id: productIdFromUrl(url),
        requested_url: url,
        ...result,
      });
    }
    const output = argValue("--output");
    if (output) {
      await writeFile(output, `${JSON.stringify(results, null, 2)}\n`, "utf8");
    }
    console.log(JSON.stringify(results, null, 2));
  } finally {
    chrome.kill();
    await delay(1000);
    await rm(profileDir, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
