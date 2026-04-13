import "./ui-feedback.js";
import { API_BASE, AUTH_CONSENT_VERSION } from "./config.js";
import { authHeaders, clearSession, getSession, redirectToLoginWithNotice, redirectToRoleHome, saveSession } from "./session.js";

const session = getSession();
if (!session?.access_token) {
  redirectToLoginWithNotice("");
}

const form = document.getElementById("consent-reaccept-form");
const message = document.getElementById("consent-message");
const logoutLink = document.getElementById("consent-logout-link");

function setMessage(text, ok = true) {
  if (!message) return;
  message.textContent = text;
  message.className = `message ${ok ? "success" : "error"}`;
}

logoutLink?.addEventListener("click", (event) => {
  event.preventDefault();
  clearSession();
  redirectToLoginWithNotice("");
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fd = new FormData(form);

  const payload = {
    legal_acknowledged: fd.get("legal_acknowledged") === "on",
    terms_accepted: fd.get("terms_accepted") === "on",
    data_consent_accepted: fd.get("data_consent_accepted") === "on",
    consent_version: String(session?.required_consent_version || AUTH_CONSENT_VERSION),
  };

  setMessage("Updating consent...");
  try {
    const response = await fetch(`${API_BASE}/auth/consent`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      redirectToLoginWithNotice("session_expired");
      return;
    }

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body?.detail || "Could not update consent");
    }

    const nextSession = {
      ...session,
      user: body,
      consent_reaccept_required: false,
      required_consent_version: null,
    };
    saveSession(nextSession);
    setMessage("Consent updated. Redirecting...");
    redirectToRoleHome(nextSession);
  } catch (error) {
    setMessage(error.message || "Could not update consent", false);
  }
});
