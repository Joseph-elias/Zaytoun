import "./ui-feedback.js";
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

function parseApiDetailMessage(payload) {
  if (!payload) return null;
  if (typeof payload === "string") return payload;

  if (Array.isArray(payload)) {
    for (const item of payload) {
      const message = parseApiDetailMessage(item);
      if (message) return message;
    }
    return null;
  }

  if (typeof payload === "object") {
    if (typeof payload.msg === "string" && payload.msg.trim()) return payload.msg;
    for (const key of ["detail", "error", "message"]) {
      const nested = parseApiDetailMessage(payload[key]);
      if (nested) return nested;
    }
    if (Array.isArray(payload.errors)) {
      for (const item of payload.errors) {
        const message = parseApiDetailMessage(item);
        if (message) return message;
      }
    }
  }

  return null;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, { headers: authHeaders(), ...options });
  if (response.status === 401 || response.status === 403) {
    clearSession();
    window.location.href = "./index.html";
    return null;
  }
  if (!response.ok) {
    let payload = null;
    let fallbackText = "";
    try {
      payload = await response.json();
    } catch {
      fallbackText = (await response.text().catch(() => "")).trim();
    }

    const detail =
      parseApiDetailMessage(payload) || fallbackText || `Request failed (${response.status})`;
    throw new Error(detail);
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
const deleteOilTankPriceBtn = document.getElementById("delete-oil-tank-price-btn");
const clearAllOilTankPricesBtn = document.getElementById("clear-all-oil-tank-prices-btn");
const budgetOilTankPriceMessage = document.getElementById("budget-oil-tank-price-message");
const ACTION_RESET_DELAY_MS = 2600;

[saveOilTankPriceBtn, deleteOilTankPriceBtn, clearAllOilTankPricesBtn].forEach((btn) => {
  if (btn) btn.dataset.uiFeedback = "off";
});

function setActionButtonBusy(button, label) {
  if (!button) return;
  if (!button.dataset.defaultLabel) {
    button.dataset.defaultLabel = button.textContent || "";
  }
  button.dataset.busyAt = String(Date.now());
  button.disabled = true;
  button.classList.remove("is-done", "is-error");
  button.classList.add("is-loading");
  button.textContent = label;
}

function setActionButtonDone(button, label = "Done ?") {
  if (!button) return;
  button.classList.remove("is-loading", "is-error");
  button.classList.add("is-done");
  button.textContent = label;
}

function setActionButtonError(button, label = "Failed") {
  if (!button) return;
  button.classList.remove("is-loading", "is-done");
  button.classList.add("is-error");
  button.textContent = label;
}

function resetActionButton(button) {
  if (!button) return;
  const defaultLabel = button.dataset.defaultLabel || "";
  button.disabled = false;
  button.classList.remove("is-loading", "is-done", "is-error");
  button.textContent = defaultLabel;
}

function finishActionButton(button, ok) {
  if (!button) return;
  const busyAt = Number(button.dataset.busyAt || 0);
  const elapsed = Date.now() - busyAt;
  const minLoadingMs = 260;
  const waitMs = Math.max(0, minLoadingMs - elapsed);

  window.setTimeout(() => {
    if (ok) {
      setActionButtonDone(button);
    } else {
      setActionButtonError(button);
    }
    window.setTimeout(() => resetActionButton(button), ACTION_RESET_DELAY_MS);
  }, waitMs);
}

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

  setActionButtonBusy(saveOilTankPriceBtn, "Saving...");
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
    finishActionButton(saveOilTankPriceBtn, true);
    document.getElementById("refresh-finance-btn")?.click();
    document.getElementById("refresh-seasons-btn")?.click();
  } catch (error) {
    budgetOilTankPriceMessage.textContent = error.message || "Could not save tank price";
    budgetOilTankPriceMessage.className = "message error";
    finishActionButton(saveOilTankPriceBtn, false);
  }
});


