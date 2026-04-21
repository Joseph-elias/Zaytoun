import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireAuth, roleHome } from "./session.js";

const session = requireAuth();
if (!session) {
  // redirected
}
if (session && !["worker", "farmer"].includes(session.user.role)) {
  window.location.href = roleHome(session.user.role);
}

const listEl = document.getElementById("workers-list");
const form = document.getElementById("filters-form");
const refreshBtn = document.getElementById("refresh-btn");
const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");
const useMyLocationBtn = document.getElementById("use-my-location-btn");
const nearLatInput = form.querySelector('input[name="near_latitude"]');
const nearLngInput = form.querySelector('input[name="near_longitude"]');
const sortByInput = form.querySelector('select[name="sort_by"]');
const mapHint = document.getElementById("map-hint");
const mapEl = document.getElementById("workers-map");
const mapSelectedWorkerEl = document.getElementById("map-selected-worker");
const advancedFiltersEl = document.getElementById("advanced-filters");
const advancedFiltersCountEl = document.getElementById("advanced-filters-count");
const liveWeatherEl = document.getElementById("live-weather");
const liveWeatherIconEl = document.getElementById("live-weather-icon");
const liveWeatherTextEl = document.getElementById("live-weather-text");
const workerDetailOverlayEl = document.getElementById("worker-detail-overlay");
const workerDetailPanelEl = document.getElementById("worker-detail-panel");
const workerDetailTitleEl = document.getElementById("worker-detail-title");
const workerDetailBodyEl = document.getElementById("worker-detail-body");
const workerDetailCloseBtn = document.getElementById("worker-detail-close");
const workersPageMainEl = document.querySelector("main.page-workers");

const isWorker = session?.user?.role === "worker";
const isFarmer = session?.user?.role === "farmer";
const capacityCache = new Map();
const workersById = new Map();
let farmerSeasons = [];
let openedWorkerId = null;

let map = null;
let markersLayer = null;
let mapLegendControl = null;
let mapLegendEl = null;
const markersByWorkerId = new Map();
let weatherRefreshTimerId = null;
let weatherLastCoords = null;
const WEATHER_REFRESH_MS = 15 * 60 * 1000;
let lastFocusedElement = null;
const ADVANCED_FILTERS_STORAGE_KEY = "workers_advanced_filters_open_v1";
const advancedFilterFields = [
  "work_slot",
  "sort_by",
  "max_distance_km",
  "rate_type",
  "min_men_rate",
  "max_men_rate",
  "min_women_rate",
  "max_women_rate",
];

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (${session.user.role}).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "workers.html");
}
if (listEl && isFarmer) {
  listEl.classList.add("workers-compact-list");
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./index.html";
});

function money(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(2);
}

function displayName(value) {
  const raw = String(value || "").trim();
  if (!raw) return "-";
  return raw
    .split(/\s+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { day: "2-digit", month: "long", year: "numeric" });
}

function dateBadges(dates) {
  return (dates || []).map((d) => `<span class="badge day">${formatDate(d)}</span>`).join(" ");
}

function slotLabel(slot) {
  return slot === "extra_time" ? "Extra Time" : "Full Day";
}

function slotBadges(windows) {
  const rows = windows || [];
  if (!rows.length) return "-";
  return rows
    .map((item) => `<span class="badge day">${formatDate(item.work_date)} - ${slotLabel(item.slot_type)}</span>`)
    .join(" ");
}

function selectedWorkDate() {
  const raw = form.elements.work_date?.value;
  return raw ? String(raw).trim() : "";
}

function selectedWorkSlot() {
  const raw = form.elements.work_slot?.value;
  return raw ? String(raw).trim() : "";
}

function distanceText(worker) {
  if (worker.distance_km === null || worker.distance_km === undefined) return "-";
  return `${Number(worker.distance_km).toFixed(2)} km`;
}

function distanceBadgeClass(worker) {
  const distance = worker.distance_km;
  if (distance === null || distance === undefined) return "na";
  if (distance <= 5) return "near";
  if (distance <= 20) return "medium";
  return "far";
}

function seasonOptions() {
  if (!isFarmer) return "";
  if (!farmerSeasons.length) return '<option value="">No seasons yet</option>';
  return ['<option value="">Select season</option>', ...farmerSeasons.map((s) => `<option value="${s.id}">${s.season_year} - ${s.land_piece_name}</option>`)].join("");
}

function seasonOptionsWithSelected(selectedSeasonId = "") {
  const selected = String(selectedSeasonId || "").trim();
  if (!isFarmer) return "";
  if (!farmerSeasons.length) return '<option value="">No seasons yet</option>';
  const options = ['<option value="">Select season</option>'];
  for (const season of farmerSeasons) {
    const isSelected = selected && selected === season.id ? "selected" : "";
    options.push(`<option value="${season.id}" ${isSelected}>${season.season_year} - ${season.land_piece_name}</option>`);
  }
  return options.join("");
}

