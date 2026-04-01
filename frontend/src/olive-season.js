import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireRole } from "./session.js";

const session = requireRole("farmer", "./workers.html");

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");
const form = document.getElementById("olive-season-form");
const messageEl = document.getElementById("olive-season-message");
const seasonsList = document.getElementById("olive-seasons-list");
const seasonProgress = document.getElementById("season-progress");
const refreshBtn = document.getElementById("refresh-seasons-btn");
const resetBtn = document.getElementById("reset-form-btn");
const deleteBtn = document.getElementById("delete-season-btn");
const kgNeededInput = document.getElementById("kg-needed-per-tank");
const toggleInsightsBtn = document.getElementById("toggle-insights-btn");
const insightsEmbed = document.getElementById("olive-insights-embed");

let cachedSeasons = [];
let insightsVisible = false;

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (farmer).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "olive-season.html");
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setMessage(text, ok = true) {
  messageEl.textContent = text;
  messageEl.className = `message ${ok ? "success" : "error"}`;
}

function currentYear() {
  return new Date().getFullYear();
}

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

function readFormPayload() {
  return {
    season_year: Number(form.elements.season_year.value),
    land_pieces: Number(form.elements.land_pieces.value || 1),
    land_piece_name: String(form.elements.land_piece_name.value || "").trim() || null,
    estimated_chonbol: toNum(form.elements.estimated_chonbol.value),
    actual_chonbol: toNum(form.elements.actual_chonbol.value),
    kg_per_land_piece: toNum(form.elements.kg_per_land_piece.value),
    tanks_20l: toNum(form.elements.tanks_20l.value),
    notes: String(form.elements.notes.value || "").trim() || null,
  };
}

function refreshCalculated() {
  const kgPerLandPiece = toNum(form.elements.kg_per_land_piece.value);
  const actual = toNum(form.elements.actual_chonbol.value);
  const tanks = toNum(form.elements.tanks_20l.value);
  kgNeededInput.value = calculateKgPerTank(kgPerLandPiece, actual, tanks);
}

function resetForm() {
  form.reset();
  form.elements.season_id.value = "";
  form.elements.land_pieces.value = "1";
  form.elements.season_year.value = String(currentYear());
  deleteBtn.hidden = true;
  kgNeededInput.value = "-";
  setMessage("", true);
  messageEl.className = "message";
}

function fillForm(item) {
  form.elements.season_id.value = item.id;
  form.elements.season_year.value = String(item.season_year);
  form.elements.land_pieces.value = String(item.land_pieces ?? 1);
  form.elements.land_piece_name.value = item.land_piece_name || "";
  form.elements.estimated_chonbol.value = item.estimated_chonbol ?? "";
  form.elements.actual_chonbol.value = item.actual_chonbol ?? "";
  form.elements.kg_per_land_piece.value = item.kg_per_land_piece ?? "";
  form.elements.tanks_20l.value = item.tanks_20l ?? "";
  form.elements.notes.value = item.notes || "";
  deleteBtn.hidden = false;
  refreshCalculated();
}

function missingSeasonFields(item) {
  const missing = [];
  if (!String(item.land_piece_name || "").trim()) missing.push("piece name");
  if (toNum(item.kg_per_land_piece) === null) missing.push("kg per land piece");
  if (toNum(item.tanks_20l) === null || Number(item.tanks_20l) <= 0) missing.push("tanks produced");
  return missing;
}

function seasonStatusBadge(item) {
  const missing = missingSeasonFields(item);
  if (!missing.length) {
    return '<span class="badge available">Complete</span>';
  }
  return `<span class="badge draft" title="Missing: ${missing.join(", ")}">Draft (${missing.length} missing)</span>`;
}

function updateSeasonProgress(items) {
  if (!seasonProgress) return;
  const total = items.length;
  const drafts = items.filter((item) => missingSeasonFields(item).length > 0).length;
  seasonProgress.textContent = `Drafts: ${drafts} / ${total}`;
}