deleteOilTankPriceBtn?.addEventListener("click", async () => {
  if (!financeSeasonSelect || !budgetOilTankPriceInput || !budgetOilTankPriceMessage) return;

  const seasonId = String(financeSeasonSelect.value || "").trim();
  if (!seasonId) {
    budgetOilTankPriceMessage.textContent = "Select a season first.";
    budgetOilTankPriceMessage.className = "message error";
    return;
  }

  if (!window.confirm("Delete tank price for this piece/season?")) return;

  setActionButtonBusy(deleteOilTankPriceBtn, "Deleting...");
  budgetOilTankPriceMessage.textContent = "Deleting tank price...";
  budgetOilTankPriceMessage.className = "message success";

  try {
    await requestJson(`${API_BASE}/olive-seasons/${seasonId}/oil-tank-price`, {
      method: "DELETE",
      headers: authHeaders(),
    });

    budgetOilTankPriceInput.value = "";
    budgetOilTankPriceMessage.textContent = "Tank price deleted.";
    budgetOilTankPriceMessage.className = "message success";
    finishActionButton(deleteOilTankPriceBtn, true);
    document.getElementById("refresh-finance-btn")?.click();
    document.getElementById("refresh-seasons-btn")?.click();
  } catch (error) {
    budgetOilTankPriceMessage.textContent = error.message || "Could not delete tank price";
    budgetOilTankPriceMessage.className = "message error";
    finishActionButton(deleteOilTankPriceBtn, false);
  }
});

clearAllOilTankPricesBtn?.addEventListener("click", async () => {
  if (!budgetOilTankPriceMessage) return;

  if (!window.confirm("Clear oil tank prices for all seasons?")) return;

  setActionButtonBusy(clearAllOilTankPricesBtn, "Clearing...");
  budgetOilTankPriceMessage.textContent = "Clearing all tank prices...";
  budgetOilTankPriceMessage.className = "message success";

  try {
    const result = await requestJson(`${API_BASE}/olive-seasons/oil-tank-prices`, {
      method: "DELETE",
      headers: authHeaders(),
    });

    if (budgetOilTankPriceInput) budgetOilTankPriceInput.value = "";
    const count = Number(result?.cleared_count || 0);
    budgetOilTankPriceMessage.textContent = `Cleared ${count} tank price value(s).`;
    budgetOilTankPriceMessage.className = "message success";
    finishActionButton(clearAllOilTankPricesBtn, true);
    document.getElementById("refresh-finance-btn")?.click();
    document.getElementById("refresh-seasons-btn")?.click();
    await syncBudgetTankPriceInput();
  } catch (error) {
    budgetOilTankPriceMessage.textContent = error.message || "Could not clear tank prices";
    budgetOilTankPriceMessage.className = "message error";
    finishActionButton(clearAllOilTankPricesBtn, false);
  }
});
window.setTimeout(syncBudgetTankPriceInput, 300);
const usageSeasonSelect = document.getElementById("usage-season-id");
const usageHistoryList = document.getElementById("usage-history-list");
const usageForm = document.getElementById("usage-form");
const refreshUsageBtn = document.getElementById("refresh-usage-btn");
let usageHistoryRows = [];
let usageHistoryEditId = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function usageSeasonId() {
  return String(usageSeasonSelect?.value || "").trim();
}

