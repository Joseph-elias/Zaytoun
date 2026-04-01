import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireRole } from "./session.js";

const session = requireRole("worker", "./workers.html");

const listEl = document.getElementById("workers-list");
const refreshBtn = document.getElementById("refresh-btn");
const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");

const bookingRequestsList = document.getElementById("booking-requests-list");
const refreshRequestsBtn = document.getElementById("refresh-requests-btn");
const upcomingScheduleList = document.getElementById("upcoming-schedule-list");
const refreshScheduleBtn = document.getElementById("refresh-schedule-btn");

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (worker). Phone scope: ${session.user.phone}`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "my-profiles.html");
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

function money(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(2);
}

function sanitizePhone(phone) {
  return String(phone || "").replace(/[^\d]/g, "");
}

function whatsappLink(phone) {
  const clean = sanitizePhone(phone);
  if (!clean) return "#";
  return `https://wa.me/${clean}`;
}

function formatDateTime(value) {
  return new Date(value).toLocaleString();
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString();
}

function bookingDateLabel(booking) {
  if (booking.work_date) {
    return formatDate(booking.work_date);
  }
  if (booking.day) return booking.day;
  return "-";
}

function messageCard(message) {
  const mine = message.sender_user_id === session.user.id;
  return `
    <article class="chat-message ${mine ? "mine" : "other"}">
      <p>${message.content}</p>
      <small>${message.sender_name} (${message.sender_role}) - ${formatDateTime(message.created_at)}</small>
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
  const nodes = [...bookingRequestsList.querySelectorAll("[data-timeline]")];
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

function card(worker) {
  const badgeClass = worker.available ? "available" : "busy";
  const badgeText = worker.available ? "Available" : "Busy";
  const dates = (worker.available_dates || []).map((d) => formatDate(d)).join(", ");
  return `
    <article class="worker-card">
      <div class="list-head">
        <h3>${worker.name}</h3>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="worker-grid">
        <div><strong>Village:</strong> ${worker.village}</div>
        <div><strong>Address:</strong> ${worker.address || "-"}</div>
        <div><strong>Phone:</strong> ${worker.phone}</div>
        <div><strong>Men:</strong> ${worker.men_count} | <strong>Rate:</strong> ${money(worker.men_rate_value)}</div>
        <div><strong>Women:</strong> ${worker.women_count} | <strong>Rate:</strong> ${money(worker.women_rate_value)}</div>
        <div><strong>Rate Type:</strong> ${worker.rate_type}</div>
        <div><strong>Overtime:</strong> ${worker.overtime_open ? "Yes" : "No"}</div>
        <div class="full"><strong>Available Dates:</strong> ${dates || "-"}</div>
        <div class="full"><strong>Note:</strong> ${worker.overtime_note || "-"}</div>
      </div>
      <button class="btn ghost" data-id="${worker.id}" data-next="${!worker.available}">
        Mark as ${worker.available ? "Busy" : "Available"}
      </button>
    </article>
  `;
}

function renderUpcomingSchedule(requests) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const upcoming = requests
    .filter((request) => normalizeStatus(request.status) === "confirmed")
    .filter((request) => {
      if (!request.work_date) return false;
      const d = new Date(`${request.work_date}T00:00:00`);
      return d >= today;
    })
    .sort((a, b) => String(a.work_date).localeCompare(String(b.work_date)));

  if (!upcoming.length) {
    upcomingScheduleList.innerHTML = "No upcoming confirmed shifts.";
    return;
  }

  upcomingScheduleList.innerHTML = upcoming
    .map(
      (request) => `
        <article class="worker-card">
          <div class="list-head">
            <h3>${bookingDateLabel(request)}</h3>
            ${statusBadge(request.status)}
          </div>
          <div class="worker-grid">
            <div><strong>Farmer:</strong> ${request.farmer_name}</div>
            <div><strong>Team:</strong> ${request.worker_name}</div>
            <div><strong>Assigned:</strong> ${request.requested_men} men</div>
            <div><strong>Assigned:</strong> ${request.requested_women} women</div>
            <div class="full"><strong>Note:</strong> ${request.note || "-"}</div>
          </div>
        </article>
      `
    )
    .join("");
}

async function fetchMine() {
  listEl.innerHTML = "Loading your profiles...";
  try {
    const response = await fetch(`${API_BASE}/workers`, { headers: authHeaders() });
    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    if (!response.ok) throw new Error("Could not load profiles");

    const workers = await response.json();
    if (!workers.length) {
      listEl.innerHTML = "You have no profiles yet. Create one from Register Worker.";
      return;
    }

    listEl.innerHTML = workers.map(card).join("");
  } catch (error) {
    listEl.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

async function fetchRequests() {
  bookingRequestsList.innerHTML = "Loading booking requests...";
  try {
    const response = await fetch(`${API_BASE}/bookings/received`, { headers: authHeaders() });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    if (!response.ok) throw new Error("Could not load booking requests");

    const requests = await response.json();
    renderUpcomingSchedule(requests);

    if (!requests.length) {
      bookingRequestsList.innerHTML = "No booking requests yet.";
      return;
    }

    bookingRequestsList.innerHTML = requests
      .map((request) => {
        const s = normalizeStatus(request.status);
        const waitingWorker = s === "pending_worker";
        const waitingFarmer = s === "pending_farmer";

        return `
      <article class="worker-card">
        <div class="list-head">
          <h3>${request.farmer_name}</h3>
          ${statusBadge(s)}
        </div>
        <div class="worker-grid">
          <div><strong>Team:</strong> ${request.worker_name}</div>
          <div><strong>Date:</strong> ${bookingDateLabel(request)}</div>
          <div><strong>Requested:</strong> ${request.requested_men} men</div>
          <div><strong>Requested:</strong> ${request.requested_women} women</div>
          <div class="full"><strong>Note:</strong> ${request.note || "-"}</div>
          <div class="full"><strong>Flow:</strong> ${waitingWorker ? "Your turn: accept, reject, or propose changes" : waitingFarmer ? "Waiting farmer final validation" : s === "confirmed" ? "Finalized" : "Rejected"}</div>
          <div class="full"><strong>Timeline:</strong> <span data-timeline="${request.id}">Loading timeline...</span></div>
        </div>
        ${
          waitingWorker
            ? `<form class="booking-form" data-worker-response-form="${request.id}">
                <h4>Worker Response</h4>
                <label>Men<input name="requested_men" type="number" min="0" value="${request.requested_men}" required /></label>
                <label>Women<input name="requested_women" type="number" min="0" value="${request.requested_women}" required /></label>
                <label class="full">Note<textarea name="note" rows="2" placeholder="Optional note">${request.note || ""}</textarea></label>
                <div class="actions-row">
                  <button class="btn" type="button" data-worker-action="accept" data-booking-id="${request.id}">Accept As Is</button>
                  <button class="btn ghost" type="button" data-worker-action="propose" data-booking-id="${request.id}">Send Proposal</button>
                  <button class="btn ghost" type="button" data-worker-action="reject" data-booking-id="${request.id}">Reject</button>
                </div>
                <p class="message"></p>
              </form>`
            : ""
        }
        <div class="actions-row">
          <a class="btn ghost" href="${whatsappLink(request.farmer_phone)}" target="_blank" rel="noopener noreferrer">WhatsApp</a>
          <button class="btn ghost" type="button" data-chat-toggle="${request.id}">Open Chat</button>
        </div>
        <section class="chat-panel" data-chat-panel="${request.id}" hidden>
          <div class="chat-messages" data-chat-messages="${request.id}"></div>
          <form class="chat-form" data-chat-form="${request.id}">
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
    bookingRequestsList.innerHTML = `<p class="message error">${error.message}</p>`;
    upcomingScheduleList.innerHTML = `<p class="message error">${error.message}</p>`;
  }
}