async function fetchFarmerSeasons() {
  if (!isFarmer) return;
  try {
    const response = await fetch(`${API_BASE}/olive-seasons/mine`, { headers: authHeaders() });
    if (!response.ok) {
      farmerSeasons = [];
      return;
    }
    farmerSeasons = await response.json();
  } catch {
    farmerSeasons = [];
  }
}
function bookingRequestRow(defaultDate = "", defaultSlot = "full_day", defaultSeasonId = "") {
  const seasonRequired = farmerSeasons.length ? "required" : "";
  return `
    <div class="worker-grid full booking-request-row">
      <label>Season
        <select name="season_id" ${seasonRequired}>
          ${seasonOptionsWithSelected(defaultSeasonId)}
        </select>
      </label>
      <label>Work Date<input name="work_date" type="date" value="${defaultDate}" required /></label>
      <label>Work Slot
        <select name="work_slot" required>
          <option value="full_day" ${defaultSlot === "full_day" ? "selected" : ""}>Full Day</option>
          <option value="extra_time" ${defaultSlot === "extra_time" ? "selected" : ""}>Extra Time</option>
        </select>
      </label>
      <label>Men Needed<input name="requested_men" type="number" min="0" value="0" required /></label>
      <label>Women Needed<input name="requested_women" type="number" min="0" value="0" required /></label>
      <div class="actions-row" style="align-items:end;">
        <button class="btn ghost" type="button" data-remove-booking-row>Remove</button>
      </div>
      <p class="message full" data-row-capacity></p>
    </div>
  `;
}

function bookingForm(worker) {
  if (!isFarmer) return "";

  const filterDate = selectedWorkDate();
  const filterSlot = selectedWorkSlot() || "full_day";
  const remainingMen = worker.remaining_men_count ?? worker.men_count;
  const remainingWomen = worker.remaining_women_count ?? worker.women_count;
  const liveRemaining = filterDate && worker.remaining_men_count !== null && worker.remaining_women_count !== null;

  return `
    <form class="booking-form" data-worker-id="${worker.id}">
      <h4>Book This Team</h4>
      <div class="full"><strong>Date:</strong> ${filterDate ? formatDate(filterDate) : "Pick date(s) below"}</div>
      <div class="full"><strong>Default Slot:</strong> ${slotLabel(filterSlot)}</div>
      <div class="full"><strong>Remaining Capacity:</strong> ${remainingMen} men, ${remainingWomen} women${liveRemaining ? " (live for selected date)" : ""}</div>
      <p class="message">For each row, choose date, slot, and the season (land piece) you want.</p>
      <div class="full" data-booking-requests>${bookingRequestRow(filterDate, filterSlot)}</div>
      <div class="actions-row">
        <button class="btn ghost" type="button" data-add-booking-row>Add Another Date</button>
      </div>
      <label class="full">Note<textarea name="note" rows="2" placeholder="Optional note for all selected dates"></textarea></label>
      <button class="btn" type="submit">Send Booking Request</button>
      <p class="message booking-submit-message"></p>
    </form>
  `;
}

function card(worker) {
  const workerName = displayName(worker.name);
  const badgeClass = worker.available ? "available" : "busy";
  const badgeText = worker.available ? "Available" : "Busy";

  const menDisplay = worker.remaining_men_count ?? worker.men_count;
  const womenDisplay = worker.remaining_women_count ?? worker.women_count;
  const distanceBadge = distanceBadgeClass(worker);
  const distanceLabel = distanceText(worker);
  const compactMeta = `
    <div class="worker-compact-meta">
      <span class="badge day">${worker.village || "Unknown village"}</span>
      <span class="badge distance-badge ${distanceBadge}">${distanceLabel}</span>
      <span class="badge day">${menDisplay} men</span>
      <span class="badge day">${womenDisplay} women</span>
      <span class="badge day">${worker.rate_type}</span>
    </div>
  `;

  if (isFarmer) {
    const notePreview = String(worker.overtime_note || "").trim();
    return `
      <article class="worker-card worker-card-widget" data-worker-card-id="${worker.id}">
        <button class="worker-card-widget-trigger" type="button" data-open-worker="${worker.id}">
          <div class="list-head">
            <h3>${workerName}</h3>
            <span class="badge ${badgeClass}">${badgeText}</span>
          </div>
          ${compactMeta}
          <p class="worker-widget-note">${notePreview || "No special note."}</p>
          <span class="worker-widget-cta">Open full profile</span>
        </button>
      </article>
    `;
  }

  return `
    <article class="worker-card" data-worker-card-id="${worker.id}">
      <div class="list-head">
        <h3>${worker.name}</h3>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="worker-grid">
        <div><strong>Village:</strong> ${worker.village}</div>
        <div><strong>Address:</strong> ${worker.address || "-"}</div>
        <div><strong>Phone:</strong> ${worker.phone}</div>
        <div><strong>Distance:</strong> <span class="badge distance-badge ${distanceBadge}">${distanceLabel}</span></div>
        <div><strong>Men:</strong> ${menDisplay} | <strong>Rate:</strong> ${money(worker.men_rate_value)}</div>
        <div><strong>Women:</strong> ${womenDisplay} | <strong>Rate:</strong> ${money(worker.women_rate_value)}</div>
        <div><strong>Rate Type:</strong> ${worker.rate_type}</div>
        <div><strong>Overtime:</strong> ${worker.overtime_open ? "Yes" : "No"}</div>
        <div class="full"><strong>Available Dates:</strong> ${dateBadges(worker.available_dates)}</div>
        <div class="full"><strong>Bookable Windows:</strong> ${slotBadges(worker.availability_windows)}</div>
        <div class="full"><strong>Note:</strong> ${worker.overtime_note || "-"}</div>
      </div>
      ${
        isWorker
          ? `<button class="btn ghost" data-id="${worker.id}" data-next="${!worker.available}">Mark as ${worker.available ? "Busy" : "Available"}</button>`
          : ""
      }
      ${bookingForm(worker)}
    </article>
  `;
}

