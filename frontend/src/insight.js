import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireRole } from "./session.js";

const session = requireRole("farmer", "./workers.html");
const isEmbedded = new URLSearchParams(window.location.search).get("embedded") === "1";

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");
const refreshBtn = document.getElementById("refresh-insights-btn");

const insightKpis = document.getElementById("insight-kpis");
const seasonComparisonBody = document.getElementById("season-comparison-body");
const pieceComparisonBody = document.getElementById("piece-comparison-body");
const pieceDiagnosticsBody = document.getElementById("piece-diagnostics-body");
const insightNotes = document.getElementById("insight-notes");
const yearlyChart = document.getElementById("yearly-chart");
const pieceChart = document.getElementById("piece-chart");

const filtersForm = document.getElementById("insight-filters-form");
const filterYearFrom = document.getElementById("filter-year-from");
const filterYearTo = document.getElementById("filter-year-to");
const filterMetricType = document.getElementById("filter-metric-type");
const filterPieceSelect = document.getElementById("filter-piece-select");
const filterSummary = document.getElementById("filter-summary");
const filterApplyBtn = document.getElementById("filter-apply");
const filterResetBtn = document.getElementById("filter-reset");
const filterSelectAllBtn = document.getElementById("filter-select-all-pieces");
const filterClearPiecesBtn = document.getElementById("filter-clear-pieces");

const pieceForm = document.getElementById("piece-metric-form");
const pieceMessage = document.getElementById("piece-metric-message");
const resetPieceFormBtn = document.getElementById("reset-piece-form-btn");
const deletePieceBtn = document.getElementById("delete-piece-metric-btn");
const pieceMetricsList = document.getElementById("piece-metrics-list");

let seasons = [];
let pieceMetrics = [];
let filteredSeasons = [];
let filteredPieceMetrics = [];
let activeYearlySeries = [];
let pieceDiagnostics = [];

const filtersState = {
  yearFrom: null,
  yearTo: null,
  selectedPieces: [],
  metricType: "actual_chonbol",
};

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (farmer).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "insight.html");
}

