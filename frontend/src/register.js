import { initLocationPicker } from "./location-picker.js";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireRole } from "./session.js";

const session = requireRole("worker", "./workers.html");
if (!session) {
  // redirected
}

const form = document.getElementById("worker-form");
const message = document.getElementById("form-message");
const overtimeOpen = document.getElementById("overtime_open");
const overtimePrice = document.getElementById("overtime_price");
const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");
const phoneInput = form.querySelector('input[name="phone"]');
const panelGrid = document.getElementById("availability-panel-grid");
const availabilityToday = document.getElementById("availability-today");
const availabilitySummary = document.getElementById("availability-summary");
const availabilityMonthLabel = document.getElementById("availability-month-label");
const clearDatesBtn = document.getElementById("clear-available-dates-btn");
const todayBtn = document.getElementById("availability-today-btn");
const prevMonthBtn = document.getElementById("availability-prev-month-btn");
const nextMonthBtn = document.getElementById("availability-next-month-btn");

const selectedDates = new Set();

function todayAtMidnight() {
  const t = new Date();
  t.setHours(0, 0, 0, 0);
  return t;
}

function startOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function addMonths(d, delta) {
  return new Date(d.getFullYear(), d.getMonth() + delta, 1);
}

const firstMonth = startOfMonth(todayAtMidnight());
let visibleMonth = new Date(firstMonth);

if (session) {
  if (appTabs) {
    renderAppTabs(appTabs, session.user.role, "register.html");
  }
  if (roleHint) {
    roleHint.textContent = `Logged in as ${session.user.full_name} (worker).`;
  }
  if (phoneInput) {
    phoneInput.value = session.user.phone;
    phoneInput.readOnly = true;
  }
}

const locationPicker = initLocationPicker({
  mapElementId: "worker-location-map",
  addressInputId: "worker-address",
  latitudeInputId: "worker-latitude",
  longitudeInputId: "worker-longitude",
  useMyLocationButtonId: "worker-use-my-location-btn",
});

if (session?.user?.latitude !== null && session?.user?.longitude !== null) {
  locationPicker.setValue(session.user.latitude, session.user.longitude, session.user.address || null);
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setMessage(text, ok = true) {
  message.textContent = text;
  message.className = `message ${ok ? "success" : "error"}`;
}

function toIsoDate(d) {
  return d.toISOString().slice(0, 10);
}

function humanDate(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString();
}

function renderAvailabilityPanel() {
  const today = todayAtMidnight();
  const todayIso = toIsoDate(today);
  const todayMonth = startOfMonth(today);

  availabilityToday.textContent = `Today: ${humanDate(todayIso)}`;
  availabilityMonthLabel.textContent = visibleMonth.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  prevMonthBtn.disabled = visibleMonth.getFullYear() === firstMonth.getFullYear() && visibleMonth.getMonth() === firstMonth.getMonth();
  todayBtn.disabled = visibleMonth.getFullYear() === todayMonth.getFullYear() && visibleMonth.getMonth() === todayMonth.getMonth();

  const firstDayOfVisibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
  const firstWeekday = firstDayOfVisibleMonth.getDay();
  const daysInVisibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 0).getDate();

  const cells = [];

  for (let i = 0; i < firstWeekday; i += 1) {
    cells.push('<span class="date-cell date-cell-empty" aria-hidden="true"></span>');
  }

  for (let day = 1; day <= daysInVisibleMonth; day += 1) {
    const date = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), day);
    const iso = toIsoDate(date);
    const selected = selectedDates.has(iso);
    const isToday = iso === todayIso;
    const isPast = date < today;

    cells.push(`
      <button
        type="button"
        class="date-cell${selected ? " selected" : ""}${isToday ? " today" : ""}${isPast ? " disabled" : ""}"
        data-date="${iso}"
        ${isPast ? "disabled" : ""}
      >
        <span>${day}</span>
      </button>
    `);
  }

  panelGrid.innerHTML = cells.join("");

  const count = selectedDates.size;
  availabilitySummary.textContent = count ? `${count} date${count > 1 ? "s" : ""} selected` : "No dates selected yet.";
  availabilitySummary.className = "message";
}

overtimeOpen.addEventListener("change", () => {
  overtimePrice.disabled = !overtimeOpen.checked;
  if (!overtimeOpen.checked) overtimePrice.value = "";
});

panelGrid.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-date]");
  if (!button || button.disabled) return;

  const iso = button.dataset.date;
  if (selectedDates.has(iso)) {
    selectedDates.delete(iso);
  } else {
    selectedDates.add(iso);
  }
  renderAvailabilityPanel();
});

clearDatesBtn.addEventListener("click", () => {
  selectedDates.clear();
  renderAvailabilityPanel();
});

prevMonthBtn.addEventListener("click", () => {
  const target = addMonths(visibleMonth, -1);
  if (target < firstMonth) return;
  visibleMonth = target;
  renderAvailabilityPanel();
});

nextMonthBtn.addEventListener("click", () => {
  visibleMonth = addMonths(visibleMonth, 1);
  renderAvailabilityPanel();
});

todayBtn.addEventListener("click", () => {
  visibleMonth = startOfMonth(todayAtMidnight());
  renderAvailabilityPanel();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Saving worker profile...");

  const data = new FormData(form);
  const menCount = Number(data.get("men_count"));
  const womenCount = Number(data.get("women_count"));
  const availableDates = [...selectedDates].sort();
  const location = locationPicker.getValue();

  const payload = {
    name: String(data.get("name") || "").trim(),
    phone: session?.user?.phone || String(data.get("phone") || "").trim(),
    village: String(data.get("village") || "").trim(),
    address: location.address,
    latitude: location.latitude,
    longitude: location.longitude,
    men_count: menCount,
    women_count: womenCount,
    rate_type: data.get("rate_type"),
    men_rate_value: data.get("men_rate_value") ? Number(data.get("men_rate_value")) : null,
    women_rate_value: data.get("women_rate_value") ? Number(data.get("women_rate_value")) : null,
    overtime_open: overtimeOpen.checked,
    overtime_price: data.get("overtime_price") ? Number(data.get("overtime_price")) : null,
    overtime_note: String(data.get("overtime_note") || "").trim() || null,
    available_dates: availableDates,
    available: data.get("available") === "on",
  };

  if (menCount + womenCount < 1) {
    setMessage("Add at least one worker (men or women count).", false);
    return;
  }
  if (!availableDates.length) {
    setMessage("Select at least one available date.", false);
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/workers`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        const err = await response.json().catch(() => ({}));
        if (response.status === 401) {
          clearSession();
          window.location.href = "./login.html";
          return;
        }
        throw new Error(err?.detail || "You do not have permission for this action.");
      }
      const err = await response.json();
      const detail = err?.detail?.[0]?.msg || err?.detail || "Invalid input.";
      throw new Error(typeof detail === "string" ? detail : "Invalid input.");
    }

    form.reset();
    selectedDates.clear();
    visibleMonth = new Date(firstMonth);
    renderAvailabilityPanel();
    if (phoneInput && session?.user?.phone) phoneInput.value = session.user.phone;
    overtimePrice.disabled = true;
    setMessage("Worker registered successfully.");
  } catch (error) {
    setMessage(error.message || "Failed to register worker.", false);
  }
});

renderAvailabilityPanel();