function workerPanelDetails(worker) {
  const workerName = displayName(worker.name);
  const badgeClass = worker.available ? "available" : "busy";
  const badgeText = worker.available ? "Available" : "Busy";
  const menDisplay = worker.remaining_men_count ?? worker.men_count;
  const womenDisplay = worker.remaining_women_count ?? worker.women_count;
  const distanceBadge = distanceBadgeClass(worker);

  return `
    <article class="worker-profile-shell" data-worker-profile="${worker.id}">
      <div class="worker-profile-layout">
        <aside class="worker-profile-left">
          <section class="worker-profile-overview">
            <div class="list-head">
              <h3>${workerName}</h3>
              <span class="badge ${badgeClass}">${badgeText}</span>
            </div>
            <div class="worker-compact-meta">
              <span class="badge day">${worker.village || "Unknown village"}</span>
              <span class="badge distance-badge ${distanceBadge}">${distanceText(worker)}</span>
              <span class="badge day">${worker.rate_type}</span>
            </div>
          </section>
          <section class="worker-profile-stats">
            <div class="worker-stat-card">
              <strong>${menDisplay}</strong>
              <span>Men Available</span>
              <small>Rate: ${money(worker.men_rate_value)}</small>
            </div>
            <div class="worker-stat-card">
              <strong>${womenDisplay}</strong>
              <span>Women Available</span>
              <small>Rate: ${money(worker.women_rate_value)}</small>
            </div>
            <div class="worker-stat-card">
              <strong>${worker.overtime_open ? "Yes" : "No"}</strong>
              <span>Overtime</span>
              <small>${worker.overtime_note || "No extra note"}</small>
            </div>
          </section>
        </aside>

        <section class="worker-profile-right">
          <section class="worker-grid worker-profile-grid">
            <div><strong>Village:</strong> ${worker.village}</div>
            <div><strong>Address:</strong> ${worker.address || "-"}</div>
            <div><strong>Phone:</strong> ${worker.phone}</div>
            <div><strong>Distance:</strong> <span class="badge distance-badge ${distanceBadge}">${distanceText(worker)}</span></div>
            <div><strong>Rate Type:</strong> ${worker.rate_type}</div>
            <div><strong>Status:</strong> ${badgeText}</div>
            <div class="full"><strong>Available Dates:</strong> ${dateBadges(worker.available_dates)}</div>
            <div class="full"><strong>Bookable Windows:</strong> ${slotBadges(worker.availability_windows)}</div>
            <div class="full"><strong>Note:</strong> ${worker.overtime_note || "-"}</div>
          </section>
          <section class="worker-profile-booking">
            ${bookingForm(worker)}
          </section>
        </section>
      </div>
    </article>
  `;
}

function closeWorkerPanel() {
  openedWorkerId = null;
  document.body.classList.remove("worker-panel-open");
  if (workersPageMainEl) workersPageMainEl.removeAttribute("inert");
  if (workerDetailPanelEl) {
    workerDetailPanelEl.classList.remove("is-open");
    workerDetailPanelEl.hidden = true;
    workerDetailPanelEl.setAttribute("aria-hidden", "true");
  }
  if (workerDetailOverlayEl) {
    workerDetailOverlayEl.classList.remove("is-open");
    workerDetailOverlayEl.hidden = true;
  }
  if (lastFocusedElement && typeof lastFocusedElement.focus === "function") lastFocusedElement.focus();
  lastFocusedElement = null;
}

function openWorkerPanel(workerId, { scrollCard = false } = {}) {
  if (!isFarmer) return;
  const worker = workersById.get(workerId);
  if (!worker || !workerDetailBodyEl || !workerDetailPanelEl || !workerDetailOverlayEl) return;

  openedWorkerId = workerId;
  lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  if (workerDetailTitleEl) workerDetailTitleEl.textContent = displayName(worker.name);
  workerDetailBodyEl.innerHTML = workerPanelDetails(worker);

  if (workersPageMainEl) workersPageMainEl.setAttribute("inert", "");
  workerDetailPanelEl.hidden = false;
  workerDetailPanelEl.removeAttribute("aria-hidden");
  workerDetailOverlayEl.hidden = false;
  requestAnimationFrame(() => {
    workerDetailPanelEl.classList.add("is-open");
    workerDetailOverlayEl.classList.add("is-open");
    (workerDetailCloseBtn || workerDetailPanelEl).focus();
  });
  document.body.classList.add("worker-panel-open");

  const cardEl = document.querySelector(`[data-worker-card-id="${workerId}"]`);
  if (cardEl) {
    if (scrollCard) cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
    cardEl.classList.add("worker-card-highlight");
    window.setTimeout(() => cardEl.classList.remove("worker-card-highlight"), 1400);
  }
}

function panelFocusableElements() {
  if (!workerDetailPanelEl || workerDetailPanelEl.hidden) return [];
  const candidates = workerDetailPanelEl.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  );
  return [...candidates].filter((element) => element.getClientRects().length > 0);
}

