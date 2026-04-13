import "./ui-feedback.js";
import { getSession, login, redirectToRoleHome } from "./session.js";

const existing = getSession();
if (existing?.user?.role) {
  redirectToRoleHome(existing);
}

const form = document.getElementById("landing-login-form");
const message = document.getElementById("landing-login-message");

function setMessage(text, ok = true) {
  if (!message) return;
  message.textContent = text;
  message.className = `message ${ok ? "success" : "error"}`;
}

const loginNotice = new URLSearchParams(window.location.search).get("notice");
if (loginNotice === "session_expired") {
  setMessage("Session expired, please log in again.", false);
  const clean = new URL(window.location.href);
  clean.searchParams.delete("notice");
  window.history.replaceState({}, "", clean.toString());
}

if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(form);
    const legalAccepted = fd.get("login_legal_ack") === "on";
    if (!legalAccepted) {
      setMessage("Please accept Terms & Conditions and Data Consent Policy before logging in.", false);
      return;
    }

    setMessage("Signing in...");

    const phone = String(fd.get("phone") || "").trim();
    const password = String(fd.get("password") || "");

    try {
      const session = await login(phone, password);
      setMessage("Login successful. Redirecting...");
      redirectToRoleHome(session);
    } catch (error) {
      setMessage(error.message || "Login failed", false);
    }
  });
}
