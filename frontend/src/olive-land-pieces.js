import { API_BASE } from "./config.js";
import { authHeaders, clearSession } from "./session.js";

const landPieceForm = document.getElementById("land-piece-form");
const landPieceMessage = document.getElementById("land-piece-message");
const landPiecesList = document.getElementById("land-pieces-list");
const refreshLandPiecesBtn = document.getElementById("refresh-land-pieces-btn");
const seasonForm = document.getElementById("olive-season-form");
const seasonLandPieceSelect = document.getElementById("season-land-piece-select");
const landPieceSeasonYearToggle = document.getElementById("land-piece-season-year-toggle");
const landPieceSeasonYearField = document.getElementById("land-piece-season-year-field");

let landPieces = [];

function setLandPieceMessage(text, ok = true) {
  if (!landPieceMessage) return;
  landPieceMessage.textContent = text;
  landPieceMessage.className = `message ${ok ? "success" : "error"}`;
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

function selectedSeasonYear() {
  const raw = String(seasonForm?.elements?.season_year?.value || "").trim();
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function renderLandPieceOptions() {
  if (!seasonLandPieceSelect) return;
  const current = String(seasonLandPieceSelect.value || "").trim();
  const selectedYear = selectedSeasonYear();

  const eligiblePieces = landPieces.filter((piece) => {
    if (piece.season_year === null || piece.season_year === undefined) return true;
    if (selectedYear === null) return false;
    return Number(piece.season_year) === selectedYear;
  });

  if (!landPieces.length) {
    seasonLandPieceSelect.innerHTML = '<option value="">No land pieces yet (add one in Season Start)</option>';
    return;
  }

  if (!eligiblePieces.length) {
    seasonLandPieceSelect.innerHTML = '<option value="">No land pieces for this season year</option>';
    return;
  }

  seasonLandPieceSelect.innerHTML = [
    '<option value="">Select land piece</option>',
    ...eligiblePieces.map((piece) => `<option value="${piece.piece_name}">${piece.piece_name}</option>`),
  ].join("");

  const stillExists = eligiblePieces.some((piece) => piece.piece_name === current);
  seasonLandPieceSelect.value = stillExists ? current : "";
}

function landPieceCard(piece) {
  return `
    <article class="worker-card" data-land-piece-id="${piece.id}">
      <div class="list-head">
        <h3>${piece.piece_name}</h3>
        <button class="btn danger" type="button" data-delete-land-piece="${piece.id}">Delete</button>
      </div>
      <div class="worker-grid">
        <div><strong>Season Year:</strong> ${piece.season_year ?? "-"}</div>
        <div><strong>Created:</strong> ${String(piece.created_at || "").slice(0, 10) || "-"}</div>
      </div>
    </article>
  `;
}

function renderLandPiecesList() {
  if (!landPiecesList) return;
  landPiecesList.innerHTML = landPieces.length ? landPieces.map(landPieceCard).join("") : "No land pieces yet.";
}

async function fetchLandPieces() {
  landPieces = (await requestJson(`${API_BASE}/olive-land-pieces/mine`)) || [];
  renderLandPieceOptions();
  renderLandPiecesList();
}

if (seasonForm) {
  seasonForm.addEventListener(
    "submit",
    (event) => {
      const selected = String(seasonLandPieceSelect?.value || "").trim();
      if (!selected) {
        event.preventDefault();
        setLandPieceMessage("Add a land piece in Season Start, then select it.", false);
        return;
      }

      const selectedYear = selectedSeasonYear();
      const selectedPiece = landPieces.find((piece) => piece.piece_name === selected);
      if (selectedPiece?.season_year !== null && selectedPiece?.season_year !== undefined) {
        if (selectedYear === null || Number(selectedPiece.season_year) !== selectedYear) {
          event.preventDefault();
          setLandPieceMessage(`This land piece is linked to season year ${selectedPiece.season_year}.`, false);
        }
      }
    },
    true,
  );
}

if (landPieceForm) {
  landPieceForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const pieceName = String(landPieceForm.elements.piece_name.value || "").trim();
    const useYear = Boolean(landPieceSeasonYearToggle?.checked);
    const seasonYear = useYear ? Number(landPieceForm.elements.season_year.value) : null;
    if (!pieceName) {
      setLandPieceMessage("Enter a piece name.", false);
      return;
    }
    if (useYear && (!Number.isFinite(seasonYear) || seasonYear < 2000 || seasonYear > 2100)) {
      setLandPieceMessage("Enter a valid season year (2000-2100).", false);
      return;
    }

    setLandPieceMessage("Saving piece...", true);
    try {
      await requestJson(`${API_BASE}/olive-land-pieces`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ piece_name: pieceName, season_year: seasonYear }),
      });
      landPieceForm.reset();
      if (landPieceSeasonYearField) landPieceSeasonYearField.classList.add("is-hidden");
      await fetchLandPieces();
      setLandPieceMessage("Land piece added.", true);
    } catch (error) {
      setLandPieceMessage(error.message || "Could not add land piece", false);
    }
  });
}

if (landPiecesList) {
  landPiecesList.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-delete-land-piece]");
    if (!btn) return;

    const pieceId = btn.dataset.deleteLandPiece;
    if (!window.confirm("Delete this land piece?")) return;

    try {
      await requestJson(`${API_BASE}/olive-land-pieces/${pieceId}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      await fetchLandPieces();
      setLandPieceMessage("Land piece deleted.", true);
    } catch (error) {
      setLandPieceMessage(error.message || "Could not delete land piece", false);
    }
  });
}

if (refreshLandPiecesBtn) {
  refreshLandPiecesBtn.addEventListener("click", fetchLandPieces);
}

if (landPieceSeasonYearToggle && landPieceSeasonYearField) {
  landPieceSeasonYearToggle.addEventListener("change", () => {
    const show = Boolean(landPieceSeasonYearToggle.checked);
    landPieceSeasonYearField.classList.toggle("is-hidden", !show);
    if (!show && landPieceForm?.elements?.season_year) {
      landPieceForm.elements.season_year.value = "";
    }
  });
}

if (seasonForm?.elements?.season_year) {
  seasonForm.elements.season_year.addEventListener("input", renderLandPieceOptions);
}

fetchLandPieces();