function trapWorkerPanelFocus(event) {
  if (event.key !== "Tab" || workerDetailPanelEl?.hidden) return;
  const focusable = panelFocusableElements();
  if (!focusable.length) {
    event.preventDefault();
    workerDetailPanelEl?.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const activeElement = document.activeElement;

  if (event.shiftKey) {
    if (activeElement === first || !workerDetailPanelEl?.contains(activeElement)) {
      event.preventDefault();
      last.focus();
    }
    return;
  }

  if (activeElement === last || !workerDetailPanelEl?.contains(activeElement)) {
    event.preventDefault();
    first.focus();
  }
}

function setWorkerActionMessage(button, text, isError = true) {
  const cardEl = button.closest("[data-worker-card-id]");
  if (!cardEl) return;

  let messageEl = cardEl.querySelector(".worker-action-message");
  if (!messageEl) {
    messageEl = document.createElement("p");
    messageEl.className = "message worker-action-message";
    button.insertAdjacentElement("afterend", messageEl);
  }

  messageEl.textContent = text || "";
  messageEl.className = `message worker-action-message ${isError ? "error" : "success"}`;
}

function buildQuery() {
  const fd = new FormData(form);
  const params = new URLSearchParams();

  [
    "village",
    "available",
    "work_date",
    "work_slot",
    "sort_by",
    "max_distance_km",
    "near_latitude",
    "near_longitude",
    "rate_type",
    "min_men_rate",
    "max_men_rate",
    "min_women_rate",
    "max_women_rate",
  ].forEach((key) => {
    const raw = fd.get(key);
    if (raw !== null && String(raw).trim() !== "") params.set(key, String(raw).trim());
  });

  return params.toString();
}

function hasAdvancedFiltersActive() {
  if (!form) return false;
  return advancedFilterFields.some((fieldName) => {
    const value = form.elements[fieldName]?.value;
    return String(value || "").trim() !== "";
  });
}

function activeAdvancedFiltersCount() {
  if (!form) return 0;
  return advancedFilterFields.reduce((count, fieldName) => {
    const value = String(form.elements[fieldName]?.value || "").trim();
    return value ? count + 1 : count;
  }, 0);
}

function updateAdvancedFiltersSummary() {
  if (!advancedFiltersCountEl) return;
  const count = activeAdvancedFiltersCount();
  if (!count) {
    advancedFiltersCountEl.hidden = true;
    advancedFiltersCountEl.textContent = "";
    return;
  }
  advancedFiltersCountEl.hidden = false;
  advancedFiltersCountEl.textContent = `${count} active`;
}

function readStoredAdvancedFiltersOpen() {
  try {
    const raw = window.localStorage.getItem(ADVANCED_FILTERS_STORAGE_KEY);
    if (raw === "open") return true;
    if (raw === "closed") return false;
  } catch {
    // ignore storage issues
  }
  return null;
}

function writeStoredAdvancedFiltersOpen(isOpen) {
  try {
    window.localStorage.setItem(ADVANCED_FILTERS_STORAGE_KEY, isOpen ? "open" : "closed");
  } catch {
    // ignore storage issues
  }
}

function setAdvancedFiltersOpen(isOpen, { persist = true } = {}) {
  if (!advancedFiltersEl) return;
  advancedFiltersEl.open = Boolean(isOpen);
  if (persist) writeStoredAdvancedFiltersOpen(Boolean(isOpen));
}

function syncAdvancedFiltersOpenState(forceOpen = false) {
  if (!advancedFiltersEl) return;
  if (forceOpen) {
    setAdvancedFiltersOpen(true);
    updateAdvancedFiltersSummary();
    return;
  }

  const stored = readStoredAdvancedFiltersOpen();
  if (stored !== null) {
    setAdvancedFiltersOpen(stored, { persist: false });
    updateAdvancedFiltersSummary();
    return;
  }

  setAdvancedFiltersOpen(hasAdvancedFiltersActive(), { persist: false });
  updateAdvancedFiltersSummary();
}

function extractApiErrorMessage(err, fallbackMessage) {
  const detail = err?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    if (typeof first === "string") return first;
    if (first && typeof first.msg === "string") return first.msg;
    try {
      return JSON.stringify(first);
    } catch {
      return fallbackMessage;
    }
  }

  return fallbackMessage;
}

function weatherCodeLabel(code) {
  const map = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Strong showers",
    82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Heavy thunderstorm hail",
  };
  return map[Number(code)] || "Weather update";
}

function weatherCodeIcon(code) {
  const value = Number(code);
  if (value === 0) return "☀";
  if (value === 1 || value === 2) return "⛅";
  if (value === 3) return "☁";
  if (value === 45 || value === 48) return "🌫";
  if ((value >= 51 && value <= 67) || (value >= 80 && value <= 82)) return "🌧";
  if (value >= 71 && value <= 77) return "❄";
  if (value >= 95) return "⛈";
  return "○";
}

function setLiveWeatherMessage(text, isError = false, icon = "○") {
  if (!liveWeatherEl) return;
  if (liveWeatherTextEl) liveWeatherTextEl.textContent = text;
  else liveWeatherEl.textContent = text;
  if (liveWeatherIconEl) liveWeatherIconEl.textContent = icon;
  liveWeatherEl.classList.toggle("error", Boolean(isError));
}

async function fetchLiveWeather(latitude, longitude) {
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.searchParams.set("latitude", String(latitude));
  url.searchParams.set("longitude", String(longitude));
  url.searchParams.set("current", "temperature_2m,apparent_temperature,weather_code,wind_speed_10m");
  url.searchParams.set("timezone", "auto");

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error("Weather service unavailable.");
  const data = await response.json();
  const current = data?.current || {};
  const units = data?.current_units || {};

  const temp = current.temperature_2m;
  const feels = current.apparent_temperature;
  const wind = current.wind_speed_10m;
  const code = current.weather_code;

  if (temp === undefined || code === undefined) throw new Error("No weather data returned.");

  const tempUnit = units.temperature_2m || "C";
  const windUnit = units.wind_speed_10m || "km/h";
  return {
    summary: `Live weather: ${Number(temp).toFixed(1)}${tempUnit}, feels ${Number(feels ?? temp).toFixed(1)}${tempUnit}, ${weatherCodeLabel(code)}, wind ${Number(wind ?? 0).toFixed(1)} ${windUnit}.`,
    icon: weatherCodeIcon(code),
  };
}

function scheduleLiveWeatherRefresh() {
  if (weatherRefreshTimerId) {
    window.clearInterval(weatherRefreshTimerId);
    weatherRefreshTimerId = null;
  }
  if (!weatherLastCoords) return;
  weatherRefreshTimerId = window.setInterval(() => {
    refreshLiveWeatherFromCoords(weatherLastCoords.latitude, weatherLastCoords.longitude);
  }, WEATHER_REFRESH_MS);
}

