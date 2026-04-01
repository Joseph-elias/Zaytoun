import "../css/style.css";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, requireRole } from "./session.js";

const session = requireRole("worker", "./workers.html");

const listEl = document.getElementById("workers-list");
const refreshBtn = document.getElementById("refresh-btn");
const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (worker). Phone scope: ${session.user.phone}`;
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function money(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(2);
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
        <div class="full"><strong>Note:</strong> ${worker.overtime_note || "-"}</div>
      </div>
      <button class="btn ghost" data-id="${worker.id}" data-next="${!worker.available}">
        Mark as ${worker.available ? "Busy" : "Available"}
      </button>
    </article>
  `;
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
fetchMine();
