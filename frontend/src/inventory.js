import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireRole } from "./session.js";

const session = requireRole("farmer", "./workers.html");
const isEmbedded = new URLSearchParams(window.location.search).get("embedded") === "1";

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");

const refreshSummaryBtn = document.getElementById("refresh-summary-btn");
const refreshItemsBtn = document.getElementById("refresh-items-btn");
const inventoryKpis = document.getElementById("inventory-kpis");
const inventoryYearInput = document.getElementById("inventory-year-input");
const carryOverBtn = document.getElementById("carry-over-btn");
const inventoryYearMessage = document.getElementById("inventory-year-message");

const form = document.getElementById("inventory-item-form");
const formMessage = document.getElementById("inventory-item-message");
const itemsList = document.getElementById("inventory-items-list");

let seasons = [];
let inventoryItems = [];

function currentYear() {
  return new Date().getFullYear();
}

function selectedYear() {
  const raw = String(inventoryYearInput?.value || "").trim();
  const year = Number(raw);
  if (!Number.isFinite(year)) return currentYear();
  return year;
}

if (inventoryYearInput && !inventoryYearInput.value) {
  inventoryYearInput.value = String(currentYear());
}

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (farmer).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "inventory.html");
}
if (isEmbedded) {
  document.querySelector(".page")?.classList.add("embedded-view");
  document.querySelector(".hero")?.classList.add("is-hidden");
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setMessage(text, ok = true) {
  formMessage.textContent = text;
  formMessage.className = `message ${ok ? "success" : "error"}`;
}

function setYearMessage(text, ok = true) {
  if (!inventoryYearMessage) return;
  inventoryYearMessage.textContent = text;
  inventoryYearMessage.className = `message ${ok ? "success" : "error"}`;
}

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function money(v) {
  return toNum(v).toFixed(2);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, { headers: authHeaders(), ...options });
  if (response.status === 401 || response.status === 403) {
    clearSession();
    window.location.href = "./login.html";
    return null;
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const detail = err?.detail?.[0]?.msg || err?.detail || "Request failed";
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }

  if (response.status === 204) return null;
  return response.json();
}

function renderSummary() {
  const year = selectedYear();
  const seasonRows = seasons.filter((row) => Number(row.season_year) === year);

  const takenHomeTanks = seasonRows.reduce((acc, row) => acc + toNum(row.tanks_taken_home_20l), 0);
  const producedKg = seasonRows.reduce((acc, row) => acc + toNum(row.kg_per_land_piece ?? row.actual_chonbol), 0);
  const soldTanks = seasonRows.reduce((acc, row) => acc + toNum(row.sold_tanks), 0);
  const usedTanks = seasonRows.reduce((acc, row) => acc + toNum(row.used_tanks), 0);
  const remainingTanks = seasonRows.reduce((acc, row) => acc + toNum(row.remaining_tanks), 0);

  const cards = [
    { title: "Tanks Taken Home", value: money(takenHomeTanks), caption: `Tanks entered into inventory (${year})` },
    { title: "Produced KG", value: money(producedKg), caption: `KG per piece or actual chonbol (${year})` },
    { title: "Sold Tanks", value: money(soldTanks), caption: `From sales converted to tanks (${year})` },
    { title: "Used Tanks", value: money(usedTanks), caption: `From usage tab (${year})` },
    { title: "Remaining Tanks", value: money(remainingTanks), caption: `Produced - sold - used (${year})` },
  ];

  inventoryKpis.innerHTML = cards
    .map(
      (card) => `
        <article class="insight-kpi-card">
          <p class="insight-kpi-title">${card.title}</p>
          <p class="insight-kpi-value">${card.value}</p>
          <p class="insight-kpi-caption">${card.caption}</p>
        </article>
      `,
    )
    .join("");
}

function itemCard(item) {
  return `
    <article class="worker-card" data-item-id="${item.id}">
      <div class="list-head">
        <h3>${item.item_name}</h3>
        <span class="badge day">${money(item.quantity_on_hand)} ${item.unit_label}</span>
      </div>
      <div class="worker-grid">
        <div><strong>Year:</strong> ${item.inventory_year}</div>
        <div><strong>Default Price:</strong> ${item.default_price_per_unit === null ? "-" : money(item.default_price_per_unit)}</div>
        <div><strong>Unit:</strong> ${item.unit_label}</div>
        <div class="full"><strong>Notes:</strong> ${item.notes || "-"}</div>
      </div>
      <div class="actions-row">
        <button class="btn ghost" type="button" data-edit-item="${item.id}">Edit Qty/Price</button>
        <button class="btn danger" type="button" data-delete-item="${item.id}">Delete</button>
      </div>
    </article>
  `;
}

