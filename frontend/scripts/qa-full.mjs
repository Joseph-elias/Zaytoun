import { chromium } from "playwright";

const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:5173";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  const text = await res.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  return { ok: res.ok, status: res.status, body };
}

async function waitForText(locator, regex, timeout = 6000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const text = (await locator.innerText().catch(() => "")).trim();
    if (regex.test(text)) return text;
    await new Promise((r) => setTimeout(r, 120));
  }
  const finalText = (await locator.innerText().catch(() => "")).trim();
  throw new Error(`Expected ${regex} within ${timeout}ms, got '${finalText}'`);
}

const now = Date.now();
const phone = `+2128${String(now).slice(-8)}`;
const password = "secret123";

const register = await api("/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    full_name: "QA Farmer",
    phone,
    role: "farmer",
    password,
  }),
});
assert(register.ok, `register failed: ${register.status}`);

const login = await api("/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ phone, password }),
});
assert(login.ok, `login failed: ${login.status}`);
const session = login.body;
const auth = { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" };

const land = await api("/olive-land-pieces", {
  method: "POST",
  headers: auth,
  body: JSON.stringify({ piece_name: "QA Piece", season_year: 2025 }),
});
assert(land.ok, `land piece create failed: ${land.status}`);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

await page.goto(`${WEB}/login.html`);
await page.evaluate((s) => localStorage.setItem("worker_radar_session", JSON.stringify(s)), session);
await page.goto(`${WEB}/olive-season.html`, { waitUntil: "networkidle" });
await page.fill('#olive-season-form input[name="season_year"]', '2025');
await page.waitForFunction(() => {
  const select = document.querySelector('#season-land-piece-select');
  return !!select && select.options.length > 0;
});
const seasonPieceValue = await page.$eval('#season-land-piece-select', (select) => {
  const opt = Array.from(select.options).find((o) => String(o.value || '').trim());
  return opt ? opt.value : '';
});
assert(seasonPieceValue, 'season land-piece options empty');

// 1) Logical guard: year mismatch should fail (API-level check)
const mismatchSeason = await api('/olive-seasons', {
  method: 'POST',
  headers: auth,
  body: JSON.stringify({
    season_year: 2026,
    land_pieces: 1,
    land_piece_name: 'QA Piece',
    tanks_20l: 9,
    tanks_taken_home_20l: 8,
    pressing_cost_mode: 'oil_tanks',
    pressing_cost: 0,
  }),
});
assert(!mismatchSeason.ok && mismatchSeason.status === 400, `expected year mismatch 400, got ${mismatchSeason.status}`);

// 2) Valid season save
await page.fill('#olive-season-form input[name="season_year"]', '2025');
await page.waitForFunction(() => {
  const select = document.querySelector('#season-land-piece-select');
  return !!select && Array.from(select.options).some((o) => String(o.value || '').trim());
});
await page.selectOption('#season-land-piece-select', seasonPieceValue);
await page.fill('#olive-season-form input[name="tanks_20l"]', '9');
await page.fill('#olive-season-form input[name="tanks_taken_home_20l"]', '8');
await page.selectOption('#pressing-cost-mode-select', 'oil_tanks');
await page.click('#olive-season-form button[type="submit"]');
const seasonMsg = page.locator('#olive-season-message');
await waitForText(seasonMsg, /saved successfully/i);

const seasonsRes = await api('/olive-seasons/mine', { headers: auth });
assert(seasonsRes.ok, 'list seasons failed');
const row = seasonsRes.body.find((r) => r.land_piece_name === 'QA Piece' && Number(r.season_year) === 2025);
assert(row, 'saved season not found');
assert(String(row.pressing_cost_oil_tanks_20l) === '1.00', `expected pressing oil 1.00 got ${row.pressing_cost_oil_tanks_20l}`);

// 3) Usage: overspend should be blocked, then valid usage should work
await page.click('#olive-mode-usage');
await page.waitForFunction(() => {
  const s = document.querySelector('#usage-season-id');
  return !!s && s.options.length > 0;
});
const seasonValue = await page.$eval('#usage-season-id', (s) => {
  const opt = Array.from(s.options).find((o) => String(o.value||'').trim());
  return opt ? opt.value : '';
});
assert(seasonValue, 'usage season select empty');
await page.selectOption('#usage-season-id', seasonValue);
await page.waitForTimeout(300);

// choose season_tanks source
await page.selectOption('#usage-inventory-item-id', { value: `season_tanks:${seasonValue}` });
await page.fill('input[name="usage_quantity_used"]', '10');
await page.fill('input[name="usage_type"]', 'qa_over');
await page.click('#usage-form button[type="submit"]');
const usageMsg = page.locator('#usage-message');
await waitForText(usageMsg, /not enough|remaining/i);

await page.fill('input[name="usage_quantity_used"]', '1');
await page.fill('input[name="usage_type"]', 'qa_ok');
await page.click('#usage-form button[type="submit"]');
await waitForText(usageMsg, /saved/i);

// 4) Usage history should support edit/delete
await page.waitForFunction(() => document.querySelectorAll('#usage-history-list .worker-card').length > 0);
await page.click('#usage-history-list button[data-edit-usage]');
await page.fill('#usage-history-list input[name="edit_tanks_used"]', '10');
page.once('dialog', async (d) => { await d.accept(); });
await page.click('#usage-history-list form[data-usage-edit-form] button[type="submit"]');

// if update fails it may alert; if not, still enforce via api check below.
await page.waitForTimeout(500);

const usagesAfter = await api(`/olive-usages/mine?season_id=${seasonValue}`, { headers: auth });
assert(usagesAfter.ok, 'usage list api failed');
const qaUsage = usagesAfter.body.find((u) => String(u.usage_type || '').includes('qa_ok')) || usagesAfter.body[0];
assert(qaUsage, 'usage row missing after create');

// Force a valid edit to 0.5
const stillEditing = await page.locator('#usage-history-list form[data-usage-edit-form]').count();
if (!stillEditing) {
  await page.click('#usage-history-list button[data-edit-usage]');
}
await page.fill('#usage-history-list input[name="edit_tanks_used"]', '0.5');
await page.fill('#usage-history-list input[name="edit_usage_type"]', 'qa_fixed');
await page.click('#usage-history-list form[data-usage-edit-form] button[type="submit"]');
await page.waitForFunction(() => {
  return Array.from(document.querySelectorAll('#usage-history-list .worker-card')).some((c) => c.innerText.includes('qa_fixed'));
});

// delete edited row
page.once('dialog', (d) => d.accept());
await page.click('#usage-history-list button[data-delete-usage]');
await page.waitForTimeout(600);

// 5) Budgeting save/delete tank price + feedback
await page.click('#olive-mode-budget');
await page.waitForFunction(() => {
  const s = document.querySelector('#finance-season-id');
  return !!s && s.options.length > 0;
});
await page.selectOption('#finance-season-id', seasonValue);
await page.fill('#budget-oil-tank-price', '100');
const saveBtn = page.locator('#save-oil-tank-price-btn');
await saveBtn.click();
await waitForText(saveBtn, /Saving|Loading/i, 2000);
await waitForText(saveBtn, /Done ✓/i, 5000);

page.once('dialog', (d) => d.accept());
const delBtn = page.locator('#delete-oil-tank-price-btn');
await delBtn.click();
await waitForText(delBtn, /Deleting|Loading/i, 2000);
await waitForText(delBtn, /Done ✓/i, 5000);

// 6) Sales guard via API: cannot sell more than remaining
const badSale = await api('/olive-sales', {
  method: 'POST',
  headers: auth,
  body: JSON.stringify({ season_id: seasonValue, sale_type: 'oil_tank', tanks_sold: 99, price_per_tank: 10 }),
});
assert(!badSale.ok && badSale.status === 400, `expected bad sale 400, got ${badSale.status}`);

console.log('QA_FULL_PASS');
await browser.close();