async function refreshLiveWeatherFromCoords(latitude, longitude) {
  if (latitude === null || latitude === undefined || longitude === null || longitude === undefined) return;
  weatherLastCoords = { latitude: Number(latitude), longitude: Number(longitude) };
  scheduleLiveWeatherRefresh();
  setLiveWeatherMessage("Live weather: loading...", false, "○");
  try {
    const data = await fetchLiveWeather(latitude, longitude);
    setLiveWeatherMessage(data.summary, false, data.icon);
  } catch (error) {
    setLiveWeatherMessage(error.message || "Could not load live weather.", true, "!");
  }
}

function ensureMap() {
  if (map || !window.L || !mapEl) return;

  map = window.L.map("workers-map").setView([33.8938, 35.5018], 8);
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  markersLayer = window.L.layerGroup().addTo(map);
  ensureMapLegend();
}

function ensureMapLegend() {
  if (!map || !window.L || mapLegendControl) return;
  mapLegendControl = window.L.control({ position: "bottomleft" });
  mapLegendControl.onAdd = () => {
    const el = window.L.DomUtil.create("div", "workers-map-legend");
    el.innerHTML = `
      <p class="workers-map-legend-title">Map Legend</p>
      <div class="workers-map-legend-row"><span class="swatch available"></span><span>Available</span><strong data-map-available>0</strong></div>
      <div class="workers-map-legend-row"><span class="swatch busy"></span><span>Busy</span><strong data-map-busy>0</strong></div>
      <p class="workers-map-legend-note">Dense spots show <code>+N</code>.</p>
    `;
    window.L.DomEvent.disableClickPropagation(el);
    window.L.DomEvent.disableScrollPropagation(el);
    mapLegendEl = el;
    return el;
  };
  mapLegendControl.addTo(map);
}

function renderMapLegend(workers) {
  if (!mapLegendEl) return;
  const available = workers.filter((worker) => worker.available).length;
  const busy = Math.max(0, workers.length - available);
  const availableEl = mapLegendEl.querySelector("[data-map-available]");
  const busyEl = mapLegendEl.querySelector("[data-map-busy]");
  if (availableEl) availableEl.textContent = String(available);
  if (busyEl) busyEl.textContent = String(busy);
}

function markerTooltipHtml(worker) {
  const workerName = displayName(worker.name);
  const men = worker.remaining_men_count ?? worker.men_count;
  const women = worker.remaining_women_count ?? worker.women_count;
  return `
    <div class="map-tip">
      <strong>${workerName}</strong>
      <small>${worker.village || "Unknown village"}</small>
      <small>${men} men | ${women} women</small>
    </div>
  `;
}

function markerPopupHtml(worker) {
  const workerName = displayName(worker.name);
  const men = worker.remaining_men_count ?? worker.men_count;
  const women = worker.remaining_women_count ?? worker.women_count;
  const badgeClass = worker.available ? "available" : "busy";
  const badgeText = worker.available ? "Available" : "Busy";
  return `
    <article class="map-popup">
      <header class="map-popup-head">
        <strong>${workerName}</strong>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </header>
      <p class="map-popup-line"><strong>Village:</strong> ${worker.village || "-"}</p>
      <p class="map-popup-line"><strong>Capacity:</strong> ${men} men, ${women} women</p>
      <p class="map-popup-line"><strong>Distance:</strong> ${distanceText(worker)}</p>
      <p class="map-popup-line"><strong>Rate type:</strong> ${worker.rate_type}</p>
    </article>
  `;
}

function selectedWorkerDetailsHtml(worker) {
  const workerName = displayName(worker.name);
  const men = worker.remaining_men_count ?? worker.men_count;
  const women = worker.remaining_women_count ?? worker.women_count;
  const badgeClass = worker.available ? "available" : "busy";
  const badgeText = worker.available ? "Available" : "Busy";
  return `
    <article class="map-selected-card">
      <div class="map-selected-head">
        <strong>${workerName}</strong>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="map-selected-grid">
        <p><strong>Village:</strong> ${worker.village}</p>
        <p><strong>Distance:</strong> ${distanceText(worker)}</p>
        <p><strong>Address:</strong> ${worker.address || "No address"}</p>
        <p><strong>Phone:</strong> ${worker.phone || "-"}</p>
        <p><strong>Capacity:</strong> ${men} men, ${women} women</p>
        <p><strong>Rate type:</strong> ${worker.rate_type}</p>
      </div>
      ${
        isFarmer
          ? `<div class="actions-row"><button class="btn" type="button" data-open-worker-from-map="${worker.id}">Open Full Profile</button></div>`
          : ""
      }
    </article>
  `;
}

function renderSelectedWorker(worker) {
  if (!mapSelectedWorkerEl) return;
  if (!worker) {
    mapSelectedWorkerEl.innerHTML = '<p class="sub">Select a worker on the map to view full details here.</p>';
    return;
  }
  mapSelectedWorkerEl.innerHTML = selectedWorkerDetailsHtml(worker);
  const openProfileBtn = mapSelectedWorkerEl.querySelector("[data-open-worker-from-map]");
  if (openProfileBtn) {
    openProfileBtn.addEventListener("click", () => openWorkerPanel(worker.id, { scrollCard: true }));
  }
}

