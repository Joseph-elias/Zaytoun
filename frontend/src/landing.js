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

if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("Signing in...");

    const fd = new FormData(form);
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