function seasonCard(item) {
  const missing = missingSeasonFields(item);
  const missingDetails = missing.length
    ? `<div class="full season-missing"><strong>Missing:</strong> ${missing.join(", ")}</div>`
    : '<div class="full season-missing complete">All key info completed.</div>';

  return `
    <article class="worker-card" data-season-id="${item.id}">
      <div class="list-head">
        <h3>Season ${item.season_year}</h3>
        <div class="actions-row season-badges">
          ${seasonStatusBadge(item)}
          <span class="badge day">${item.kg_needed_per_tank ?? "-"} kg / tank</span>
        </div>
      </div>
      <div class="worker-grid">
        <div><strong>Land Piece Name:</strong> ${item.land_piece_name || "-"}</div>
        <div><strong>Estimated Chonbol:</strong> ${item.estimated_chonbol ?? "-"}</div>
        <div><strong>Actual Chonbol:</strong> ${item.actual_chonbol ?? "-"}</div>
        <div><strong>KG per Piece:</strong> ${item.kg_per_land_piece ?? "-"}</div>
        <div><strong>Tanks (20L):</strong> ${item.tanks_20l ?? "-"}</div>
        <div><strong>KG needed / Tank:</strong> ${item.kg_needed_per_tank ?? "-"}</div>
        ${missingDetails}
        <div class="full"><strong>Notes:</strong> ${item.notes || "-"}</div>
      </div>
      <div class="actions-row">
        <button class="btn ghost" type="button" data-edit-season="${item.id}">Modify</button>
      </div>
    </article>
  `;
}

function setInsightsVisible(nextVisible) {
  insightsVisible = nextVisible;
  insightsEmbed.classList.toggle("is-hidden", !insightsVisible);
  toggleInsightsBtn.textContent = insightsVisible ? "Hide Insights" : "Show Insights";
}

async function fetchSeasons() {
  seasonsList.innerHTML = "Loading seasons...";
  try {
    const response = await fetch(`${API_BASE}/olive-seasons/mine`, { headers: authHeaders() });
    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    if (!response.ok) throw new Error("Could not load olive seasons");

    const items = await response.json();
    cachedSeasons = items;
    updateSeasonProgress(items);
    seasonsList.innerHTML = items.length ? items.map(seasonCard).join("") : "No season records yet.";
  } catch (error) {
    updateSeasonProgress([]);
    seasonsList.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

form.addEventListener("input", (event) => {
  if (event.target.name === "kg_per_land_piece" || event.target.name === "actual_chonbol" || event.target.name === "tanks_20l") {
    refreshCalculated();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const seasonId = String(form.elements.season_id.value || "").trim();
  const payload = readFormPayload();

  setMessage("Saving season...", true);
  try {
    const response = await fetch(`${API_BASE}/olive-seasons${seasonId ? `/${seasonId}` : ""}`, {
      method: seasonId ? "PATCH" : "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const detail = err?.detail?.[0]?.msg || err?.detail || "Could not save season";
      throw new Error(typeof detail === "string" ? detail : "Could not save season");
    }

    await fetchSeasons();
    resetForm();
    setMessage("Season saved successfully.", true);
  } catch (error) {
    setMessage(error.message || "Could not save season", false);
  }
});

deleteBtn.addEventListener("click", async () => {
  const seasonId = String(form.elements.season_id.value || "").trim();
  if (!seasonId) return;
  if (!window.confirm("Delete this season record?")) return;

  try {
    const response = await fetch(`${API_BASE}/olive-seasons/${seasonId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err?.detail || "Could not delete season");
    }

    await fetchSeasons();
    resetForm();
    setMessage("Season deleted.", true);
  } catch (error) {
    setMessage(error.message || "Could not delete season", false);
  }
});

seasonsList.addEventListener("click", (event) => {
  const editBtn = event.target.closest("button[data-edit-season]");
  if (!editBtn) return;

  const id = editBtn.dataset.editSeason;
  const item = cachedSeasons.find((row) => row.id === id);
  if (!item) return;

  fillForm(item);
  window.scrollTo({ top: 0, behavior: "smooth" });
});

toggleInsightsBtn.addEventListener("click", () => {
  setInsightsVisible(!insightsVisible);
});

resetBtn.addEventListener("click", resetForm);
refreshBtn.addEventListener("click", fetchSeasons);

resetForm();
setInsightsVisible(false);
fetchSeasons();
