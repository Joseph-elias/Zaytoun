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

const isWorker = session?.user?.role === "worker";
const isFarmer = session?.user?.role === "farmer";

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

function dayLabel(day) {
  return day.charAt(0).toUpperCase() + day.slice(1);
}

function daysBadges(days) {
  return days.map((day) => `<span class="badge day">${dayLabel(day)}</span>`).join(" ");
}

function bookingForm(worker) {
  if (!isFarmer) return "";

  const dayChecks = worker.available_days
    .map(
      (day, index) =>
        `<label><input type="checkbox" name="days" value="${day}" ${index === 0 ? "checked" : ""} /> ${dayLabel(day)}</label>`
    )
    .join("");

  return `
    <form class="booking-form" data-worker-id="${worker.id}" data-days='${JSON.stringify(worker.available_days)}'>
      <h4>Book This Team</h4>
      <label class="inline-check">
        <input type="checkbox" name="all_days" /> Book all available days
      </label>
      <fieldset class="full day-selector">
        <legend>Pick Days</legend>
        ${dayChecks}
      </fieldset>
      <label>Men Needed<input name="requested_men" type="number" min="0" value="0" required /></label>
      <label>Women Needed<input name="requested_women" type="number" min="0" value="0" required /></label>
      <label class="full">Note<textarea name="note" rows="2" placeholder="Optional note"></textarea></label>
      <button class="btn" type="submit">Send Booking Request</button>
      <p class="message"></p>
    </form>
  `;
}

function card(worker) {
  const badgeClass = worker.available ? "available" : "busy";
  const badgeText = worker.available ? "Available" : "Busy";

  return `
    <article class="worker-card">
      <div class="list-head">
        <h3>${worker.name}</h3>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="worker-grid">
        <div><strong>Village:</strong> ${worker.village}</div>
        <div><strong>Phone:</strong> ${worker.phone}</div>
        <div><strong>Men:</strong> ${worker.men_count} | <strong>Rate:</strong> ${money(worker.men_rate_value)}</div>
        <div><strong>Women:</strong> ${worker.women_count} | <strong>Rate:</strong> ${money(worker.women_rate_value)}</div>
        <div><strong>Rate Type:</strong> ${worker.rate_type}</div>
        <div><strong>Overtime:</strong> ${worker.overtime_open ? "Yes" : "No"}</div>
        <div class="full"><strong>Available Days:</strong> ${daysBadges(worker.available_days)}</div>
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

  ["village", "available", "available_day", "rate_type", "min_men_rate", "max_men_rate", "min_women_rate", "max_women_rate"].forEach(
    (key) => {
      const raw = fd.get(key);
      if (raw !== null && String(raw).trim() !== "") params.set(key, String(raw).trim());
    }
  );

  return params.toString();
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
      return;
    }

    listEl.innerHTML = workers.map(card).join("");
  } catch (error) {
    listEl.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

listEl.addEventListener("change", (event) => {
  const allDaysToggle = event.target.closest('input[name="all_days"]');
  if (allDaysToggle) {
    const bookingFormEl = allDaysToggle.closest("form.booking-form");
    if (!bookingFormEl) return;
    const dayInputs = bookingFormEl.querySelectorAll('input[name="days"]');
    dayInputs.forEach((input) => {
      input.checked = allDaysToggle.checked;
      input.disabled = allDaysToggle.checked;
    });
    return;
  }

  const dayInput = event.target.closest('input[name="days"]');
  if (!dayInput) return;
  const bookingFormEl = dayInput.closest("form.booking-form");
  if (!bookingFormEl) return;
  const dayInputs = [...bookingFormEl.querySelectorAll('input[name="days"]')];
  const allChecked = dayInputs.length > 0 && dayInputs.every((input) => input.checked);
  const allDaysCheckbox = bookingFormEl.querySelector('input[name="all_days"]');
  if (allDaysCheckbox) allDaysCheckbox.checked = allChecked;
});

listEl.addEventListener("submit", async (event) => {
  const bookingFormEl = event.target.closest("form.booking-form");
  if (!bookingFormEl) return;
  event.preventDefault();

  const messageEl = bookingFormEl.querySelector(".message");
  const workerId = bookingFormEl.dataset.workerId;
  const availableDays = JSON.parse(bookingFormEl.dataset.days || "[]");
  const fd = new FormData(bookingFormEl);

  const allDays = fd.get("all_days") === "on";
  const requestedMen = Number(fd.get("requested_men") || 0);
  const requestedWomen = Number(fd.get("requested_women") || 0);
  const selectedDays = fd.getAll("days").map((day) => String(day));
  const days = allDays ? availableDays : selectedDays;

  if (requestedMen + requestedWomen < 1) {
    messageEl.textContent = "Pick at least one person (men/women).";
    messageEl.className = "message error";
    return;
  }
  if (!days.length) {
    messageEl.textContent = "Pick at least one day.";
    messageEl.className = "message error";
    return;
  }

  messageEl.textContent = "Sending booking request...";
  messageEl.className = "message success";

  try {
    const response = await fetch(`${API_BASE}/workers/${workerId}/bookings`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        days,
        requested_men: requestedMen,
        requested_women: requestedWomen,
        note: String(fd.get("note") || "").trim() || null,
      }),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err?.detail || "Booking request failed");
    }

    messageEl.textContent = "Booking request sent.";
    messageEl.className = "message success";
    bookingFormEl.reset();
    bookingFormEl.querySelectorAll('input[name="days"]').forEach((input, index) => {
      input.disabled = false;
      input.checked = index === 0;
    });
  } catch (error) {
    messageEl.textContent = error.message || "Booking request failed";
    messageEl.className = "message error";
  }
});

listEl.addEventListener("click", async (event) => {
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

form.addEventListener("submit", (event) => {
  event.preventDefault();
  fetchWorkers();
});

refreshBtn.addEventListener("click", fetchWorkers);
fetchWorkers();
