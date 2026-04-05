import { chromium } from "playwright";

const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:5173";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${JSON.stringify(data)}`);
  }
  return data;
}

const now = Date.now();
const phone = `+2129${String(now).slice(-8)}`;
const password = "secret123";

await api("/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    full_name: "UI Smoke Farmer",
    phone,
    role: "farmer",
    password,
  }),
});

const session = await api("/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ phone, password }),
});

const auth = { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" };

await api("/olive-land-pieces", {
  method: "POST",
  headers: auth,
  body: JSON.stringify({ piece_name: "UI Smoke Piece", season_year: 2026 }),
});

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

await page.goto(`${WEB}/login.html`);
await page.evaluate((sess) => {
  localStorage.setItem("worker_radar_session", JSON.stringify(sess));
}, session);

await page.goto(`${WEB}/olive-season.html`, { waitUntil: "networkidle" });

// Season save flow (Add/Save)
await page.fill('#olive-season-form input[name="season_year"]', '2026');
await page.selectOption('#season-land-piece-select', { label: 'UI Smoke Piece' });
await page.fill('#olive-season-form input[name="estimated_chonbol"]', '5');
await page.fill('#olive-season-form input[name="actual_chonbol"]', '5');
await page.fill('#olive-season-form input[name="kg_per_land_piece"]', '500');
await page.fill('#olive-season-form input[name="tanks_20l"]', '8');
await page.fill('#olive-season-form input[name="tanks_taken_home_20l"]', '6');

const saveSeasonBtn = page.locator('#olive-season-form button[type="submit"]');
await saveSeasonBtn.click();
await expectTextSoon(saveSeasonBtn, /Saving|Loading/, 1500);
await expectTextSoon(saveSeasonBtn, /Done ✓/, 3000);

// Open budgeting tab and test Save price
await page.click('#olive-mode-budget');
await page.waitForFunction(() => {
  const select = document.querySelector('#finance-season-id');
  return !!select && select.options.length > 0;
});
const financeSeasonValue = await page.$eval('#finance-season-id', (select) => {
  const firstNonEmpty = Array.from(select.options).find((opt) => String(opt.value || '').trim());
  return firstNonEmpty ? firstNonEmpty.value : '';
});
assert(financeSeasonValue, 'No finance season option available');
await page.selectOption('#finance-season-id', financeSeasonValue);
await page.fill('#budget-oil-tank-price', '130');

const savePriceBtn = page.locator('#save-oil-tank-price-btn');
await savePriceBtn.click();
await expectTextSoon(savePriceBtn, /Saving|Loading/, 1500);
await expectTextSoon(savePriceBtn, /Done ✓/, 3000);

// Delete single price
page.once('dialog', (dialog) => dialog.accept());
const deletePriceBtn = page.locator('#delete-oil-tank-price-btn');
await deletePriceBtn.click();
await expectTextSoon(deletePriceBtn, /Deleting|Loading/, 1500);
await expectTextSoon(deletePriceBtn, /Done ✓/, 3000);

// Clear all prices (Delete action)
page.once('dialog', (dialog) => dialog.accept());
const clearAllBtn = page.locator('#clear-all-oil-tank-prices-btn');
await clearAllBtn.click();
await expectTextSoon(clearAllBtn, /Clearing|Loading/, 1500);
await expectTextSoon(clearAllBtn, /Done ✓/, 3000);

// Season delete flow (Delete)
await page.click('#olive-mode-season');
await page.waitForSelector('[data-edit-season]');
await page.click('[data-edit-season]');
page.once('dialog', (dialog) => dialog.accept());
const deleteSeasonBtn = page.locator('#delete-season-btn');
await deleteSeasonBtn.click();
await expectTextSoon(deleteSeasonBtn, /Deleting|Loading/, 1500);
await expectTextSoon(deleteSeasonBtn, /Done ✓/, 3000);

console.log('UI_FEEDBACK_SMOKE_PASS');

await browser.close();

async function expectTextSoon(locator, regex, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const text = (await locator.innerText().catch(() => '')).trim();
    if (regex.test(text)) return;
    await new Promise((r) => setTimeout(r, 80));
  }
  const finalText = (await locator.innerText().catch(() => '')).trim();
  throw new Error(`Expected ${regex} within ${timeoutMs}ms, got "${finalText}"`);
}
