import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireAuth } from "./session.js";

const session = requireAuth();
if (!session) {
  // redirected
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

const isWorker = session?.user?.role === "worker";
const isFarmer = session?.user?.role === "farmer";
const capacityCache = new Map();

let map = null;
let markersLayer = null;
const markersByWorkerId = new Map();

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (${session.user.role}).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "workers.html");
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function money(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(2);
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString();
}

function dateBadges(dates) {
  return (dates || []).map((d) => `<span class="badge day">${formatDate(d)}</span>`).join(" ");
}

function selectedWorkDate() {
  const raw = form.elements.work_date?.value;
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

function bookingRequestRow(defaultDate = "") {
  return `
    <div class="worker-grid full booking-request-row">
      <label>Work Date<input name="work_date" type="date" value="${defaultDate}" required /></label>
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
  const remainingMen = worker.remaining_men_count ?? worker.men_count;
  const remainingWomen = worker.remaining_women_count ?? worker.women_count;
  const liveRemaining = filterDate && worker.remaining_men_count !== null && worker.remaining_women_count !== null;

  return `
    <form class="booking-form" data-worker-id="${worker.id}">
      <h4>Book This Team</h4>
      <div class="full"><strong>Date:</strong> ${filterDate ? formatDate(filterDate) : "Pick date(s) below"}</div>
      <div class="full"><strong>Remaining Capacity:</strong> ${remainingMen} men, ${remainingWomen} women${liveRemaining ? " (live for selected date)" : ""}</div>
      <p class="message">You can add multiple dates and choose different men/women for each date.</p>
      <div class="full" data-booking-requests>${bookingRequestRow(filterDate)}</div>
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
  const badgeClass = worker.available ? "available" : "busy";
  const badgeText = worker.available ? "Available" : "Busy";

  const menDisplay = worker.remaining_men_count ?? worker.men_count;
  const womenDisplay = worker.remaining_women_count ?? worker.women_count;
  const distanceBadge = distanceBadgeClass(worker);
  const distanceLabel = distanceText(worker);

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

function buildQuery() {
  const fd = new FormData(form);
  const params = new URLSearchParams();

  [
    "village",
    "available",
    "work_date",
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

function ensureMap() {
  if (map || !window.L || !mapEl) return;

  map = window.L.map("workers-map").setView([33.8938, 35.5018], 8);
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  markersLayer = window.L.layerGroup().addTo(map);
}

function markerPopupHtml(worker) {
  const men = worker.remaining_men_count ?? worker.men_count;
  const women = worker.remaining_women_count ?? worker.women_count;
  return `
    <div>
      <strong>${worker.name}</strong><br/>
      <small>${worker.village}</small><br/>
      <small>${worker.address || "No address"}</small><br/>
      <small>Men: ${men} | Women: ${women}</small><br/>
      <small>Rate: ${worker.rate_type}</small><br/>
      <small>Distance: ${distanceText(worker)}</small>
    </div>
  `;
}

function renderWorkersMap(workers) {
  ensureMap();
  if (!map || !markersLayer) return;

  markersLayer.clearLayers();
  markersByWorkerId.clear();

  const withCoords = workers.filter((worker) => worker.latitude !== null && worker.longitude !== null);
  if (!withCoords.length) {
    mapHint.textContent = "No worker locations available for this filter.";
    return;
  }

  const bounds = [];
  withCoords.forEach((worker) => {
    const men = worker.remaining_men_count ?? worker.men_count;
    const women = worker.remaining_women_count ?? worker.women_count;
    const marker = window.L.marker([worker.latitude, worker.longitude], {
      title: worker.name,
      icon: window.L.divIcon({
        className: "worker-pin-wrap",
        html: `<div class=\"worker-pin\">${worker.name}</div><div class=\"worker-pin-count\">M:${men} W:${women}</div>`,
      }),
    });

    marker.bindPopup(markerPopupHtml(worker), { autoClose: false, closeButton: false });
    marker.on("mouseover", () => marker.openPopup());
    marker.on("mouseout", () => marker.closePopup());
    marker.on("click", () => {
      const cardEl = document.querySelector(`[data-worker-card-id="${worker.id}"]`);
      if (!cardEl) return;
      cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
      cardEl.classList.add("worker-card-highlight");
      window.setTimeout(() => cardEl.classList.remove("worker-card-highlight"), 1400);
    });

    marker.addTo(markersLayer);
    markersByWorkerId.set(worker.id, marker);
    bounds.push([worker.latitude, worker.longitude]);
  });

  if (bounds.length === 1) {
    map.setView(bounds[0], 13);
  } else {
    map.fitBounds(bounds, { padding: [20, 20] });
  }

  mapHint.textContent = `${withCoords.length} worker location${withCoords.length > 1 ? "s" : ""} shown on map.`;
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
      window.location.href = "./login.html";
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
    renderWorkersMap(workers);
  } catch (error) {
    listEl.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

async function fetchDateCapacity(workerId, workDate) {
  const key = `${workerId}|${workDate}`;
  if (capacityCache.has(key)) return capacityCache.get(key);

  const response = await fetch(`${API_BASE}/workers?work_date=${encodeURIComponent(workDate)}`, {
    headers: authHeaders(),
  });

  if (response.status === 401 || response.status === 403) {
    clearSession();
    window.location.href = "./login.html";
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
  if (!capacityEl || !dateInput) return;

  const workDate = String(dateInput.value || "").trim();
  if (!workDate) {
    capacityEl.textContent = "";
    capacityEl.className = "message";
    return;
  }

  capacityEl.textContent = "Checking availability...";
  capacityEl.className = "message";

  try {
    const capacity = await fetchDateCapacity(workerId, workDate);
    if (!capacity) {
      capacityEl.textContent = "Not available for this date.";
      capacityEl.className = "message error";
      return;
    }

    capacityEl.textContent = `Remaining on ${formatDate(workDate)}: ${capacity.men} men, ${capacity.women} women`;
    capacityEl.className = "message success";
  } catch {
    capacityEl.textContent = "Could not check date capacity.";
    capacityEl.className = "message error";
  }
}

useMyLocationBtn?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    mapHint.textContent = "Geolocation not supported on this device.";
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      nearLatInput.value = String(position.coords.latitude);
      nearLngInput.value = String(position.coords.longitude);
      if (sortByInput) sortByInput.value = "distance";
      fetchWorkers();
    },
    () => {
      mapHint.textContent = "Could not get your location.";
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
});

if (session?.user?.latitude !== null && session?.user?.longitude !== null) {
  nearLatInput.value = String(session.user.latitude);
  nearLngInput.value = String(session.user.longitude);
}

listEl.addEventListener("click", async (event) => {
  const clickedCard = event.target.closest("[data-worker-card-id]");
  if (clickedCard && !event.target.closest("button, input, select, textarea, a, form")) {
    const workerId = clickedCard.dataset.workerCardId;
    const marker = markersByWorkerId.get(workerId);
    if (marker && map) {
      const latlng = marker.getLatLng();
      map.setView(latlng, Math.max(13, map.getZoom()));
      marker.openPopup();
      clickedCard.classList.add("worker-card-highlight");
      window.setTimeout(() => clickedCard.classList.remove("worker-card-highlight"), 1400);
    }
    return;
  }

  const addRowButton = event.target.closest("button[data-add-booking-row]");
  if (addRowButton) {
    const bookingFormEl = addRowButton.closest("form.booking-form");
    if (!bookingFormEl) return;
    const container = bookingFormEl.querySelector("[data-booking-requests]");
    if (!container) return;
    container.insertAdjacentHTML("beforeend", bookingRequestRow());
    return;
  }

  const removeRowButton = event.target.closest("button[data-remove-booking-row]");
  if (removeRowButton) {
    const bookingFormEl = removeRowButton.closest("form.booking-form");
    if (!bookingFormEl) return;
    const container = bookingFormEl.querySelector("[data-booking-requests]");
    if (!container) return;

    const rows = [...container.querySelectorAll(".booking-request-row")];
    if (rows.length <= 1) {
      const row = rows[0];
      row.querySelectorAll('input[name="work_date"], input[name="requested_men"], input[name="requested_women"]').forEach((input) => {
        if (input.name === "work_date") input.value = "";
        else input.value = "0";
      });
      const capacityEl = row.querySelector("[data-row-capacity]");
      if (capacityEl) {
        capacityEl.textContent = "";
        capacityEl.className = "message";
      }
      return;
    }

    const row = removeRowButton.closest(".booking-request-row");
    if (row) row.remove();
    return;
  }

  const button = event.target.closest("button[data-id]");
  if (!button) return;

  const workerId = button.dataset.id;
  const next = button.dataset.next === "true";

  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/workers/${workerId}/availability`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ available: next }),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }

    if (!response.ok) throw new Error("Could not update availability");
    await fetchWorkers();
  } catch (error) {
    button.disabled = false;
    alert(error.message);
  }
});

listEl.addEventListener("change", async (event) => {
  const dateInput = event.target.closest('input[name="work_date"]');
  if (!dateInput) return;

  const rowEl = dateInput.closest(".booking-request-row");
  const bookingFormEl = dateInput.closest("form.booking-form");
  if (!rowEl || !bookingFormEl) return;

  await updateRowCapacity(rowEl, bookingFormEl.dataset.workerId);
});

listEl.addEventListener("submit", async (event) => {
  const bookingFormEl = event.target.closest("form.booking-form");
  if (!bookingFormEl) return;
  event.preventDefault();

  const messageEl = bookingFormEl.querySelector(".booking-submit-message");
  const workerId = bookingFormEl.dataset.workerId;
  const note = String(new FormData(bookingFormEl).get("note") || "").trim() || null;

  const rows = [...bookingFormEl.querySelectorAll(".booking-request-row")];
  const requests = [];
  const seenDates = new Set();

  for (const row of rows) {
    const workDate = String(row.querySelector('input[name="work_date"]').value || "").trim();
    const requestedMen = Number(row.querySelector('input[name="requested_men"]').value || 0);
    const requestedWomen = Number(row.querySelector('input[name="requested_women"]').value || 0);

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
    if (seenDates.has(workDate)) {
      messageEl.textContent = `Duplicate date selected: ${formatDate(workDate)}. Use each date once per request.`;
      messageEl.className = "message error";
      return;
    }
    seenDates.add(workDate);

    requests.push({
      work_date: workDate,
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
      window.location.href = "./login.html";
      return;
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(extractApiErrorMessage(err, "Booking request failed"));
    }

    const created = await response.json();
    messageEl.textContent = `${created.length} booking request${created.length > 1 ? "s" : ""} sent.`;
    messageEl.className = "message success";
    await fetchWorkers();
  } catch (error) {
    messageEl.textContent = error.message || "Booking request failed";
    messageEl.className = "message error";
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  fetchWorkers();
});

refreshBtn.addEventListener("click", fetchWorkers);
fetchWorkers();