function offsetLatLng(lat, lng, index, total) {
  if (total <= 1) return [lat, lng];

  const radiusMeters = total <= 3 ? 24 : total <= 6 ? 32 : 40;
  const angle = (Math.PI * 2 * index) / total;
  const dx = Math.cos(angle) * radiusMeters;
  const dy = Math.sin(angle) * radiusMeters;
  const latOffset = dy / 111320;
  const lngOffset = dx / (111320 * Math.max(0.2, Math.cos((lat * Math.PI) / 180)));
  return [lat + latOffset, lng + lngOffset];
}

function renderWorkersMap(workers) {
  ensureMap();
  if (!map || !markersLayer) return;

  markersLayer.clearLayers();
  markersByWorkerId.clear();
  workersById.clear();

  const withCoords = workers.filter((worker) => worker.latitude !== null && worker.longitude !== null);
  if (!withCoords.length) {
    mapHint.textContent = "No worker locations available for this filter.";
    renderMapLegend([]);
    renderSelectedWorker(null);
    return;
  }

  const coordinateBuckets = new Map();
  withCoords.forEach((worker) => {
    workersById.set(worker.id, worker);
    const key = `${Number(worker.latitude).toFixed(5)}|${Number(worker.longitude).toFixed(5)}`;
    if (!coordinateBuckets.has(key)) coordinateBuckets.set(key, []);
    coordinateBuckets.get(key).push(worker);
  });

  const bounds = [];
  let crowdedLocations = 0;
  coordinateBuckets.forEach((entries) => {
    if (entries.length > 1) crowdedLocations += 1;
    if (entries.length <= 1) return;
    const base = entries[0];
    const crowdMarker = window.L.marker([base.latitude, base.longitude], {
      interactive: false,
      keyboard: false,
      zIndexOffset: -300,
      icon: window.L.divIcon({
        className: "worker-crowd-wrap",
        html: `<div class="worker-crowd-badge">+${entries.length - 1}</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      }),
    });
    crowdMarker.addTo(markersLayer);
  });

  withCoords.forEach((worker) => {
    const key = `${Number(worker.latitude).toFixed(5)}|${Number(worker.longitude).toFixed(5)}`;
    const siblings = coordinateBuckets.get(key) || [];
    const indexInBucket = siblings.findIndex((item) => item.id === worker.id);
    const [pinLat, pinLng] = offsetLatLng(worker.latitude, worker.longitude, Math.max(0, indexInBucket), siblings.length);
    const men = worker.remaining_men_count ?? worker.men_count;
    const women = worker.remaining_women_count ?? worker.women_count;
    const total = Math.max(0, Number(men || 0) + Number(women || 0));
    const statusClass = worker.available ? "available" : "busy";
    const marker = window.L.marker([worker.latitude, worker.longitude], {
      title: displayName(worker.name),
      zIndexOffset: worker.available ? 180 : 80,
      icon: window.L.divIcon({
        className: "worker-pin-wrap",
        html: `<div class=\"worker-pin ${statusClass}\"><span class=\"worker-pin-core\"></span><span class=\"worker-pin-total\">${total}</span></div>`,
        iconSize: [46, 46],
        iconAnchor: [23, 38],
      }),
    });
    marker.setLatLng([pinLat, pinLng]);

    marker.bindTooltip(markerTooltipHtml(worker), {
      direction: "top",
      offset: [0, -18],
      className: "worker-map-tip",
      opacity: 0.95,
    });
    marker.bindPopup(markerPopupHtml(worker), {
      className: "worker-map-popup",
      closeButton: false,
      offset: [0, -14],
    });
    marker.on("mouseover", () => marker.openTooltip());
    marker.on("mouseout", () => marker.closeTooltip());
    marker.on("click", () => {
      renderSelectedWorker(worker);
      marker.openPopup();
      if (!isFarmer) {
        const cardEl = document.querySelector(`[data-worker-card-id="${worker.id}"]`);
        if (!cardEl) return;
        cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
        cardEl.classList.add("worker-card-highlight");
        window.setTimeout(() => cardEl.classList.remove("worker-card-highlight"), 1400);
      }
    });

    marker.addTo(markersLayer);
    markersByWorkerId.set(worker.id, marker);
    bounds.push([pinLat, pinLng]);
  });

  if (bounds.length === 1) {
    map.setView(bounds[0], 13);
  } else {
    map.fitBounds(bounds, { padding: [20, 20] });
  }

  mapHint.textContent = `${withCoords.length} worker location${withCoords.length > 1 ? "s" : ""} on map. Click a pin to preview details${crowdedLocations ? ` (${crowdedLocations} crowded spot${crowdedLocations > 1 ? "s" : ""} spread for clarity)` : ""}.`;
  renderMapLegend(withCoords);
  renderSelectedWorker(null);
}