bookingRequestsList.addEventListener("click", async (event) => {
  const actionButton = event.target.closest("button[data-worker-action]");
  if (actionButton) {
    const bookingId = actionButton.dataset.bookingId;
    const action = actionButton.dataset.workerAction;
    const form = bookingRequestsList.querySelector(`form[data-worker-response-form="${bookingId}"]`);
    if (!form) return;

    const message = form.querySelector(".message");
    const fd = new FormData(form);
    const requestedMen = Number(fd.get("requested_men") || 0);
    const requestedWomen = Number(fd.get("requested_women") || 0);
    const note = String(fd.get("note") || "").trim() || null;

    if (action === "propose" && requestedMen + requestedWomen < 1) {
      message.textContent = "Proposed team must include at least 1 person.";
      message.className = "message error";
      return;
    }

    actionButton.disabled = true;
    message.textContent = "Sending response...";
    message.className = "message success";

    try {
      const payload = { action };
      if (action === "propose") {
        payload.requested_men = requestedMen;
        payload.requested_women = requestedWomen;
        payload.note = note;
      }

      const response = await fetch(`${API_BASE}/bookings/${bookingId}/worker-response`, {
        method: "PATCH",
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
        throw new Error(err?.detail || "Could not send worker response");
      }

      await fetchRequests();
      return;
    } catch (error) {
      actionButton.disabled = false;
      message.textContent = error.message || "Could not send worker response";
      message.className = "message error";
      return;
    }
  }

  const toggleButton = event.target.closest("button[data-chat-toggle]");
  if (!toggleButton) return;

  const bookingId = toggleButton.dataset.chatToggle;
  const panel = bookingRequestsList.querySelector(`[data-chat-panel="${bookingId}"]`);
  const messagesBox = bookingRequestsList.querySelector(`[data-chat-messages="${bookingId}"]`);
  if (!panel || !messagesBox) return;

  const opening = panel.hidden;
  panel.hidden = !panel.hidden;
  toggleButton.textContent = panel.hidden ? "Open Chat" : "Hide Chat";
  if (opening) {
    await renderChat(bookingId, messagesBox);
  }
});

bookingRequestsList.addEventListener("submit", async (event) => {
  const chatForm = event.target.closest("form[data-chat-form]");
  if (!chatForm) return;
  event.preventDefault();

  const bookingId = chatForm.dataset.chatForm;
  const messagesBox = bookingRequestsList.querySelector(`[data-chat-messages="${bookingId}"]`);
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

listEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-id]");
  if (!button) return;

  button.disabled = true;
  const workerId = button.dataset.id;
  const next = button.dataset.next === "true";

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

    if (!response.ok) throw new Error("Could not update profile availability");
    await fetchMine();
  } catch (error) {
    button.disabled = false;
    alert(error.message);
  }
});

refreshBtn.addEventListener("click", fetchMine);
refreshRequestsBtn.addEventListener("click", fetchRequests);
refreshScheduleBtn.addEventListener("click", fetchRequests);
fetchRequests();
fetchMine();
