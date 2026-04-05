import "./ui-feedback.js";
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
const trendStory = document.getElementById("trend-story");
const insightRisks = document.getElementById("insight-risks");
const dataQualityBody = document.getElementById("data-quality-body");
const salesInventoryKpis = document.getElementById("sales-inventory-kpis");
const salesInventoryNotes = document.getElementById("sales-inventory-notes");
const salesInventoryBody = document.getElementById("sales-inventory-body");
const inventoryChart = document.getElementById("inventory-chart");

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
const rangeLast3Btn = document.getElementById("range-last-3");
const rangeLast5Btn = document.getElementById("range-last-5");

let seasons = [];
let pieceMetrics = [];
let sales = [];
let usages = [];
let analyticsPieceMetrics = [];
let filteredSeasons = [];
let filteredPieceMetrics = [];
let activeYearlySeries = [];
let pieceDiagnostics = [];
let activeInventoryRows = [];

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
  document.querySelector(".page")?.classList.add("embedded-view");
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

function normalizePieceLabel(value) {
  return String(value || "").trim() || "Unnamed";
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

function linearProjection(points, targetX) {
  if (points.length < 2) return null;
  const slope = linearSlope(points);
  if (slope === null) return null;

  const xAvg = mean(points.map((p) => p.x));
  const yAvg = mean(points.map((p) => p.y));
  if (xAvg === null || yAvg === null) return null;

  const intercept = yAvg - slope * xAvg;
  return slope * targetX + intercept;
}

function aggregateSeasonYears(rows) {
  const yearMap = new Map();

  for (const row of rows) {
    const year = Number(row.season_year);
    const actual = toNumber(row.actual_chonbol) ?? 0;
    const estimated = toNumber(row.estimated_chonbol) ?? 0;
    const tanks = toNumber(row.tanks_20l) ?? 0;
    const kgBase = toNumber(row.kg_per_land_piece) ?? toNumber(row.actual_chonbol) ?? 0;
    const sold = toNumber(row.sold_tanks) ?? 0;
    const used = toNumber(row.used_tanks) ?? 0;
    const revenue = toNumber(row.sales_revenue_total) ?? 0;
    const cost = toNumber(row.total_cost) ?? 0;
    const profit = toNumber(row.profit) ?? 0;
    const remaining = toNumber(row.remaining_tanks) ?? 0;

    const entry =
      yearMap.get(year) ||
      {
        year,
        pieces: 0,
        actualTotal: 0,
        estimatedTotal: 0,
        tanksTotal: 0,
        kgBaseTotal: 0,
        soldTotal: 0,
        usedTotal: 0,
        revenueTotal: 0,
        costTotal: 0,
        profitTotal: 0,
        remainingTotal: 0,
        rows: [],
      };

    entry.pieces += 1;
    entry.actualTotal += actual;
    entry.estimatedTotal += estimated;
    entry.tanksTotal += tanks;
    entry.kgBaseTotal += kgBase;
    entry.soldTotal += sold;
    entry.usedTotal += used;
    entry.revenueTotal += revenue;
    entry.costTotal += cost;
    entry.profitTotal += profit;
    entry.remainingTotal += remaining;
    entry.rows.push(row);

    yearMap.set(year, entry);
  }

  const years = Array.from(yearMap.values()).sort((a, b) => a.year - b.year);
  for (const row of years) {
    row.kgPerTank = row.tanksTotal > 0 ? row.kgBaseTotal / row.tanksTotal : null;
  }
  return years;
}

function aggregatePieces(metrics) {
  const map = new Map();

  for (const item of metrics) {
    const key = normalizePieceLabel(item.piece_label);
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
  if (metricType === "sales_revenue_total") return "Sales Revenue";
  if (metricType === "profit") return "Profit";
  if (metricType === "remaining_tanks") return "Remaining Tanks";
  return "Actual Chonbol";
}

function getMetricFromYearRow(row, metricType) {
  if (metricType === "tanks_20l") return row.tanksTotal;
  if (metricType === "kg_needed_per_tank") return row.kgPerTank;
  if (metricType === "sales_revenue_total") return row.revenueTotal;
  if (metricType === "profit") return row.profitTotal;
  if (metricType === "remaining_tanks") return row.remainingTotal;
  return row.actualTotal;
}

function buildAutoPieceMetricFromSeason(season) {
  const harvestedKg = toNumber(season.kg_per_land_piece) ?? toNumber(season.actual_chonbol) ?? 0;
  const tanks = toNumber(season.tanks_20l);
  const computedKgNeededPerTank = tanks && tanks > 0 ? harvestedKg / tanks : null;
  const existingKgNeededPerTank = toNumber(season.kg_needed_per_tank);

  return {
    id: `season:${season.id}`,
    season_year: Number(season.season_year),
    piece_label: normalizePieceLabel(season.land_piece_name),
    harvested_kg: harvestedKg,
    tanks_20l: tanks,
    kg_needed_per_tank: existingKgNeededPerTank ?? computedKgNeededPerTank,
    notes: season.notes || null,
    is_auto_generated: true,
  };
}

function buildAnalyticsPieceMetrics() {
  const manualMetrics = (pieceMetrics || []).map((metric) => ({
    ...metric,
    piece_label: normalizePieceLabel(metric.piece_label),
    season_year: Number(metric.season_year),
    is_auto_generated: false,
  }));

  const existingKeys = new Set(manualMetrics.map((metric) => `${metric.season_year}::${normalizePieceLabel(metric.piece_label).toLowerCase()}`));

  const inferredMetrics = [];
  for (const season of seasons) {
    const pieceLabel = normalizePieceLabel(season.land_piece_name);
    const seasonYear = Number(season.season_year);
    if (!Number.isFinite(seasonYear)) continue;

    const key = `${seasonYear}::${pieceLabel.toLowerCase()}`;
    if (existingKeys.has(key)) continue;

    inferredMetrics.push(buildAutoPieceMetricFromSeason(season));
  }

  return [...manualMetrics, ...inferredMetrics];
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

  const seasonYears = aggregateSeasonYears(filteredSeasons);
  return seasonYears
    .map((row) => ({ year: row.year, value: getMetricFromYearRow(row, metricType) }))
    .filter((item) => item.value !== null)
    .sort((a, b) => a.year - b.year);
}

function updateFilterSummary() {
  const years = [filtersState.yearFrom, filtersState.yearTo].filter((y) => y !== null);
  const yearText = years.length === 2 ? `${filtersState.yearFrom} -> ${filtersState.yearTo}` : "All years";
  const piecesText = filtersState.selectedPieces.length ? `${filtersState.selectedPieces.length} selected` : "All pieces";
  const metricText = getMetricTypeLabel(filtersState.metricType);
  filterSummary.textContent = `Scope: ${yearText} | Pieces: ${piecesText} | Lens: ${metricText}`;
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

  filteredPieceMetrics = analyticsPieceMetrics.filter((row) => {
    const year = Number(row.season_year);
    const piece = normalizePieceLabel(row.piece_label);
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
  const allYears = Array.from(new Set([...seasons.map((s) => Number(s.season_year)), ...analyticsPieceMetrics.map((p) => Number(p.season_year))]))
    .filter((v) => Number.isFinite(v))
    .sort((a, b) => a - b);

  const allPieces = Array.from(new Set(analyticsPieceMetrics.map((item) => normalizePieceLabel(item.piece_label)))).sort((a, b) => a.localeCompare(b));

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

function calcYoYSeries(series) {
  return series.map((item, idx) => {
    if (idx === 0 || !series[idx - 1] || series[idx - 1].value === 0) {
      return { ...item, yoy: null };
    }
    return { ...item, yoy: ((item.value - series[idx - 1].value) / series[idx - 1].value) * 100 };
  });
}

function renderKpis() {
  const seasonYears = aggregateSeasonYears(filteredSeasons);
  const pieceRows = aggregatePieces(filteredPieceMetrics);
  const yoySeries = calcYoYSeries(activeYearlySeries);

  const latest = yoySeries[yoySeries.length - 1] || null;
  const totalPieces = filteredPieceMetrics.length;
  const totalYears = new Set(filteredSeasons.map((row) => Number(row.season_year))).size;
  const efficiency = seasonYears.length ? mean(seasonYears.map((row) => row.kgPerTank).filter((v) => v !== null)) : null;
  const forecast = latest ? linearProjection(activeYearlySeries.map((i) => ({ x: i.year, y: i.value })), latest.year + 1) : null;
  const topPiece = pieceRows[0] || null;

  const cards = [
    {
      title: "Latest Metric",
      value: latest ? `${safeDecimal(latest.value)} ${filtersState.metricType === "tanks_20l" ? "tanks" : ""}` : "-",
      delta: latest?.yoy !== null && latest?.yoy !== undefined ? `${latest.yoy >= 0 ? "+" : ""}${safeDecimal(latest.yoy)}%` : "n/a",
      caption: latest ? `Year ${latest.year}` : "Need records",
    },
    {
      title: "Forecast Next Year",
      value: forecast === null ? "-" : safeDecimal(forecast),
      delta: "model: linear",
      caption: latest ? `Projected for ${latest.year + 1}` : "Need at least 2 years",
    },
    {
      title: "Avg Efficiency",
      value: efficiency === null ? "-" : safeDecimal(efficiency),
      delta: "kg/tank",
      caption: seasonYears.length ? `${seasonYears.length} seasonal aggregates` : "No valid tank data",
    },
    {
      title: "Top Piece",
      value: topPiece ? topPiece.piece : "-",
      delta: topPiece ? `${safeDecimal(topPiece.totalKg, 0)} kg` : "n/a",
      caption: `${totalPieces} piece-year records across ${totalYears} years`,
    },
  ];

  insightKpis.innerHTML = cards
    .map(
      (card) => `
        <article class="insight-kpi-card">
          <p class="insight-kpi-title">${card.title}</p>
          <p class="insight-kpi-value">${card.value}</p>
          <p class="insight-kpi-delta">${card.delta}</p>
          <p class="insight-kpi-caption">${card.caption}</p>
        </article>
      `,
    )
    .join("");
}

function renderSeasonTable() {
  const rows = aggregateSeasonYears(filteredSeasons);
  if (!rows.length) {
    seasonComparisonBody.innerHTML = '<tr><td colspan="6">No season data for current filters.</td></tr>';
    return;
  }

  let prev = null;
  seasonComparisonBody.innerHTML = rows
    .map((row) => {
      let yoy = "-";
      if (prev !== null && prev !== 0) {
        const delta = ((row.actualTotal - prev) / prev) * 100;
        yoy = `${delta >= 0 ? "+" : ""}${safeDecimal(delta)}%`;
      }
      prev = row.actualTotal;

      return `
        <tr>
          <td>${row.year}</td>
          <td>${row.pieces}</td>
          <td>${safeDecimal(row.actualTotal)}</td>
          <td>${safeDecimal(row.tanksTotal, 0)}</td>
          <td>${safeDecimal(row.kgPerTank)}</td>
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
  const lowQuality = pieceDiagnostics.filter((item) => (toNumber(item.quality) ?? 0) < 70);

  const notes = [];
  if (strongestUp && toNumber(strongestUp.slope) !== null) {
    notes.push(`Momentum: ${strongestUp.piece} shows the strongest positive slope (${safeDecimal(strongestUp.slope)} kg/year).`);
  }
  if (mostVolatile && toNumber(mostVolatile.cv) !== null) {
    notes.push(`Volatility watch: ${mostVolatile.piece} has highest CV at ${safeDecimal(mostVolatile.cv)}%.`);
  }
  if (lowQuality.length) {
    notes.push(`Data quality risk on: ${lowQuality.map((item) => item.piece).join(", ")}. Fill tanks consistently.`);
  }

  insightNotes.innerHTML = notes.length ? notes.map((text) => `<p class="insight-note">${text}</p>`).join("") : '<p class="insight-note">No major anomalies detected.</p>';
}

function renderDataQuality() {
  const rows = aggregateSeasonYears(filteredSeasons);
  if (!rows.length) {
    dataQualityBody.innerHTML = '<tr><td colspan="5">No data for quality analysis.</td></tr>';
    return;
  }

  dataQualityBody.innerHTML = rows
    .map((yearRow) => {
      const actualCoverage = yearRow.rows.filter((r) => toNumber(r.actual_chonbol) !== null).length;
      const tanksCoverage = yearRow.rows.filter((r) => (toNumber(r.tanks_20l) ?? 0) > 0).length;
      const total = yearRow.rows.length;
      const actualPct = total > 0 ? (actualCoverage / total) * 100 : 0;
      const tanksPct = total > 0 ? (tanksCoverage / total) * 100 : 0;
      const qualityScore = (actualPct + tanksPct) / 2;

      return `
        <tr>
          <td>${yearRow.year}</td>
          <td>${total}</td>
          <td>${safeDecimal(actualPct)}%</td>
          <td>${safeDecimal(tanksPct)}%</td>
          <td>${safeDecimal(qualityScore)}%</td>
        </tr>
      `;
    })
    .join("");
}

function buildInventoryRows() {
  const byYear = new Map();
  const selectedSeasonIds = new Set(filteredSeasons.map((row) => row.id));
  const seasonById = new Map(filteredSeasons.map((row) => [row.id, row]));
  const filteredSales = sales.filter((row) => selectedSeasonIds.has(row.season_id));
  const filteredUsages = usages.filter((row) => selectedSeasonIds.has(row.season_id));

  for (const season of filteredSeasons) {
    const year = Number(season.season_year);
    const produced = toNumber(season.tanks_20l) ?? 0;
    const sold = toNumber(season.sold_tanks) ?? 0;
    const used = toNumber(season.used_tanks) ?? 0;
    const revenue = toNumber(season.sales_revenue_total) ?? 0;
    const cost = toNumber(season.total_cost) ?? 0;
    const profit = toNumber(season.profit) ?? 0;

    const entry =
      byYear.get(year) ||
      {
        year,
        produced: 0,
        sold: 0,
        used: 0,
        revenue: 0,
        cost: 0,
        profit: 0,
        remaining: 0,
        salesTransactions: 0,
        usageTransactions: 0,
      };

    entry.produced += produced;
    entry.sold += sold;
    entry.used += used;
    entry.revenue += revenue;
    entry.cost += cost;
    entry.profit += profit;
    entry.remaining += produced - sold - used;
    byYear.set(year, entry);
  }

  for (const row of filteredSales) {
    const season = seasonById.get(row.season_id);
    if (!season) continue;
    const year = Number(season.season_year);
    const entry = byYear.get(year);
    if (!entry) continue;
    entry.salesTransactions += 1;
  }

  for (const row of filteredUsages) {
    const season = seasonById.get(row.season_id);
    if (!season) continue;
    const year = Number(season.season_year);
    const entry = byYear.get(year);
    if (!entry) continue;
    entry.usageTransactions += 1;
  }

  return Array.from(byYear.values())
    .sort((a, b) => a.year - b.year)
    .map((row) => ({
      ...row,
      avgSellPrice: row.sold > 0 ? row.revenue / row.sold : null,
    }));
}

function renderInventoryChart() {
  const rows = activeInventoryRows;
  if (!rows.length) {
    inventoryChart.innerHTML = "";
    return;
  }

  const width = 900;
  const height = 320;
  const geo = chartGeometry(rows.map((r) => r.remaining), width, height, 46, 28);

  const points = rows.map((row, idx) => {
    const x = geo.padX + (geo.innerW * idx) / Math.max(rows.length - 1, 1);
    const y = geo.padY + geo.innerH - ((row.remaining - geo.min) / geo.spread) * geo.innerH;
    return { ...row, x, y };
  });

  const polyline = points.map((p) => `${p.x},${p.y}`).join(" ");
  const yTicks = [0, 1, 2, 3, 4].map((idx) => {
    const y = geo.padY + (geo.innerH * idx) / 4;
    const value = geo.max - (geo.spread * idx) / 4;
    return `<line x1="${geo.padX}" y1="${y}" x2="${width - geo.padX}" y2="${y}" class="chart-grid"></line><text x="8" y="${y + 4}" class="chart-axis">${safeDecimal(value)}</text>`;
  });

  const xLabels = points.map((p) => `<text x="${p.x}" y="${height - 8}" text-anchor="middle" class="chart-axis">${p.year}</text>`);
  const markers = points.map((p) => `<circle cx="${p.x}" cy="${p.y}" r="4" class="chart-point"></circle>`);

  inventoryChart.innerHTML = `
    <rect x="0" y="0" width="${width}" height="${height}" class="chart-bg"></rect>
    ${yTicks.join("")}
    <polyline points="${polyline}" class="chart-line"></polyline>
    ${markers.join("")}
    ${xLabels.join("")}
  `;
}

function renderSalesInventory() {
  activeInventoryRows = buildInventoryRows();

  if (!activeInventoryRows.length) {
    salesInventoryKpis.innerHTML = '<p class="insight-note">No season rows for sales/inventory under current filters.</p>';
    salesInventoryNotes.innerHTML = "";
    salesInventoryBody.innerHTML = '<tr><td colspan="8">No inventory analytics available.</td></tr>';
    renderInventoryChart();
    return;
  }

  const totals = activeInventoryRows.reduce(
    (acc, row) => {
      acc.produced += row.produced;
      acc.sold += row.sold;
      acc.used += row.used;
      acc.revenue += row.revenue;
      acc.cost += row.cost;
      acc.profit += row.profit;
      acc.remaining += row.remaining;
      acc.salesTransactions += row.salesTransactions;
      acc.usageTransactions += row.usageTransactions;
      return acc;
    },
    { produced: 0, sold: 0, used: 0, revenue: 0, cost: 0, profit: 0, remaining: 0, salesTransactions: 0, usageTransactions: 0 },
  );

  const avgPrice = totals.sold > 0 ? totals.revenue / totals.sold : null;

  const cards = [
    { title: "Current Inventory", value: safeDecimal(totals.remaining), caption: "Total tanks produced - sold - used" },
    { title: "Sales Revenue", value: safeDecimal(totals.revenue), caption: `${totals.salesTransactions} sale transaction(s)` },
    { title: "Total Usage", value: safeDecimal(totals.used), caption: `${totals.usageTransactions} usage record(s)` },
    { title: "Avg Sell Price", value: avgPrice === null ? "-" : safeDecimal(avgPrice), caption: "Revenue per sold tank" },
  ];

  salesInventoryKpis.innerHTML = cards
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

  salesInventoryNotes.innerHTML = `
    <p class="insight-note">Totals in scope: produced ${safeDecimal(totals.produced)} | sold ${safeDecimal(totals.sold)} | used ${safeDecimal(totals.used)} | remaining ${safeDecimal(totals.remaining)}.</p>
    <p class="insight-note">Profit in scope: ${safeDecimal(totals.profit)} (revenue ${safeDecimal(totals.revenue)} - cost ${safeDecimal(totals.cost)}).</p>
  `;

  salesInventoryBody.innerHTML = activeInventoryRows
    .map(
      (row) => `
        <tr>
          <td>${row.year}</td>
          <td>${safeDecimal(row.produced)}</td>
          <td>${safeDecimal(row.sold)}</td>
          <td>${safeDecimal(row.used)}</td>
          <td>${safeDecimal(row.revenue)}</td>
          <td>${safeDecimal(row.cost)}</td>
          <td>${safeDecimal(row.profit)}</td>
          <td>${safeDecimal(row.remaining)}</td>
        </tr>
      `,
    )
    .join("");

  renderInventoryChart();
}

function renderNarrative() {
  const series = activeYearlySeries;
  if (!series.length) {
    trendStory.innerHTML = '<p class="insight-note">No trend narrative yet. Add records and run analysis.</p>';
    insightRisks.innerHTML = "";
    return;
  }

  const yoy = calcYoYSeries(series);
  const latest = yoy[yoy.length - 1];
  const slope = linearSlope(series.map((p) => ({ x: p.year, y: p.value })));
  const projection = linearProjection(series.map((p) => ({ x: p.year, y: p.value })), series[series.length - 1].year + 1);

  const storyLines = [];
  storyLines.push(`Lens in focus: ${getMetricTypeLabel(filtersState.metricType)} across ${series.length} year points.`);
  if (latest?.yoy !== null && latest?.yoy !== undefined) {
    storyLines.push(`Latest YoY for ${latest.year} is ${latest.yoy >= 0 ? "+" : ""}${safeDecimal(latest.yoy)}%.`);
  }
  if (slope !== null) {
    storyLines.push(`Trend slope is ${safeDecimal(slope)} units per year, indicating ${slope >= 0 ? "growth" : "decline"}.`);
  }
  if (projection !== null) {
    storyLines.push(`Simple linear projection for ${series[series.length - 1].year + 1}: ${safeDecimal(projection)}.`);
  }

  trendStory.innerHTML = storyLines.map((line) => `<p class="insight-note">${line}</p>`).join("");

  const riskLines = [];
  const steepDrops = yoy.filter((point) => point.yoy !== null && point.yoy < -20);
  if (steepDrops.length) {
    riskLines.push(`Sharp drop risk: ${steepDrops.map((d) => `${d.year} (${safeDecimal(d.yoy)}%)`).join(", ")}.`);
  }
  const lowQualityPieces = pieceDiagnostics.filter((d) => (toNumber(d.quality) ?? 0) < 70).slice(0, 3);
  if (lowQualityPieces.length) {
    riskLines.push(`Instrumentation risk: low tank coverage on ${lowQualityPieces.map((p) => p.piece).join(", ")}.`);
  }

  insightRisks.innerHTML = riskLines.length
    ? riskLines.map((line) => `<p class="insight-note insight-risk">${line}</p>`).join("")
    : '<p class="insight-note">No critical risk patterns under current filters.</p>';
}

function chartGeometry(values, width, height, padX, padY) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  return { min, max, spread, innerW, innerH, padX, padY };
}

function renderYearlyChart() {
  const rows = activeYearlySeries;
  if (!rows.length) {
    yearlyChart.innerHTML = "";
    return;
  }

  const width = 900;
  const height = 320;
  const geo = chartGeometry(rows.map((r) => r.value), width, height, 46, 28);

  const points = rows.map((row, idx) => {
    const x = geo.padX + (geo.innerW * idx) / Math.max(rows.length - 1, 1);
    const y = geo.padY + geo.innerH - ((row.value - geo.min) / geo.spread) * geo.innerH;
    return { ...row, x, y };
  });

  const polyline = points.map((p) => `${p.x},${p.y}`).join(" ");
  const areaPath = `M ${points[0].x} ${height - geo.padY} L ${polyline.replace(/ /g, " L ")} L ${points[points.length - 1].x} ${height - geo.padY} Z`;

  const yTicks = [0, 1, 2, 3, 4].map((idx) => {
    const y = geo.padY + (geo.innerH * idx) / 4;
    const value = geo.max - (geo.spread * idx) / 4;
    return `<line x1="${geo.padX}" y1="${y}" x2="${width - geo.padX}" y2="${y}" class="chart-grid"></line><text x="8" y="${y + 4}" class="chart-axis">${safeDecimal(value)}</text>`;
  });

  const xLabels = points.map((p) => `<text x="${p.x}" y="${height - 8}" text-anchor="middle" class="chart-axis">${p.year}</text>`);
  const markers = points.map((p) => `<circle cx="${p.x}" cy="${p.y}" r="4" class="chart-point"></circle>`);

  yearlyChart.innerHTML = `
    <rect x="0" y="0" width="${width}" height="${height}" class="chart-bg"></rect>
    ${yTicks.join("")}
    <path d="${areaPath}" class="chart-area"></path>
    <polyline points="${polyline}" class="chart-line"></polyline>
    ${markers.join("")}
    ${xLabels.join("")}
  `;
}

function renderPieceChart() {
  const rows = aggregatePieces(filteredPieceMetrics).slice(0, 8);
  if (!rows.length) {
    pieceChart.innerHTML = "";
    return;
  }

  const width = 900;
  const height = 320;
  const padX = 140;
  const padY = 24;
  const innerW = width - padX - 24;
  const rowH = (height - padY * 2) / rows.length;
  const maxValue = Math.max(...rows.map((row) => row.totalKg), 1);

  const bars = rows
    .map((row, idx) => {
      const y = padY + idx * rowH + rowH * 0.14;
      const barH = rowH * 0.72;
      const barW = (row.totalKg / maxValue) * innerW;
      return `
        <text x="14" y="${y + barH / 2 + 4}" class="chart-axis">${row.piece}</text>
        <rect x="${padX}" y="${y}" width="${barW}" height="${barH}" rx="8" class="chart-bar"></rect>
        <text x="${padX + barW + 8}" y="${y + barH / 2 + 4}" class="chart-value">${safeDecimal(row.totalKg, 0)}</text>
      `;
    })
    .join("");

  pieceChart.innerHTML = `<rect x="0" y="0" width="${width}" height="${height}" class="chart-bg"></rect>${bars}`;
}

function renderInsights() {
  renderKpis();
  renderSeasonTable();
  renderPieceTable();
  renderSalesInventory();
  renderDiagnostics();
  renderDataQuality();
  renderNarrative();
  renderYearlyChart();
  renderPieceChart();
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
  const [seasonData, pieceData, salesData, usageData] = await Promise.all([
    requestJson(`${API_BASE}/olive-seasons/mine`),
    requestJson(`${API_BASE}/olive-piece-metrics/mine`),
    requestJson(`${API_BASE}/olive-sales/mine`),
    requestJson(`${API_BASE}/olive-usages/mine`),
  ]);

  seasons = seasonData || [];
  pieceMetrics = pieceData || [];
  sales = salesData || [];
  usages = usageData || [];
  analyticsPieceMetrics = buildAnalyticsPieceMetrics();

  populateFilterOptions();
  applyFilters();
}

function applyQuickRange(lastNYears) {
  const allYears = Array.from(new Set(seasons.map((s) => Number(s.season_year)).filter((y) => Number.isFinite(y)))).sort((a, b) => a - b);
  if (!allYears.length) return;

  const max = allYears[allYears.length - 1];
  filtersState.yearTo = max;
  filtersState.yearFrom = Math.max(allYears[0], max - (lastNYears - 1));
  filterYearFrom.value = String(filtersState.yearFrom);
  filterYearTo.value = String(filtersState.yearTo);
  applyFilters();
}

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

rangeLast3Btn.addEventListener("click", () => applyQuickRange(3));
rangeLast5Btn.addEventListener("click", () => applyQuickRange(5));

filtersForm.addEventListener("submit", (event) => {
  event.preventDefault();
  filterApplyBtn.click();
});

refreshBtn.addEventListener("click", fetchAll);
fetchAll().catch((error) => {
  insightKpis.innerHTML = `<p class="message error">${error.message || "Could not load insights"}</p>`;
});