function renderUsageHistory() {
  if (!usageHistoryList) return;

  if (!usageSeasonId()) {
    usageHistoryList.innerHTML = "Select a target piece/season to see usage history.";
    return;
  }

  if (!usageHistoryRows.length) {
    usageHistoryList.innerHTML = "No usage history yet for selected season.";
    return;
  }

  usageHistoryList.innerHTML = usageHistoryRows
    .map((row) => {
      const isEditing = usageHistoryEditId === row.id;
      const usedOn = row.used_on ? escapeHtml(row.used_on) : "-";
      const usageType = row.usage_type ? escapeHtml(row.usage_type) : "-";
      const notes = row.notes ? escapeHtml(row.notes) : "-";
      const tanksUsed = Number(row.tanks_used || 0).toFixed(2);

      if (isEditing) {
        return `
          <article class="worker-card">
            <h4>Edit Usage</h4>
            <form data-usage-edit-form="${row.id}" class="form-grid compact">
              <label>Used On
                <input name="edit_used_on" type="date" value="${row.used_on || ""}" />
              </label>
              <label>Quantity Used
                <input name="edit_tanks_used" type="number" min="0" step="0.01" value="${tanksUsed}" required />
              </label>
              <label>Usage Type
                <input name="edit_usage_type" maxlength="120" value="${usageType === "-" ? "" : usageType}" />
              </label>
              <label class="full">Notes
                <textarea name="edit_notes" rows="2" maxlength="400">${notes === "-" ? "" : notes}</textarea>
              </label>
              <div class="actions-row full">
                <button class="btn" type="submit">Save Changes</button>
                <button class="btn ghost" type="button" data-cancel-usage-edit="${row.id}">Cancel</button>
              </div>
            </form>
          </article>
        `;
      }

      return `
        <article class="worker-card">
          <h4>${usedOn}</h4>
          <p><strong>Quantity:</strong> ${tanksUsed} tanks</p>
          <p><strong>Type:</strong> ${usageType}</p>
          <p><strong>Notes:</strong> ${notes}</p>
          <div class="actions-row">
            <button class="btn ghost" type="button" data-edit-usage="${row.id}">Modify</button>
            <button class="btn danger" type="button" data-delete-usage="${row.id}">Delete</button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadUsageHistory() {
  if (!usageHistoryList) return;

  const seasonId = usageSeasonId();
  if (!seasonId) {
    usageHistoryRows = [];
    usageHistoryEditId = null;
    renderUsageHistory();
    return;
  }

  try {
    usageHistoryRows = (await requestJson(`${API_BASE}/olive-usages/mine?season_id=${seasonId}`)) || [];
    if (!usageHistoryRows.some((row) => row.id === usageHistoryEditId)) {
      usageHistoryEditId = null;
    }
    renderUsageHistory();
  } catch (error) {
    usageHistoryList.innerHTML = `<p class="message error">${escapeHtml(error.message || "Could not load usage history")}</p>`;
  }
}

usageSeasonSelect?.addEventListener("change", loadUsageHistory);
refreshUsageBtn?.addEventListener("click", () => {
  window.setTimeout(loadUsageHistory, 250);
});
usageForm?.addEventListener("submit", () => {
  window.setTimeout(loadUsageHistory, 500);
});

usageHistoryList?.addEventListener("click", async (event) => {
  const target = event.target instanceof Element ? event.target : null;
  if (!target) return;

  const editBtn = target.closest("button[data-edit-usage]");
  if (editBtn) {
    usageHistoryEditId = String(editBtn.getAttribute("data-edit-usage") || "").trim() || null;
    renderUsageHistory();
    return;
  }

  const cancelBtn = target.closest("button[data-cancel-usage-edit]");
  if (cancelBtn) {
    usageHistoryEditId = null;
    renderUsageHistory();
    return;
  }

  const deleteBtn = target.closest("button[data-delete-usage]");
  if (!deleteBtn) return;

  const usageId = String(deleteBtn.getAttribute("data-delete-usage") || "").trim();
  if (!usageId) return;
  if (!window.confirm("Delete this usage entry?")) return;

  try {
    await requestJson(`${API_BASE}/olive-usages/${usageId}`, { method: "DELETE", headers: authHeaders() });
    usageHistoryRows = usageHistoryRows.filter((row) => row.id !== usageId);
    if (usageHistoryEditId === usageId) usageHistoryEditId = null;
    renderUsageHistory();
  } catch (error) {
    if (budgetOilTankPriceMessage) {
      budgetOilTankPriceMessage.textContent = error.message || "Could not delete usage entry";
      budgetOilTankPriceMessage.className = "message error";
    }
  }
});

usageHistoryList?.addEventListener("submit", async (event) => {
  const formEl = event.target instanceof HTMLFormElement ? event.target : null;
  if (!formEl) return;
  const usageId = String(formEl.getAttribute("data-usage-edit-form") || "").trim();
  if (!usageId) return;

  event.preventDefault();

  const tanksRaw = String(formEl.elements.edit_tanks_used?.value || "").trim();
  const tanksVal = Number(tanksRaw);
  if (!Number.isFinite(tanksVal) || tanksVal < 0) {
    alert("Enter a valid usage quantity.");
    return;
  }

  const payload = {
    used_on: String(formEl.elements.edit_used_on?.value || "").trim() || null,
    tanks_used: Number(tanksVal.toFixed(2)),
    usage_type: String(formEl.elements.edit_usage_type?.value || "").trim() || null,
    notes: String(formEl.elements.edit_notes?.value || "").trim() || null,
  };

  try {
    await requestJson(`${API_BASE}/olive-usages/${usageId}`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    usageHistoryEditId = null;
    await loadUsageHistory();
  } catch (error) {
    alert(error.message || "Could not update usage entry");
  }
});

window.setTimeout(loadUsageHistory, 700);





