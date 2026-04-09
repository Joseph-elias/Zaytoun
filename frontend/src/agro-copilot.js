import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireRole } from "./session.js";
import { mountOliveChatWidget } from "./agro-chat-widget.js";

const session = requireRole("farmer", "./workers.html");
const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");
const refreshHealthBtn = document.getElementById("refresh-health-btn");
const healthMessage = document.getElementById("agro-health-message");

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (farmer).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "agro-copilot.html");
}

logoutBtn?.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setMessage(text, ok = true) {
  if (!healthMessage) return;
  healthMessage.textContent = text;
  healthMessage.className = `message ${ok ? "success" : "error"}`;
}

async function checkAgroHealth() {
  try {
    const response = await fetch(`${API_BASE}/agro-copilot/health`, {
      headers: authHeaders(),
    });
    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.href = "./login.html";
      return;
    }
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data?.detail || `Health check failed (${response.status})`);
    }
    setMessage("Agro Copilot service is online.");
  } catch (error) {
    setMessage(String(error?.message || error), false);
  }
}

refreshHealthBtn?.addEventListener("click", () => {
  checkAgroHealth();
});

if (session) {
  mountOliveChatWidget("#agro-chat-root", {
    apiBaseUrl: API_BASE,
    endpointPath: "/agro-copilot/chat",
    language: "fr",
    requestHeaders: authHeaders(),
    title: "Agro Copilot",
    subtitle: "Ask about olive tree symptoms. Add a photo for better diagnosis.",
  });
  checkAgroHealth();
}
