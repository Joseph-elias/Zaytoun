import { API_BASE } from "./config.js";
import { authHeaders, clearSession } from "./session.js";

const seasonsList = document.getElementById("olive-seasons-list");
const form = document.getElementById("olive-season-form");
const deleteBtn = document.getElementById("delete-season-btn");
const kgNeededInput = document.getElementById("kg-needed-per-tank");
const messageEl = document.getElementById("olive-season-message");
const pressingModeSelect = form?.elements?.pressing_cost_mode;

function toNum(v) {
  const raw = String(v ?? "").trim();
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function calculateKgPerTank(kgPerLandPiece, actualChonbol, tanks) {
  const baseKg = kgPerLandPiece !== null ? kgPerLandPiece : actualChonbol;
  if (baseKg === null || tanks === null || tanks <= 0) return "-";
  return (baseKg / tanks).toFixed(2);
}

function applyPressingModeUi() {
  if (!form) return;
  const mode = String(form.elements.pressing_cost_mode?.value || "money").trim();
  const modeBlocks = Array.from(form.querySelectorAll("[data-pressing-mode]"));
  for (const block of modeBlocks) {
    const blockMode = String(block.getAttribute("data-pressing-mode") || "").trim();
    block.classList.toggle("is-hidden", blockMode !== mode);
  }

  const takenHomeInput = form.elements.tanks_taken_home_20l;
  if (takenHomeInput) {
    const lock = false;
    takenHomeInput.readOnly = lock;
    takenHomeInput.placeholder = "Tanks that enter inventory";
  }

  const pressingOilInput = form.elements.pressing_cost_oil_tanks_20l;
  if (pressingOilInput) {
    pressingOilInput.readOnly = mode === "oil_tanks";
  }

  recomputePressingOilFromTakenHome();
}

function recomputePressingOilFromTakenHome() {
  if (!form) return;
  const mode = String(form.elements.pressing_cost_mode?.value || "money").trim();
  if (mode !== "oil_tanks") return;

  const produced = toNum(form.elements.tanks_20l?.value);
  const takenHome = toNum(form.elements.tanks_taken_home_20l?.value);

  if (produced === null || takenHome === null) {
    if (form.elements.pressing_cost_oil_tanks_20l) form.elements.pressing_cost_oil_tanks_20l.value = "";
    return;
  }

  const pressingOil = produced - takenHome;
  if (form.elements.pressing_cost_oil_tanks_20l) {
    form.elements.pressing_cost_oil_tanks_20l.value = pressingOil.toFixed(2);
  }
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

function fillForm(item) {
  form.elements.season_id.value = item.id;
  form.elements.season_year.value = String(item.season_year ?? "");
  form.elements.land_pieces.value = String(item.land_pieces ?? 1);
  form.elements.land_piece_name.value = item.land_piece_name || "";
  form.elements.estimated_chonbol.value = item.estimated_chonbol ?? "";
  form.elements.actual_chonbol.value = item.actual_chonbol ?? "";
  form.elements.kg_per_land_piece.value = item.kg_per_land_piece ?? "";
  form.elements.tanks_20l.value = item.tanks_20l ?? "";
  if (form.elements.tanks_taken_home_20l) {
    form.elements.tanks_taken_home_20l.value = item.tanks_taken_home_20l ?? "";
  }
  if (form.elements.pressing_cost_mode) {
    form.elements.pressing_cost_mode.value = item.pressing_cost_mode || "money";
  }
  if (form.elements.pressing_cost) {
    form.elements.pressing_cost.value = item.pressing_cost ?? "";
  }
  if (form.elements.pressing_cost_oil_tanks_20l) {
    form.elements.pressing_cost_oil_tanks_20l.value = item.pressing_cost_oil_tanks_20l ?? "";
  }
  if (form.elements.pressing_cost_oil_tank_unit_price) {
    form.elements.pressing_cost_oil_tank_unit_price.value = item.pressing_cost_oil_tank_unit_price ?? "";
  }
  form.elements.notes.value = item.notes || "";
  if (deleteBtn) deleteBtn.hidden = false;

  const kgPerLandPiece = toNum(form.elements.kg_per_land_piece.value);
  const actual = toNum(form.elements.actual_chonbol.value);
  const tanks = toNum(form.elements.tanks_20l.value);
  if (kgNeededInput) {
    kgNeededInput.value = calculateKgPerTank(kgPerLandPiece, actual, tanks);
  }

  applyPressingModeUi();

  if (messageEl) {
    messageEl.textContent = "Edit mode: update fields, then click Save Season.";
    messageEl.className = "message success";
  }
}

function patchSeasonPayload(payload) {
  if (!form || !payload || typeof payload !== "object") return payload;

  const mode = String(form.elements.pressing_cost_mode?.value || payload.pressing_cost_mode || "money").trim();
  const produced = toNum(form.elements.tanks_20l?.value);
  const takenHomeInput = toNum(form.elements.tanks_taken_home_20l?.value);
  const pressingMoney = toNum(form.elements.pressing_cost?.value);

  payload.pressing_cost_mode = mode;

  if (mode === "oil_tanks") {
    const computedPressingOil =
      produced !== null && takenHomeInput !== null
        ? produced - takenHomeInput
        : null;
    payload.pressing_cost = 0;
    payload.pressing_cost_oil_tanks_20l = computedPressingOil;
    payload.tanks_taken_home_20l = takenHomeInput;
  } else {
    payload.pressing_cost = pressingMoney;
    payload.pressing_cost_oil_tanks_20l = null;
    payload.tanks_taken_home_20l = takenHomeInput ?? produced;
  }

  return payload;
}

(function installFetchPatch() {
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    try {
      const url = typeof input === "string" ? input : String(input?.url || "");
      const method = String(init?.method || "GET").toUpperCase();
      const isSeasonMutation =
        (url.startsWith(`${API_BASE}/olive-seasons`) || url.includes("/olive-seasons/")) &&
        (method === "POST" || method === "PATCH");

      if (isSeasonMutation && typeof init.body === "string") {
        const payload = JSON.parse(init.body);
        const patched = patchSeasonPayload(payload);
        init = { ...init, body: JSON.stringify(patched) };
      }
    } catch {
      // Keep original request if payload patching fails.
    }

    return originalFetch(input, init);
  };
})();

if (form) {
  const maybeRecompute = () => recomputePressingOilFromTakenHome();
  form.elements.tanks_20l?.addEventListener("input", maybeRecompute);
  form.elements.tanks_taken_home_20l?.addEventListener("input", maybeRecompute);
  pressingModeSelect?.addEventListener("change", applyPressingModeUi);
  form.addEventListener("reset", () => setTimeout(applyPressingModeUi, 0));
  applyPressingModeUi();
}

if (seasonsList && form) {
  seasonsList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-edit-season]");
    if (!btn) return;

    const seasonId = btn.dataset.editSeason;
    if (!seasonId) return;

    try {
      const seasons = (await requestJson(`${API_BASE}/olive-seasons/mine`)) || [];
      const item = seasons.find((row) => row.id === seasonId);
      if (!item) return;
      fillForm(item);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      if (messageEl) {
        messageEl.textContent = error.message || "Could not load season for edit";
        messageEl.className = "message error";
      }
    }
  });
}





