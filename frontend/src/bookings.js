import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireRole } from "./session.js";

const session = requireRole("farmer", "./workers.html");
if (!session) {
  // redirected
}

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");
const bookingsList = document.getElementById("bookings-list");
const filtersForm = document.getElementById("booking-filters-form");
const refreshBtn = document.getElementById("refresh-btn");

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (farmer).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "bookings.html");
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function normalizeStatus(status) {
  if (status === "pending") return "pending_worker";
  if (status === "accepted") return "confirmed";
  return status;
}

function statusLabel(status) {
  const s = normalizeStatus(status);
  if (s === "pending_worker") return "pending worker";
  if (s === "pending_farmer") return "pending farmer";
  if (s === "confirmed") return "confirmed";
  return "rejected";
}

function statusBadge(status) {
  const s = normalizeStatus(status);
  const cls = s === "confirmed" ? "available" : s === "rejected" ? "busy" : "day";
  return `<span class="badge ${cls}">${statusLabel(s)}</span>`;
}

function actionLabel(action) {
  const labels = {
    farmer_created_request: "Farmer sent request",
    worker_accepted: "Worker accepted",
    worker_proposed_changes: "Worker proposed changes",
    worker_rejected: "Worker rejected",
    farmer_confirmed: "Farmer confirmed",
    farmer_rejected: "Farmer rejected",
  };
  return labels[action] || action;
}

function timelineText(events) {
  if (!events.length) return "No timeline yet";
  const tail = events.slice(-3);
  return tail
    .map((event) => `${actionLabel(event.action)} by ${event.actor_name} (${new Date(event.created_at).toLocaleString()})${event.details ? `: ${event.details}` : ""}`)
    .join(" -> ");
}

function dayLabel(day) {
  return day.charAt(0).toUpperCase() + day.slice(1);
}

function bookingDateLabel(booking) {
  if (booking.work_date) {
    return new Date(`${booking.work_date}T00:00:00`).toLocaleDateString();
  }
  if (booking.day) return dayLabel(booking.day);
  return "-";
}

function sanitizePhone(phone) {
  return String(phone || "").replace(/[^\d]/g, "");
}

function whatsappLink(phone) {
  const clean = sanitizePhone(phone);
  if (!clean) return "#";
  return `https://wa.me/${clean}`;
}

function formatDate(value) {
  return new Date(value).toLocaleString();
}

function buildQuery() {
  const fd = new FormData(filtersForm);
  const status = String(fd.get("status") || "").trim();
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  return params.toString();
}

function messageCard(message) {
  const mine = message.sender_user_id === session.user.id;
  return `
    <article class="chat-message ${mine ? "mine" : "other"}">
      <p>${message.content}</p>
      <small>${message.sender_name} (${message.sender_role}) - ${formatDate(message.created_at)}</small>
    </article>
  `;
}