function renderItems() {
  itemsList.innerHTML = inventoryItems.length ? inventoryItems.map(itemCard).join("") : "No custom inventory items yet for this year.";
}

async function loadData() {
  const year = selectedYear();
  const [seasonRows, items] = await Promise.all([
    requestJson(`${API_BASE}/olive-seasons/mine`),
    requestJson(`${API_BASE}/olive-inventory-items/mine?inventory_year=${encodeURIComponent(String(year))}`),
  ]);

  seasons = seasonRows || [];
  inventoryItems = items || [];
  renderSummary();
  renderItems();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    inventory_year: selectedYear(),
    item_name: String(form.elements.item_name.value || "").trim(),
    unit_label: String(form.elements.unit_label.value || "").trim(),
    quantity_on_hand: Number(form.elements.quantity_on_hand.value || 0),
    default_price_per_unit: String(form.elements.default_price_per_unit.value || "").trim() ? Number(form.elements.default_price_per_unit.value) : null,
    notes: String(form.elements.notes.value || "").trim() || null,
  };

  setMessage("Saving item...", true);
  try {
    await requestJson(`${API_BASE}/olive-inventory-items`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    form.reset();
    setMessage("Inventory item saved.", true);
    await loadData();
  } catch (error) {
    setMessage(error.message || "Could not save item", false);
  }
});

itemsList.addEventListener("click", async (event) => {
  const editBtn = event.target.closest("button[data-edit-item]");
  if (editBtn) {
    const id = editBtn.dataset.editItem;
    const item = inventoryItems.find((row) => row.id === id);
    if (!item) return;

    const qtyRaw = window.prompt("New quantity on hand", String(item.quantity_on_hand ?? 0));
    if (qtyRaw === null) return;
    const priceRaw = window.prompt("New default price per unit (leave empty for none)", item.default_price_per_unit === null ? "" : String(item.default_price_per_unit));
    if (priceRaw === null) return;

    const payload = {
      quantity_on_hand: Number(qtyRaw),
      default_price_per_unit: String(priceRaw).trim() ? Number(priceRaw) : null,
    };

    try {
      await requestJson(`${API_BASE}/olive-inventory-items/${id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      await loadData();
    } catch (error) {
      setMessage(error.message || "Could not update item", false);
    }
    return;
  }

  const deleteBtn = event.target.closest("button[data-delete-item]");
  if (!deleteBtn) return;
  const id = deleteBtn.dataset.deleteItem;
  if (!window.confirm("Delete this inventory item?")) return;

  try {
    await requestJson(`${API_BASE}/olive-inventory-items/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    await loadData();
  } catch (error) {
    setMessage(error.message || "Could not delete item", false);
  }
});

carryOverBtn?.addEventListener("click", async () => {
  const toYear = selectedYear();
  const fromYear = toYear - 1;

  if (!window.confirm(`Carry over all remaining inventory from ${fromYear} to ${toYear}?`)) return;

  setYearMessage("Carrying over inventory...", true);
  try {
    const out = await requestJson(`${API_BASE}/olive-inventory-items/carry-over`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ from_year: fromYear, to_year: toYear }),
    });
    setYearMessage(`Carry over complete. ${out?.copied_count ?? 0} items copied.`, true);
    await loadData();
  } catch (error) {
    setYearMessage(error.message || "Could not carry over inventory", false);
  }
});

inventoryYearInput?.addEventListener("change", () => {
  setYearMessage("");
  loadData().catch((error) => {
    inventoryKpis.innerHTML = `<p class="message error">${error.message || "Could not load inventory"}</p>`;
  });
});

refreshSummaryBtn.addEventListener("click", loadData);
refreshItemsBtn.addEventListener("click", loadData);

loadData().catch((error) => {
  inventoryKpis.innerHTML = `<p class="message error">${error.message || "Could not load inventory"}</p>`;
});

