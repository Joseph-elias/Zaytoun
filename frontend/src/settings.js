import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireAuth } from "./session.js";

const session = requireAuth();
if (!session) {
  // redirected
}

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");
const deleteForm = document.getElementById("delete-account-form");
const deleteInput = document.getElementById("delete-confirm-input");
const deleteButton = document.getElementById("delete-account-btn");
const message = document.getElementById("settings-message");

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (${session.user.role}).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "settings.html");
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setMessage(text, ok = true) {
  message.textContent = text;
  message.className = `message ${ok ? "success" : "error"}`;
}

deleteForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const token = String(deleteInput.value || "").trim();
  if (token !== "DELETE") {
    setMessage("Please type DELETE exactly to confirm.", false);
    return;
  }

  const sure = window.confirm("Are you absolutely sure? This cannot be undone.");
  if (!sure) return;

  deleteButton.disabled = true;
  setMessage("Deleting account...", true);

  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      method: "DELETE",
      headers: authHeaders(),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err?.detail || "Could not delete account");
    }

    clearSession();
    window.location.href = "./signup.html";
  } catch (error) {
    deleteButton.disabled = false;
    setMessage(error.message || "Could not delete account", false);
  }
});