async function fetchWorkers() {
  listEl.innerHTML = "Loading workers...";
  try {
    const query = buildQuery();
    const response = await fetch(`${API_BASE}/workers${query ? `?${query}` : ""}`, {
      headers: authHeaders(),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./index.html";
      return;
    }

    if (!response.ok) throw new Error("Could not load workers");

    const workers = await response.json();
    if (!workers.length) {
      listEl.innerHTML = "No workers found for these filters.";
      renderWorkersMap([]);
      return;
    }

    listEl.innerHTML = workers.map(card).join("");
    if (isFarmer && openedWorkerId && !workers.some((worker) => worker.id === openedWorkerId)) closeWorkerPanel();
    if (isFarmer && openedWorkerId) openWorkerPanel(openedWorkerId);
    renderWorkersMap(workers);
  } catch (error) {
    listEl.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

async function fetchDateCapacity(workerId, workDate, workSlot) {
  const key = `${workerId}|${workDate}|${workSlot}`;
  if (capacityCache.has(key)) return capacityCache.get(key);

  const response = await fetch(
    `${API_BASE}/workers?work_date=${encodeURIComponent(workDate)}&work_slot=${encodeURIComponent(workSlot)}`,
    {
    headers: authHeaders(),
    }
  );

  if (response.status === 401 || response.status === 403) {
    clearSession();
    window.location.href = "./index.html";
    return null;
  }
  if (!response.ok) return null;

  const workers = await response.json();
  const worker = workers.find((item) => item.id === workerId);
  if (!worker) {
    capacityCache.set(key, null);
    return null;
  }

  const value = {
    men: worker.remaining_men_count ?? worker.men_count,
    women: worker.remaining_women_count ?? worker.women_count,
  };
  capacityCache.set(key, value);
  return value;
}

async function updateRowCapacity(rowEl, workerId) {
  const capacityEl = rowEl.querySelector("[data-row-capacity]");
  const dateInput = rowEl.querySelector('input[name="work_date"]');
  const slotInput = rowEl.querySelector('select[name="work_slot"]');
  if (!capacityEl || !dateInput || !slotInput) return;

  const workDate = String(dateInput.value || "").trim();
  const workSlot = String(slotInput.value || "full_day").trim() || "full_day";
  if (!workDate) {
    capacityEl.textContent = "";
    capacityEl.className = "message";
    return;
  }

  capacityEl.textContent = "Checking availability...";
  capacityEl.className = "message";

  try {
    const capacity = await fetchDateCapacity(workerId, workDate, workSlot);
    if (!capacity) {
      capacityEl.textContent = "Not available for this date and slot.";
      capacityEl.className = "message error";
      return;
    }

    capacityEl.textContent = `Remaining on ${formatDate(workDate)} (${slotLabel(workSlot)}): ${capacity.men} men, ${capacity.women} women`;
    capacityEl.className = "message success";
  } catch {
    capacityEl.textContent = "Could not check date capacity.";
    capacityEl.className = "message error";
  }
}

useMyLocationBtn?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    mapHint.textContent = "Geolocation not supported on this device.";
    setLiveWeatherMessage("Live weather: geolocation not supported on this device.", true, "!");
    return;
  }

  setLiveWeatherMessage("Live weather: reading your location...", false, "⌖");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      nearLatInput.value = String(position.coords.latitude);
      nearLngInput.value = String(position.coords.longitude);
      if (sortByInput) sortByInput.value = "distance";
      syncAdvancedFiltersOpenState(true);
      refreshLiveWeatherFromCoords(position.coords.latitude, position.coords.longitude);
      fetchFarmerSeasons().then(fetchWorkers);
    },
    () => {
      mapHint.textContent = "Could not get your location.";
      setLiveWeatherMessage('Live weather: location denied. Tap "Use My Location" and allow access.', true, "!");
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
});

if (session?.user?.latitude !== null && session?.user?.longitude !== null) {
  nearLatInput.value = String(session.user.latitude);
  nearLngInput.value = String(session.user.longitude);
  syncAdvancedFiltersOpenState(false);
  refreshLiveWeatherFromCoords(session.user.latitude, session.user.longitude);
} else {
  setLiveWeatherMessage('Live weather: tap "Use My Location".', false, "○");
  syncAdvancedFiltersOpenState(false);
}

workerDetailCloseBtn?.addEventListener("click", closeWorkerPanel);
workerDetailOverlayEl?.addEventListener("click", closeWorkerPanel);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !workerDetailPanelEl?.hidden) {
    closeWorkerPanel();
    return;
  }
  trapWorkerPanelFocus(event);
});
advancedFiltersEl?.addEventListener("toggle", () => {
  writeStoredAdvancedFiltersOpen(advancedFiltersEl.open);
});
form.addEventListener("input", updateAdvancedFiltersSummary);
form.addEventListener("change", updateAdvancedFiltersSummary);

function handleBookingRowsClick(event) {
  const addRowButton = event.target.closest("button[data-add-booking-row]");
  if (addRowButton) {
    const bookingFormEl = addRowButton.closest("form.booking-form");
    if (!bookingFormEl) return true;
    const container = bookingFormEl.querySelector("[data-booking-requests]");
    if (!container) return true;
    container.insertAdjacentHTML("beforeend", bookingRequestRow());
    return true;
  }

  const removeRowButton = event.target.closest("button[data-remove-booking-row]");
  if (!removeRowButton) return false;

  const bookingFormEl = removeRowButton.closest("form.booking-form");
  if (!bookingFormEl) return true;
  const container = bookingFormEl.querySelector("[data-booking-requests]");
  if (!container) return true;

  const rows = [...container.querySelectorAll(".booking-request-row")];
  if (rows.length <= 1) {
    const row = rows[0];
    row.querySelectorAll('input[name="work_date"], input[name="requested_men"], input[name="requested_women"]').forEach((input) => {
      if (input.name === "work_date") input.value = "";
      else input.value = "0";
    });
    const slotInput = row.querySelector('select[name="work_slot"]');
    if (slotInput) slotInput.value = "full_day";
    const capacityEl = row.querySelector("[data-row-capacity]");
    if (capacityEl) {
      capacityEl.textContent = "";
      capacityEl.className = "message";
    }
    return true;
  }

  const row = removeRowButton.closest(".booking-request-row");
  if (row) row.remove();
  return true;
}

async function handleBookingRowCapacityChange(event) {
  const changedInput = event.target.closest('input[name="work_date"], select[name="work_slot"]');
  if (!changedInput) return;

  const rowEl = changedInput.closest(".booking-request-row");
  const bookingFormEl = changedInput.closest("form.booking-form");
  if (!rowEl || !bookingFormEl) return;

  await updateRowCapacity(rowEl, bookingFormEl.dataset.workerId);
}

