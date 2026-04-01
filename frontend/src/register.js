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

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setMessage(text, ok = true) {
  message.textContent = text;
  message.className = `message ${ok ? "success" : "error"}`;
}

overtimeOpen.addEventListener("change", () => {
  overtimePrice.disabled = !overtimeOpen.checked;
  if (!overtimeOpen.checked) overtimePrice.value = "";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Saving worker profile...");

  const data = new FormData(form);
  const menCount = Number(data.get("men_count"));
  const womenCount = Number(data.get("women_count"));
  const availableDays = data.getAll("available_days").map((day) => String(day));

  const payload = {
    name: String(data.get("name") || "").trim(),
    phone: session?.user?.phone || String(data.get("phone") || "").trim(),
    village: String(data.get("village") || "").trim(),
    men_count: menCount,
    women_count: womenCount,
    rate_type: data.get("rate_type"),
    men_rate_value: data.get("men_rate_value") ? Number(data.get("men_rate_value")) : null,
    women_rate_value: data.get("women_rate_value") ? Number(data.get("women_rate_value")) : null,
    overtime_open: overtimeOpen.checked,
    overtime_price: data.get("overtime_price") ? Number(data.get("overtime_price")) : null,
    overtime_note: String(data.get("overtime_note") || "").trim() || null,
    available_days: availableDays,
    available: data.get("available") === "on",
  };

  if (menCount + womenCount < 1) {
    setMessage("Add at least one worker (men or women count).", false);
    return;
  }
  if (!availableDays.length) {
    setMessage("Select at least one available day.", false);
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
    if (phoneInput && session?.user?.phone) phoneInput.value = session.user.phone;
    overtimePrice.disabled = true;
    form.querySelectorAll('input[name="available_days"]').forEach((checkbox) => {
      checkbox.checked = true;
    });
    setMessage("Worker registered successfully.");
  } catch (error) {
    setMessage(error.message || "Failed to register worker.", false);
  }
});
