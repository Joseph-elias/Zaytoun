import { chromium } from "playwright";

const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:5173";
const CONSENT_VERSION = "2026-04-13";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { ok: res.ok, status: res.status, body };
}

async function registerAndLogin({ fullName, phone, role, password }) {
  const registered = await api("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      full_name: fullName,
      phone,
      role,
      password,
      terms_accepted: true,
      data_consent_accepted: true,
      consent_version: CONSENT_VERSION,
    }),
  });
  assert(registered.ok, `register failed for ${role}: ${registered.status} ${JSON.stringify(registered.body)}`);

  const login = await api("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, password, legal_acknowledged: true }),
  });
  assert(login.ok, `login failed for ${role}: ${login.status} ${JSON.stringify(login.body)}`);
  return login.body;
}

const now = Date.now();
const password = "secret123";
const farmerPhone = `+2125${String(now).slice(-8)}`;
const customerPhone = `+2124${String(now).slice(-8)}`;

const farmerSession = await registerAndLogin({
  fullName: "Keyboard Farmer",
  phone: farmerPhone,
  role: "farmer",
  password,
});
const customerSession = await registerAndLogin({
  fullName: "Keyboard Customer",
  phone: customerPhone,
  role: "customer",
  password,
});

const farmerAuth = { Authorization: `Bearer ${farmerSession.access_token}`, "Content-Type": "application/json" };
const customerAuth = { Authorization: `Bearer ${customerSession.access_token}`, "Content-Type": "application/json" };

const itemRes = await api("/market/items", {
  method: "POST",
  headers: farmerAuth,
  body: JSON.stringify({
    item_name: `Keyboard Oil ${now}`,
    description: "Keyboard smoke listing",
    brand_logo_url: null,
    photo_url: null,
    pickup_location: "Keyboard Village",
    unit_label: "liter",
    linked_inventory_item_id: null,
    price_per_unit: 15,
    quantity_available: 20,
    is_active: true,
  }),
});
assert(itemRes.ok, `item create failed: ${itemRes.status} ${JSON.stringify(itemRes.body)}`);
const marketItemId = itemRes.body?.id;
assert(marketItemId, "item id missing");

const orderRes = await api("/market/orders", {
  method: "POST",
  headers: customerAuth,
  body: JSON.stringify({
    market_item_id: marketItemId,
    quantity_ordered: 2,
    note: "Keyboard smoke order",
  }),
});
assert(orderRes.ok, `order create failed: ${orderRes.status} ${JSON.stringify(orderRes.body)}`);
const orderId = orderRes.body?.id;
assert(orderId, "order id missing");

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

await page.goto(`${WEB}/index.html`);
await page.evaluate((s) => localStorage.setItem("worker_radar_session", JSON.stringify(s)), farmerSession);
await page.goto(`${WEB}/market.html`, { waitUntil: "networkidle" });

await page.waitForSelector("#open-store-profile-panel-btn");
await page.focus("#open-store-profile-panel-btn");
await page.keyboard.press("Enter");
await page.waitForFunction(() => {
  const panel = document.getElementById("store-profile-card");
  return panel && !panel.classList.contains("is-hidden");
});
await page.keyboard.press("Escape");
await page.waitForFunction(() => {
  const panel = document.getElementById("store-profile-card");
  return panel && panel.classList.contains("is-hidden");
});
let activeId = await page.evaluate(() => document.activeElement?.id || "");
assert(activeId === "open-store-profile-panel-btn", `focus did not return to store opener: got ${activeId}`);

await page.waitForSelector('[data-open-order-full]');
await page.focus('[data-open-order-full]');
await page.keyboard.press(" ");
await page.waitForFunction(() => {
  const panel = document.getElementById("market-orders-panel");
  return panel && !panel.classList.contains("is-hidden");
});

const labelText = await page.locator("#orders-panel-order-label").innerText();
assert(labelText.includes(orderId.slice(0, 8)), `orders panel did not open selected order: ${labelText}`);

for (let i = 0; i < 20; i += 1) {
  await page.keyboard.press("Tab");
}
const trapped = await page.evaluate(() => {
  const panel = document.getElementById("market-orders-panel");
  const active = document.activeElement;
  return Boolean(panel && active && panel.contains(active));
});
assert(trapped, "Tab focus escaped orders panel");

await page.keyboard.press("Escape");
await page.waitForFunction(() => {
  const panel = document.getElementById("market-orders-panel");
  return panel && panel.classList.contains("is-hidden");
});
const focusReturned = await page.evaluate(() => {
  const active = document.activeElement;
  if (!active) return false;
  if (active.id === "open-orders-panel-btn") return true;
  if (active.getAttribute("data-open-order-full")) return true;
  return false;
});
assert(focusReturned, "focus did not return to orders opener");

console.log(`MARKET_KEYBOARD_SMOKE_PASS order=${orderId.slice(0, 8)}`);
await browser.close();