async function submitBookingForm(event) {
  const bookingFormEl = event.target.closest("form.booking-form");
  if (!bookingFormEl) return;
  event.preventDefault();

  const messageEl = bookingFormEl.querySelector(".booking-submit-message");
  const workerId = bookingFormEl.dataset.workerId;
  const formData = new FormData(bookingFormEl);
  const note = String(formData.get("note") || "").trim() || null;

  const rows = [...bookingFormEl.querySelectorAll(".booking-request-row")];
  const requests = [];
  const seenWindows = new Set();

  for (const row of rows) {
    const seasonId = String(row.querySelector('select[name="season_id"]')?.value || "").trim() || null;
    const workDate = String(row.querySelector('input[name="work_date"]').value || "").trim();
    const workSlot = String(row.querySelector('select[name="work_slot"]').value || "full_day").trim() || "full_day";
    const requestedMen = Number(row.querySelector('input[name="requested_men"]').value || 0);
    const requestedWomen = Number(row.querySelector('input[name="requested_women"]').value || 0);

    if (farmerSeasons.length && !seasonId) {
      messageEl.textContent = "Choose a season for each date row.";
      messageEl.className = "message error";
      return;
    }

    if (!workDate) {
      messageEl.textContent = "Each row needs a work date.";
      messageEl.className = "message error";
      return;
    }
    if (requestedMen + requestedWomen < 1) {
      messageEl.textContent = `Each date needs at least one person (${formatDate(workDate)} has zero).`;
      messageEl.className = "message error";
      return;
    }
    const windowKey = `${workDate}|${workSlot}`;
    if (seenWindows.has(windowKey)) {
      messageEl.textContent = `Duplicate date + slot selected: ${formatDate(workDate)} (${slotLabel(workSlot)}).`;
      messageEl.className = "message error";
      return;
    }
    seenWindows.add(windowKey);

    requests.push({
      season_id: seasonId,
      work_date: workDate,
      work_slot: workSlot,
      requested_men: requestedMen,
      requested_women: requestedWomen,
    });
  }

  if (!requests.length) {
    messageEl.textContent = "Add at least one date request.";
    messageEl.className = "message error";
    return;
  }

  messageEl.textContent = "Sending booking requests...";
  messageEl.className = "message success";

  try {
    const response = await fetch(`${API_BASE}/workers/${workerId}/bookings`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ requests, note }),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./index.html";
      return;
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(extractApiErrorMessage(err, "Booking request failed"));
    }

    const created = await response.json();
    messageEl.textContent = `${created.length} booking request${created.length > 1 ? "s" : ""} sent.`;
    messageEl.className = "message success";
    await fetchFarmerSeasons().then(fetchWorkers);
  } catch (error) {
    messageEl.textContent = error.message || "Booking request failed";
    messageEl.className = "message error";
  }
}

listEl.addEventListener("click", async (event) => {
  const openWorkerButton = event.target.closest("button[data-open-worker]");
  if (openWorkerButton) {
    const workerId = openWorkerButton.dataset.openWorker;
    if (!workerId) return;

    const worker = workersById.get(workerId);
    if (worker) renderSelectedWorker(worker);
    openWorkerPanel(workerId);

    const marker = markersByWorkerId.get(workerId);
    if (marker && map) {
      const latlng = marker.getLatLng();
      map.setView(latlng, Math.max(13, map.getZoom()));
      marker.openTooltip();
    }
    return;
  }

  const clickedCard = event.target.closest("[data-worker-card-id]");
  if (clickedCard && !event.target.closest("button, input, select, textarea, a, form")) {
    if (isFarmer) {
      const workerId = clickedCard.dataset.workerCardId;
      if (workerId) openWorkerPanel(workerId);
      return;
    }

    const workerId = clickedCard.dataset.workerCardId;
    const worker = workersById.get(workerId);
    if (worker) renderSelectedWorker(worker);
    const marker = markersByWorkerId.get(workerId);
    if (marker && map) {
      const latlng = marker.getLatLng();
      map.setView(latlng, Math.max(13, map.getZoom()));
      marker.openTooltip();
      clickedCard.classList.add("worker-card-highlight");
      window.setTimeout(() => clickedCard.classList.remove("worker-card-highlight"), 1400);
    }
    return;
  }

  if (handleBookingRowsClick(event)) return;

  const button = event.target.closest("button[data-id]");
  if (!button) return;

  const workerId = button.dataset.id;
  const next = button.dataset.next === "true";

  setWorkerActionMessage(button, "", false);
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/workers/${workerId}/availability`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ available: next }),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./index.html";
      return;
    }

    if (!response.ok) throw new Error("Could not update availability");
    await fetchFarmerSeasons().then(fetchWorkers);
  } catch (error) {
    button.disabled = false;
    setWorkerActionMessage(button, error.message || "Could not update availability.", true);
  }
});

listEl.addEventListener("change", handleBookingRowCapacityChange);
listEl.addEventListener("submit", submitBookingForm);
workerDetailPanelEl?.addEventListener("click", (event) => {
  handleBookingRowsClick(event);
});
workerDetailPanelEl?.addEventListener("change", handleBookingRowCapacityChange);
workerDetailPanelEl?.addEventListener("submit", submitBookingForm);

form.addEventListener("submit", (event) => {
  event.preventDefault();
  fetchFarmerSeasons().then(fetchWorkers);
});

refreshBtn.addEventListener("click", fetchWorkers);
fetchFarmerSeasons().then(fetchWorkers);

window.addEventListener("beforeunload", () => {
  if (weatherRefreshTimerId) window.clearInterval(weatherRefreshTimerId);
});







