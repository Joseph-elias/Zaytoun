import { getSession, login, redirectToRoleHome, registerAccount } from "./session.js";

const existing = getSession();
if (existing?.user?.role) {
  redirectToRoleHome(existing);
}

const registerForm = document.getElementById("register-user-form");
const registerMessage = document.getElementById("register-message");

function setMessage(node, text, ok = true) {
  node.textContent = text;
  node.className = `message ${ok ? "success" : "error"}`;
}

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(registerMessage, "Creating account...");

  const fd = new FormData(registerForm);
  const payload = {
    full_name: String(fd.get("full_name") || "").trim(),
    phone: String(fd.get("phone") || "").trim(),
    role: String(fd.get("role") || "worker"),
    password: String(fd.get("password") || ""),
  };

  try {
    await registerAccount(payload);
    setMessage(registerMessage, "Account created. Signing you in...");
    const session = await login(payload.phone, payload.password);
    redirectToRoleHome(session);
  } catch (error) {
    setMessage(registerMessage, error.message || "Registration failed", false);
  }
});
