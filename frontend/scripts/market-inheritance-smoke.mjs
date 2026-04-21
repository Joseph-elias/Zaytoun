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

async function expectText(locator, regex, timeoutMs = 8000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const text = (await locator.innerText().catch(() => "")).trim();
    if (regex.test(text)) return text;
    await new Promise((r) => setTimeout(r, 120));
  }
  const text = (await locator.innerText().catch(() => "")).trim();
  throw new Error(`Expected ${regex} within ${timeoutMs}ms, got "${text}"`);
}

const uniq = Date.now();
const phone = `+2126${String(uniq).slice(-8)}`;
const password = "secret123";
const storeBannerUrl = `https://example.com/store-banner-${uniq}.jpg`;
const productPhotoUrl = `https://example.com/product-photo-${uniq}.jpg`;
const updatedDescription = `Updated description ${uniq}`;

const registered = await api("/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    full_name: "Market Smoke Farmer",
    phone,
    role: "farmer",
    password,
    terms_accepted: true,
    data_consent_accepted: true,
    consent_version: CONSENT_VERSION,
  }),
});
assert(registered.ok, `register failed: ${registered.status} ${JSON.stringify(registered.body)}`);

const login = await api("/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ phone, password, legal_acknowledged: true }),
});
assert(login.ok, `login failed: ${login.status} ${JSON.stringify(login.body)}`);
const session = login.body;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

await page.goto(`${WEB}/index.html`);
await page.evaluate((s) => localStorage.setItem("worker_radar_session", JSON.stringify(s)), session);
await page.goto(`${WEB}/market.html`, { waitUntil: "networkidle" });

await page.click("#open-store-profile-panel-btn");
await page.fill('#store-profile-form input[name="store_name"]', `Smoke Store ${uniq}`);
await page.fill('#store-profile-form input[name="store_opening_hours"]', "Mon-Sat 08:00-18:00");
await page.evaluate((url) => {
  const input = document.querySelector('#store-profile-form input[name="store_banner_url"]');
  if (input) input.value = url;
}, storeBannerUrl);
await page.click('#store-profile-form button[type="submit"]');
await expectText(page.locator("#store-profile-message"), /saved/i, 10000);

await page.click("#open-listing-panel-btn");
await page.fill('#market-item-form input[name="item_name"]', `Smoke Oil ${uniq}`);
await page.fill('#market-item-form input[name="unit_label"]', "liter");
await page.fill('#market-item-form input[name="price_per_unit"]', "12.5");
await page.fill('#market-item-form input[name="quantity_available"]', "25");
await page.fill('#market-item-form input[name="pickup_location"]', "Smoke Village");
await page.fill('#market-item-form textarea[name="description"]', `Initial description ${uniq}`);
await page.evaluate((url) => {
  const input = document.querySelector('#market-item-form input[name="photo_url"]');
  if (input) input.value = url;
}, productPhotoUrl);
await page.click('#market-item-form button[type="submit"]');
await expectText(page.locator("#market-item-message"), /saved/i, 10000);

await page.waitForSelector("[data-my-item-id]");
const createdCard = page.locator("[data-my-item-id]").first();
const createdLogoSrc = await createdCard.locator(".market-logo").getAttribute("src");
assert(
  String(createdLogoSrc || "").includes(storeBannerUrl),
  `created listing logo does not inherit store banner: got ${createdLogoSrc}`
);

await createdCard.locator("button[data-edit-item]").click();
const editForm = createdCard.locator("form[data-edit-item-form]");
await editForm.waitFor();
await editForm.locator('textarea[name="description"]').fill(updatedDescription);
await editForm.locator('button[type="submit"]').click();
await expectText(page.locator("#market-item-message"), /updated/i, 10000);

await page.waitForSelector("[data-my-item-id]");
const updatedCard = page.locator("[data-my-item-id]").first();
const updatedLogoSrc = await updatedCard.locator(".market-logo").getAttribute("src");
assert(
  String(updatedLogoSrc || "").includes(storeBannerUrl),
  `updated listing logo does not inherit store banner: got ${updatedLogoSrc}`
);
const updatedDescriptionText = (await updatedCard.locator(".market-description").nth(1).innerText()).trim();
assert(
  updatedDescriptionText.includes(updatedDescription),
  `updated description not reflected in card: got "${updatedDescriptionText}"`
);

console.log(`MARKET_INHERITANCE_SMOKE_PASS banner=${storeBannerUrl}`);
await browser.close();