async function renderChat(bookingId, container) {
  container.innerHTML = "Loading conversation...";
  try {
    const response = await fetch(`${API_BASE}/bookings/${bookingId}/messages`, {
      headers: authHeaders(),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    if (!response.ok) throw new Error("Could not load conversation");

    const messages = await response.json();
    if (!messages.length) {
      container.innerHTML = '<p class="message">No messages yet.</p>';
      return;
    }

    container.innerHTML = messages.map(messageCard).join("");
  } catch (error) {
    container.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

async function hydrateTimelines() {
  const nodes = [...bookingsList.querySelectorAll("[data-timeline]")];
  await Promise.all(
    nodes.map(async (node) => {
      const bookingId = node.dataset.timeline;
      try {
        const response = await fetch(`${API_BASE}/bookings/${bookingId}/events`, { headers: authHeaders() });
        if (!response.ok) {
          node.textContent = "timeline unavailable";
          return;
        }
        const events = await response.json();
        node.textContent = timelineText(events);
      } catch {
        node.textContent = "timeline unavailable";
      }
    })
  );
}

async function fetchBookings() {
  bookingsList.innerHTML = "Loading bookings...";
  try {
    const query = buildQuery();
    const response = await fetch(`${API_BASE}/bookings/mine${query ? `?${query}` : ""}`, {
      headers: authHeaders(),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }

    if (!response.ok) throw new Error("Could not load bookings");

    const bookings = await response.json();
    if (!bookings.length) {
      bookingsList.innerHTML = "No booking requests found for this filter.";
      return;
    }

    bookingsList.innerHTML = bookings
      .map((booking) => {
        const s = normalizeStatus(booking.status);
        const waitingWorker = s === "pending_worker";
        const waitingFarmer = s === "pending_farmer";

        return `
      <article class="worker-card">
        <div class="list-head">
          <h3>${booking.worker_name}</h3>
          ${statusBadge(s)}
        </div>
        <div class="worker-grid">
          <div><strong>Village:</strong> ${booking.worker_village}</div>
          <div><strong>Date:</strong> ${bookingDateLabel(booking)}</div>
          <div><strong>Requested:</strong> ${booking.requested_men} men</div>
          <div><strong>Requested:</strong> ${booking.requested_women} women</div>
          <div class="full"><strong>Note:</strong> ${booking.note || "-"}</div>
          <div class="full"><strong>Flow:</strong> ${waitingWorker ? "Waiting worker response" : waitingFarmer ? "Worker answered. Please validate." : s === "confirmed" ? "Finalized" : "Rejected"}</div>
          <div class="full"><strong>Timeline:</strong> <span data-timeline="${booking.id}">Loading timeline...</span></div>
        </div>
        ${
          waitingFarmer
            ? `<div class="actions-row">
                <button class="btn" type="button" data-farmer-action="confirm" data-booking-id="${booking.id}">Validate & Confirm</button>
                <button class="btn ghost" type="button" data-farmer-action="reject" data-booking-id="${booking.id}">Reject</button>
              </div>`
            : ""
        }
        <div class="actions-row">
          <a class="btn ghost" href="${whatsappLink(booking.worker_phone)}" target="_blank" rel="noopener noreferrer">WhatsApp</a>
          <button class="btn ghost" type="button" data-chat-toggle="${booking.id}">Open Chat</button>
        </div>
        <section class="chat-panel" data-chat-panel="${booking.id}" hidden>
          <div class="chat-messages" data-chat-messages="${booking.id}"></div>
          <form class="chat-form" data-chat-form="${booking.id}">
            <textarea name="content" rows="2" required maxlength="1200" placeholder="Write a message..."></textarea>
            <button class="btn" type="submit">Send</button>
          </form>
        </section>
      </article>
    `;
      })
      .join("");

    await hydrateTimelines();
  } catch (error) {
    bookingsList.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

bookingsList.addEventListener("click", async (event) => {
  const farmerActionButton = event.target.closest("button[data-farmer-action]");
  if (farmerActionButton) {
    const bookingId = farmerActionButton.dataset.bookingId;
    const action = farmerActionButton.dataset.farmerAction;
    farmerActionButton.disabled = true;

    try {
      const response = await fetch(`${API_BASE}/bookings/${bookingId}/farmer-validation`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ action }),
      });

      if (response.status === 401 || response.status === 403) {
        clearSession();
        window.location.href = "./login.html";
        return;
      }
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err?.detail || "Could not validate booking");
      }

      await fetchBookings();
      return;
    } catch (error) {
      farmerActionButton.disabled = false;
      alert(error.message || "Could not validate booking");
      return;
    }
  }

  const toggleButton = event.target.closest("button[data-chat-toggle]");
  if (!toggleButton) return;

  const bookingId = toggleButton.dataset.chatToggle;
  const panel = bookingsList.querySelector(`[data-chat-panel="${bookingId}"]`);
  const messagesBox = bookingsList.querySelector(`[data-chat-messages="${bookingId}"]`);
  if (!panel || !messagesBox) return;

  const opening = panel.hidden;
  panel.hidden = !panel.hidden;
  toggleButton.textContent = panel.hidden ? "Open Chat" : "Hide Chat";

  if (opening) {
    await renderChat(bookingId, messagesBox);
  }
});

bookingsList.addEventListener("submit", async (event) => {
  const chatForm = event.target.closest("form[data-chat-form]");
  if (!chatForm) return;
  event.preventDefault();

  const bookingId = chatForm.dataset.chatForm;
  const messagesBox = bookingsList.querySelector(`[data-chat-messages="${bookingId}"]`);
  if (!messagesBox) return;

  const fd = new FormData(chatForm);
  const content = String(fd.get("content") || "").trim();
  if (!content) return;

  try {
    const response = await fetch(`${API_BASE}/bookings/${bookingId}/messages`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ content }),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err?.detail || "Could not send message");
    }

    chatForm.reset();
    await renderChat(bookingId, messagesBox);
  } catch (error) {
    alert(error.message || "Could not send message");
  }
});

filtersForm.addEventListener("submit", (event) => {
  event.preventDefault();
  fetchBookings();
});

refreshBtn.addEventListener("click", fetchBookings);
fetchBookings();