const financeSeasonSelect = document.getElementById("finance-season-id");
const budgetOilTankPriceInput = document.getElementById("budget-oil-tank-price");
const saveOilTankPriceBtn = document.getElementById("save-oil-tank-price-btn");
const budgetOilTankPriceMessage = document.getElementById("budget-oil-tank-price-message");

function seasonPayloadFromRow(row, overrides = {}) {
  return {
    season_year: Number(row.season_year),
    land_pieces: Number(row.land_pieces ?? 1),
    land_piece_name: String(row.land_piece_name || "").trim(),
    estimated_chonbol: row.estimated_chonbol === null ? null : Number(row.estimated_chonbol),
    actual_chonbol: row.actual_chonbol === null ? null : Number(row.actual_chonbol),
    kg_per_land_piece: row.kg_per_land_piece === null ? null : Number(row.kg_per_land_piece),
    tanks_20l: row.tanks_20l === null ? null : Number(row.tanks_20l),
    tanks_taken_home_20l: row.tanks_taken_home_20l === null ? null : Number(row.tanks_taken_home_20l),
    pressing_cost_mode: String(row.pressing_cost_mode || "money"),
    pressing_cost: row.pressing_cost === null ? null : Number(row.pressing_cost),
    pressing_cost_oil_tanks_20l: row.pressing_cost_oil_tanks_20l === null ? null : Number(row.pressing_cost_oil_tanks_20l),
    pressing_cost_oil_tank_unit_price:
      row.pressing_cost_oil_tank_unit_price === null ? null : Number(row.pressing_cost_oil_tank_unit_price),
    notes: row.notes || null,
    ...overrides,
  };
}

async function syncBudgetTankPriceInput() {
  if (!financeSeasonSelect || !budgetOilTankPriceInput) return;
  const seasonId = String(financeSeasonSelect.value || "").trim();
  if (!seasonId) {
    budgetOilTankPriceInput.value = "";
    return;
  }

  try {
    const rows = (await requestJson(`${API_BASE}/olive-seasons/mine`)) || [];
    const row = rows.find((item) => item.id === seasonId);
    if (!row) {
      budgetOilTankPriceInput.value = "";
      return;
    }
    budgetOilTankPriceInput.value = row.pressing_cost_oil_tank_unit_price ?? "";
  } catch {
    // keep UI quiet on passive sync
  }
}

financeSeasonSelect?.addEventListener("change", syncBudgetTankPriceInput);

saveOilTankPriceBtn?.addEventListener("click", async () => {
  if (!financeSeasonSelect || !budgetOilTankPriceInput || !budgetOilTankPriceMessage) return;

  const seasonId = String(financeSeasonSelect.value || "").trim();
  if (!seasonId) {
    budgetOilTankPriceMessage.textContent = "Select a season first.";
    budgetOilTankPriceMessage.className = "message error";
    return;
  }

  const raw = String(budgetOilTankPriceInput.value || "").trim();
  const parsed = raw ? Number(raw) : null;
  if (raw && (!Number.isFinite(parsed) || parsed < 0)) {
    budgetOilTankPriceMessage.textContent = "Enter a valid non-negative tank price.";
    budgetOilTankPriceMessage.className = "message error";
    return;
  }

  budgetOilTankPriceMessage.textContent = "Saving tank price...";
  budgetOilTankPriceMessage.className = "message success";

  try {
    await requestJson(`${API_BASE}/olive-seasons/${seasonId}/oil-tank-price`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ unit_price: parsed }),
    });

    budgetOilTankPriceMessage.textContent = "Tank price saved.";
    budgetOilTankPriceMessage.className = "message success";

    document.getElementById("refresh-finance-btn")?.click();
    document.getElementById("refresh-seasons-btn")?.click();
  } catch (error) {
    budgetOilTankPriceMessage.textContent = error.message || "Could not save tank price";
    budgetOilTankPriceMessage.className = "message error";
  }
});

window.setTimeout(syncBudgetTankPriceInput, 300);