if (isEmbedded) {
  document.querySelector(".hero")?.classList.add("is-hidden");
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function toNumber(value) {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function safeDecimal(value, digits = 2) {
  const num = toNumber(value);
  if (num === null) return "-";
  return num.toFixed(digits);
}

function currentYear() {
  return new Date().getFullYear();
}

function setPieceMessage(text, ok = true) {
  pieceMessage.textContent = text;
  pieceMessage.className = `message ${ok ? "success" : "error"}`;
}

function mean(values) {
  if (!values.length) return null;
  return values.reduce((acc, v) => acc + v, 0) / values.length;
}

function stdDev(values) {
  if (values.length < 2) return 0;
  const m = mean(values) ?? 0;
  const variance = values.reduce((acc, v) => acc + (v - m) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function linearSlope(points) {
  if (points.length < 2) return null;

  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumXX = 0;

  for (const point of points) {
    sumX += point.x;
    sumY += point.y;
    sumXY += point.x * point.y;
    sumXX += point.x * point.x;
  }

  const n = points.length;
  const denominator = n * sumXX - sumX * sumX;
  if (denominator === 0) return null;

  return (n * sumXY - sumX * sumY) / denominator;
}

function resetPieceForm() {
  pieceForm.reset();
  pieceForm.elements.metric_id.value = "";
  pieceForm.elements.season_year.value = String(currentYear());
  deletePieceBtn.hidden = true;
  pieceMessage.textContent = "";
  pieceMessage.className = "message";
}

function fillPieceForm(metric) {
  pieceForm.elements.metric_id.value = metric.id;
  pieceForm.elements.season_year.value = String(metric.season_year);
  pieceForm.elements.piece_label.value = metric.piece_label || "";
  pieceForm.elements.harvested_kg.value = metric.harvested_kg ?? "";
  pieceForm.elements.tanks_20l.value = metric.tanks_20l ?? "";
  pieceForm.elements.notes.value = metric.notes || "";
  deletePieceBtn.hidden = false;
}

function pieceMetricCard(metric) {
  return `
    <article class="worker-card" data-piece-metric-id="${metric.id}">
      <div class="list-head">
        <h3>${metric.piece_label} (${metric.season_year})</h3>
        <span class="badge day">${metric.kg_needed_per_tank ?? "-"} kg / tank</span>
      </div>
      <div class="worker-grid">
        <div><strong>Harvested KG:</strong> ${safeDecimal(metric.harvested_kg)}</div>
        <div><strong>Tanks:</strong> ${metric.tanks_20l ?? "-"}</div>
        <div><strong>KG / Tank:</strong> ${metric.kg_needed_per_tank ?? "-"}</div>
        <div class="full"><strong>Notes:</strong> ${metric.notes || "-"}</div>
      </div>
      <div class="actions-row">
        <button class="btn ghost" type="button" data-edit-piece-metric="${metric.id}">Modify</button>
      </div>
    </article>
  `;
}

function aggregatePieces(metrics) {
  const map = new Map();

  for (const item of metrics) {
    const key = String(item.piece_label || "").trim() || "Unnamed";
    const kg = toNumber(item.harvested_kg) ?? 0;
    const tanks = toNumber(item.tanks_20l) ?? 0;
    const year = Number(item.season_year);

    const entry =
      map.get(key) ||
      {
        piece: key,
        seasons: 0,
        totalKg: 0,
        totalTanks: 0,
        perYear: [],
      };

    entry.seasons += 1;
    entry.totalKg += kg;
    entry.totalTanks += tanks;
    entry.perYear.push({ year, kg, tanks });

    map.set(key, entry);
  }

  const rows = Array.from(map.values());
  rows.forEach((row) => {
    row.avgKgPerTank = row.totalTanks > 0 ? row.totalKg / row.totalTanks : null;
    row.avgKgPerSeason = row.seasons > 0 ? row.totalKg / row.seasons : null;
    row.perYear.sort((a, b) => a.year - b.year);
  });

  rows.sort((a, b) => b.totalKg - a.totalKg);
  return rows;
}

function buildDiagnostics(pieceRows) {
  return pieceRows
    .map((row) => {
      const kgValues = row.perYear.map((item) => item.kg);
      const avg = mean(kgValues);
      const stdev = stdDev(kgValues);
      const cv = avg && avg > 0 ? (stdev / avg) * 100 : null;
      const slope = linearSlope(row.perYear.map((item) => ({ x: item.year, y: item.kg })));
      const best = row.perYear.reduce((max, item) => (item.kg > max.kg ? item : max), row.perYear[0]);
      const worst = row.perYear.reduce((min, item) => (item.kg < min.kg ? item : min), row.perYear[0]);
      const filledTanks = row.perYear.filter((item) => item.tanks > 0).length;
      const quality = row.perYear.length > 0 ? (filledTanks / row.perYear.length) * 100 : 0;

      return {
        piece: row.piece,
        slope,
        cv,
        bestLabel: best ? `${best.year}: ${safeDecimal(best.kg, 0)}` : "-",
        worstLabel: worst ? `${worst.year}: ${safeDecimal(worst.kg, 0)}` : "-",
        quality,
      };
    })
    .sort((a, b) => (toNumber(b.slope) ?? -999999) - (toNumber(a.slope) ?? -999999));
}

function getMetricTypeLabel(metricType) {
  if (metricType === "tanks_20l") return "Tanks 20L";
  if (metricType === "kg_needed_per_tank") return "KG per Tank";
  if (metricType === "piece_harvested_kg") return "Piece Harvested KG";
  return "Actual Chonbol";
}

function getMetricFromSeason(row, metricType) {
  if (metricType === "tanks_20l") return toNumber(row.tanks_20l);
  if (metricType === "kg_needed_per_tank") return toNumber(row.kg_needed_per_tank);
  return toNumber(row.actual_chonbol);
}

function buildYearlySeries() {
  const metricType = filtersState.metricType;

  if (metricType === "piece_harvested_kg") {
    const byYear = new Map();
    for (const item of filteredPieceMetrics) {
      const year = Number(item.season_year);
      const kg = toNumber(item.harvested_kg) ?? 0;
      byYear.set(year, (byYear.get(year) || 0) + kg);
    }
    return Array.from(byYear.entries())
      .map(([year, value]) => ({ year, value }))
      .sort((a, b) => a.year - b.year);
  }

  return [...filteredSeasons]
    .map((row) => ({ year: Number(row.season_year), value: getMetricFromSeason(row, metricType) }))
    .filter((item) => item.value !== null)
    .sort((a, b) => a.year - b.year);
}

function updateFilterSummary() {
  const years = [filtersState.yearFrom, filtersState.yearTo].filter((y) => y !== null);
  const yearText = years.length === 2 ? `${filtersState.yearFrom} -> ${filtersState.yearTo}` : "All years";
  const piecesText = filtersState.selectedPieces.length ? `${filtersState.selectedPieces.length} selected` : "All pieces";
  const metricText = getMetricTypeLabel(filtersState.metricType);
  filterSummary.textContent = `Range: ${yearText} | Pieces: ${piecesText} | Metric: ${metricText}`;
  filterSummary.className = "message success";
}

function applyFilters() {
  const yearFrom = filtersState.yearFrom;
  const yearTo = filtersState.yearTo;

  filteredSeasons = seasons.filter((row) => {
    const year = Number(row.season_year);
    if (yearFrom !== null && year < yearFrom) return false;
    if (yearTo !== null && year > yearTo) return false;
    return true;
  });

  filteredPieceMetrics = pieceMetrics.filter((row) => {
    const year = Number(row.season_year);
    const piece = String(row.piece_label || "").trim() || "Unnamed";
    if (yearFrom !== null && year < yearFrom) return false;
    if (yearTo !== null && year > yearTo) return false;
    if (filtersState.selectedPieces.length && !filtersState.selectedPieces.includes(piece)) return false;
    return true;
  });

  activeYearlySeries = buildYearlySeries();
  renderInsights();
  updateFilterSummary();
}

function populateFilterOptions() {
  const allYears = Array.from(
    new Set([
      ...seasons.map((s) => Number(s.season_year)),
      ...pieceMetrics.map((p) => Number(p.season_year)),
    ]),
  )
    .filter((v) => Number.isFinite(v))
    .sort((a, b) => a - b);

  const allPieces = Array.from(
    new Set(pieceMetrics.map((item) => String(item.piece_label || "").trim() || "Unnamed")),
  ).sort((a, b) => a.localeCompare(b));

  if (!allYears.length) {
    filterYearFrom.innerHTML = '<option value="">No data</option>';
    filterYearTo.innerHTML = '<option value="">No data</option>';
  } else {
    const yearOptions = ['<option value="">All</option>', ...allYears.map((y) => `<option value="${y}">${y}</option>`)].join("");
    filterYearFrom.innerHTML = yearOptions;
    filterYearTo.innerHTML = yearOptions;

    if (filtersState.yearFrom === null) filtersState.yearFrom = allYears[0];
    if (filtersState.yearTo === null) filtersState.yearTo = allYears[allYears.length - 1];

    filterYearFrom.value = String(filtersState.yearFrom ?? "");
    filterYearTo.value = String(filtersState.yearTo ?? "");
  }

  if (!allPieces.length) {
    filterPieceSelect.innerHTML = '<option value="">No pieces</option>';
  } else {
    filterPieceSelect.innerHTML = allPieces.map((piece) => `<option value="${piece}">${piece}</option>`).join("");

    const selected = filtersState.selectedPieces.length ? filtersState.selectedPieces : allPieces;
    for (const option of filterPieceSelect.options) {
      option.selected = selected.includes(option.value);
    }
    filtersState.selectedPieces = selected;
  }

  filterMetricType.value = filtersState.metricType;
}

function chartPoints(values, width, height, pad) {
  if (!values.length) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const usableW = width - pad * 2;
  const usableH = height - pad * 2;

  return values
    .map((value, idx) => {
      const x = pad + (usableW * idx) / Math.max(values.length - 1, 1);
      const y = pad + usableH - ((value - min) / spread) * usableH;
      return `${x},${y}`;
    })
    .join(" ");
}

function renderKpis() {
  const seasonRows = [...filteredSeasons].sort((a, b) => a.season_year - b.season_year);
  const pieceRows = aggregatePieces(filteredPieceMetrics);

  const bestSeason =
    [...seasonRows].sort((a, b) => (toNumber(b.actual_chonbol) ?? -1) - (toNumber(a.actual_chonbol) ?? -1))[0] || null;

  const totalKg = seasonRows.reduce((acc, item) => acc + (toNumber(item.actual_chonbol) ?? 0), 0);
  const totalTanks = seasonRows.reduce((acc, item) => acc + (toNumber(item.tanks_20l) ?? 0), 0);
  const avgKgPerTankOverall = totalTanks > 0 ? totalKg / totalTanks : null;

  const latestPoint = activeYearlySeries[activeYearlySeries.length - 1] || null;
  const previousPoint = activeYearlySeries[activeYearlySeries.length - 2] || null;
  const yoy =
    latestPoint && previousPoint && previousPoint.value !== 0
      ? ((latestPoint.value - previousPoint.value) / previousPoint.value) * 100
      : null;

  const bestPiece = pieceRows[0] || null;

  insightKpis.innerHTML = [
    {
      title: "Best Season",
      value: bestSeason ? `${bestSeason.season_year}` : "-",
      caption: bestSeason ? `${safeDecimal(bestSeason.actual_chonbol)} actual chonbol` : "Add season records",
    },
    {
      title: "Overall KG / Tank",
      value: avgKgPerTankOverall === null ? "-" : safeDecimal(avgKgPerTankOverall),
      caption: totalTanks > 0 ? `${totalTanks} tanks in filtered range` : "No tanks recorded",
    },
    {
      title: `Latest YoY (${getMetricTypeLabel(filtersState.metricType)})`,
      value: yoy === null ? "-" : `${safeDecimal(yoy)}%`,
      caption: latestPoint ? `Latest year: ${latestPoint.year}` : "Need at least 2 years",
    },
    {
      title: "Top Piece",
      value: bestPiece ? bestPiece.piece : "-",
      caption: bestPiece ? `${safeDecimal(bestPiece.totalKg)} kg total` : "No filtered piece data",
    },
  ]
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

function renderSeasonTable() {
  const rows = [...filteredSeasons].sort((a, b) => a.season_year - b.season_year);
  if (!rows.length) {
    seasonComparisonBody.innerHTML = '<tr><td colspan="6">No season data for current filters.</td></tr>';
    return;
  }

  let prev = null;
  seasonComparisonBody.innerHTML = rows
    .map((row) => {
      const actual = toNumber(row.actual_chonbol);
      let yoy = "-";
      if (actual !== null && prev !== null && prev !== 0) {
        yoy = `${safeDecimal(((actual - prev) / prev) * 100)}%`;
      }
      if (actual !== null) prev = actual;

      return `
        <tr>
          <td>${row.season_year}</td>
          <td>${row.land_pieces}</td>
          <td>${safeDecimal(row.actual_chonbol)}</td>
          <td>${row.tanks_20l ?? "-"}</td>
          <td>${safeDecimal(row.kg_needed_per_tank)}</td>
          <td>${yoy}</td>
        </tr>
      `;
    })
    .join("");
}

function renderPieceTable() {
  const rows = aggregatePieces(filteredPieceMetrics);
  if (!rows.length) {
    pieceComparisonBody.innerHTML = '<tr><td colspan="6">No piece metrics for current filters.</td></tr>';
    return;
  }

  pieceComparisonBody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${row.piece}</td>
          <td>${row.seasons}</td>
          <td>${safeDecimal(row.totalKg)}</td>
          <td>${row.totalTanks || "-"}</td>
          <td>${safeDecimal(row.avgKgPerTank)}</td>
          <td>${safeDecimal(row.avgKgPerSeason)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderDiagnostics() {
  const pieceRows = aggregatePieces(filteredPieceMetrics);
  pieceDiagnostics = buildDiagnostics(pieceRows);

  if (!pieceDiagnostics.length) {
    pieceDiagnosticsBody.innerHTML = '<tr><td colspan="6">No diagnostics available for current filters.</td></tr>';
    insightNotes.innerHTML = '<p class="insight-note">Add more piece records to unlock diagnostics.</p>';
    return;
  }

  pieceDiagnosticsBody.innerHTML = pieceDiagnostics
    .map(
      (row) => `
        <tr>
          <td>${row.piece}</td>
          <td>${safeDecimal(row.slope)}</td>
          <td>${safeDecimal(row.cv)}</td>
          <td>${row.bestLabel}</td>
          <td>${row.worstLabel}</td>
          <td>${safeDecimal(row.quality)}%</td>
        </tr>
      `,
    )
    .join("");

  const strongestUp = pieceDiagnostics[0];
  const mostVolatile = [...pieceDiagnostics].sort((a, b) => (toNumber(b.cv) ?? 0) - (toNumber(a.cv) ?? 0))[0];
  const lowQuality = pieceDiagnostics.filter((item) => (toNumber(item.quality) ?? 0) < 60);

  const notes = [];
  if (strongestUp && toNumber(strongestUp.slope) !== null) {
    notes.push(`Strongest upward trend: ${strongestUp.piece} (${safeDecimal(strongestUp.slope)} kg/year).`);
  }
  if (mostVolatile && toNumber(mostVolatile.cv) !== null) {
    notes.push(`Highest volatility: ${mostVolatile.piece} (${safeDecimal(mostVolatile.cv)}% CV).`);
  }
  if (lowQuality.length) {
    notes.push(`Low tank-data quality pieces: ${lowQuality.map((item) => item.piece).join(", ")}.`);
  }

  insightNotes.innerHTML = notes.length
    ? notes.map((text) => `<p class="insight-note">${text}</p>`).join("")
    : '<p class="insight-note">No major anomalies detected in current filter scope.</p>';
}

function renderYearlyChart() {
  const rows = activeYearlySeries;
  if (!rows.length) {
    yearlyChart.innerHTML = "";
    return;
  }

  const values = rows.map((item) => item.value);
  const points = chartPoints(values, 800, 260, 24);

  const labels = rows
    .map((row, idx) => {
      const x = 24 + ((800 - 48) * idx) / Math.max(rows.length - 1, 1);
      return `<text x="${x}" y="252" text-anchor="middle" class="chart-label">${row.year}</text>`;
    })
    .join("");

  yearlyChart.innerHTML = `
    <rect x="0" y="0" width="800" height="260" class="chart-bg"></rect>
    <polyline points="${points}" class="chart-line"></polyline>
    ${labels}
  `;
}

function renderPieceChart() {
  const rows = aggregatePieces(filteredPieceMetrics).slice(0, 8);
  if (!rows.length) {
    pieceChart.innerHTML = "";
    return;
  }

  const maxValue = Math.max(...rows.map((item) => item.totalKg), 1);
  const barWidth = 68;
  const gap = 20;
  const baseY = 230;

  const bars = rows
    .map((row, index) => {
      const x = 42 + index * (barWidth + gap);
      const h = Math.max(8, (row.totalKg / maxValue) * 170);
      const y = baseY - h;
      return `
        <rect x="${x}" y="${y}" width="${barWidth}" height="${h}" class="chart-bar"></rect>
        <text x="${x + barWidth / 2}" y="246" text-anchor="middle" class="chart-label">${row.piece}</text>
        <text x="${x + barWidth / 2}" y="${y - 6}" text-anchor="middle" class="chart-value">${safeDecimal(row.totalKg, 0)}</text>
      `;
    })
    .join("");

  pieceChart.innerHTML = `<rect x="0" y="0" width="800" height="280" class="chart-bg"></rect>${bars}`;
}

function renderPieceMetricList() {
  const rows = [...filteredPieceMetrics].sort((a, b) => b.season_year - a.season_year || a.piece_label.localeCompare(b.piece_label));
  if (!rows.length) {
    pieceMetricsList.innerHTML = "No piece metrics for current filters.";
    return;
  }
  pieceMetricsList.innerHTML = rows.map(pieceMetricCard).join("");
}

function renderInsights() {
  renderKpis();
  renderSeasonTable();
  renderPieceTable();
  renderDiagnostics();
  renderYearlyChart();
  renderPieceChart();
  renderPieceMetricList();
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

async function fetchAll() {
  const [seasonData, pieceData] = await Promise.all([
    requestJson(`${API_BASE}/olive-seasons/mine`),
    requestJson(`${API_BASE}/olive-piece-metrics/mine`),
  ]);

  seasons = seasonData || [];
  pieceMetrics = pieceData || [];

  populateFilterOptions();
  applyFilters();
}

pieceForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const metricId = String(pieceForm.elements.metric_id.value || "").trim();
  const payload = {
    season_year: Number(pieceForm.elements.season_year.value),
    piece_label: String(pieceForm.elements.piece_label.value || "").trim(),
    harvested_kg: Number(pieceForm.elements.harvested_kg.value),
    tanks_20l: String(pieceForm.elements.tanks_20l.value || "").trim() ? Number(pieceForm.elements.tanks_20l.value) : null,
    notes: String(pieceForm.elements.notes.value || "").trim() || null,
  };

  setPieceMessage("Saving piece metric...", true);

  try {
    await requestJson(`${API_BASE}/olive-piece-metrics${metricId ? `/${metricId}` : ""}`, {
      method: metricId ? "PATCH" : "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    await fetchAll();
    resetPieceForm();
    setPieceMessage("Piece metric saved.", true);
  } catch (error) {
    setPieceMessage(error.message || "Could not save piece metric", false);
  }
});

deletePieceBtn.addEventListener("click", async () => {
  const metricId = String(pieceForm.elements.metric_id.value || "").trim();
  if (!metricId) return;
  if (!window.confirm("Delete this piece metric record?")) return;

  try {
    await requestJson(`${API_BASE}/olive-piece-metrics/${metricId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });

    await fetchAll();
    resetPieceForm();
    setPieceMessage("Piece metric deleted.", true);
  } catch (error) {
    setPieceMessage(error.message || "Could not delete piece metric", false);
  }
});

pieceMetricsList.addEventListener("click", (event) => {
  const editBtn = event.target.closest("button[data-edit-piece-metric]");
  if (!editBtn) return;

  const metricId = editBtn.dataset.editPieceMetric;
  const metric = pieceMetrics.find((item) => item.id === metricId);
  if (!metric) return;

  fillPieceForm(metric);
  window.scrollTo({ top: pieceForm.getBoundingClientRect().top + window.scrollY - 40, behavior: "smooth" });
});

filterApplyBtn.addEventListener("click", () => {
  const yearFrom = String(filterYearFrom.value || "").trim();
  const yearTo = String(filterYearTo.value || "").trim();

  filtersState.yearFrom = yearFrom ? Number(yearFrom) : null;
  filtersState.yearTo = yearTo ? Number(yearTo) : null;
  filtersState.metricType = filterMetricType.value;
  filtersState.selectedPieces = Array.from(filterPieceSelect.selectedOptions).map((item) => item.value);

  if (filtersState.yearFrom !== null && filtersState.yearTo !== null && filtersState.yearFrom > filtersState.yearTo) {
    const tmp = filtersState.yearFrom;
    filtersState.yearFrom = filtersState.yearTo;
    filtersState.yearTo = tmp;
    filterYearFrom.value = String(filtersState.yearFrom);
    filterYearTo.value = String(filtersState.yearTo);
  }

  applyFilters();
});

filterResetBtn.addEventListener("click", () => {
  filtersState.metricType = "actual_chonbol";
  filtersState.yearFrom = null;
  filtersState.yearTo = null;
  filtersState.selectedPieces = [];
  populateFilterOptions();
  applyFilters();
});

filterSelectAllBtn.addEventListener("click", () => {
  for (const option of filterPieceSelect.options) option.selected = true;
});

filterClearPiecesBtn.addEventListener("click", () => {
  for (const option of filterPieceSelect.options) option.selected = false;
});

filtersForm.addEventListener("submit", (event) => {
  event.preventDefault();
  filterApplyBtn.click();
});

refreshBtn.addEventListener("click", fetchAll);
resetPieceFormBtn.addEventListener("click", resetPieceForm);

resetPieceForm();
fetchAll().catch((error) => {
  insightKpis.innerHTML = `<p class="message error">${error.message || "Could not load insights"}</p>`;
});




