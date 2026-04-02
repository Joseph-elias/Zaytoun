import { API_BASE } from "./config.js";
import { authHeaders, clearSession } from "./session.js";

const seasonsList = document.getElementById("olive-seasons-list");
const form = document.getElementById("olive-season-form");
const deleteBtn = document.getElementById("delete-season-btn");
const kgNeededInput = document.getElementById("kg-needed-per-tank");
const messageEl = document.getElementById("olive-season-message");

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
  if (form.elements.pressing_cost) {
    form.elements.pressing_cost.value = item.pressing_cost ?? "";
  }
  form.elements.notes.value = item.notes || "";
  if (deleteBtn) deleteBtn.hidden = false;

  const kgPerLandPiece = toNum(form.elements.kg_per_land_piece.value);
  const actual = toNum(form.elements.actual_chonbol.value);
  const tanks = toNum(form.elements.tanks_20l.value);
  if (kgNeededInput) {
    kgNeededInput.value = calculateKgPerTank(kgPerLandPiece, actual, tanks);
  }
  if (messageEl) {
    messageEl.textContent = "Edit mode: update fields, then click Save Season.";
    messageEl.className = "message success";
  }
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
