import "../css/style.css";
import { getSession, login } from "./session.js";

const existing = getSession();
if (existing?.user?.role === "worker") {
  window.location.href = "./register.html";
} else if (existing?.user?.role === "farmer") {
  window.location.href = "./workers.html";
}

const loginForm = document.getElementById("login-form");
const loginMessage = document.getElementById("login-message");

function setMessage(node, text, ok = true) {
  node.textContent = text;
  node.className = `message ${ok ? "success" : "error"}`;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(loginMessage, "Signing in...");

  const fd = new FormData(loginForm);
  const phone = String(fd.get("phone") || "").trim();
  const password = String(fd.get("password") || "");

  try {
    const session = await login(phone, password);
    setMessage(loginMessage, "Login successful. Redirecting...");

    if (session.user.role === "worker") {
      window.location.href = "./register.html";
    } else {
      window.location.href = "./workers.html";
    }
  } catch (error) {
    setMessage(loginMessage, error.message || "Login failed", false);
  }
});
