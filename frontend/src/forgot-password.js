import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import { getSession, redirectToRoleHome } from "./session.js";

const requestForm = document.getElementById("forgot-request-form");
const confirmForm = document.getElementById("forgot-confirm-form");
const messageNode = document.getElementById("forgot-message");
const params = new URLSearchParams(window.location.search);
const prefillPhone = String(params.get("phone") || "").trim();
const allowLoggedIn = params.get("allow_logged_in") === "1";

const existing = getSession();
if (!allowLoggedIn && existing?.user?.role) {
  redirectToRoleHome(existing);
}

function setMessage(text, ok = true) {
  if (!messageNode) return;
  messageNode.textContent = text;
  messageNode.className = `message ${ok ? "success" : "error"}`;
}

async function requestResetCode(phone) {
  const response = await fetch(`${API_BASE}/auth/password-reset/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.detail || "Could not request reset code.");
  }
  return payload;
}

async function confirmPasswordReset(phone, resetCode, newPassword) {
  const response = await fetch(`${API_BASE}/auth/password-reset/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      phone,
      reset_code: resetCode,
      new_password: newPassword,
    }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.detail || "Reset code is invalid or expired.");
  }
  return payload;
}

if (requestForm) {
  if (prefillPhone) {
    const requestPhone = requestForm.querySelector('input[name="phone"]');
    if (requestPhone) requestPhone.value = prefillPhone;
  }
  requestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(requestForm);
    const phone = String(fd.get("phone") || "").trim();
    if (!phone) {
      setMessage("Phone is required.", false);
      return;
    }

    setMessage("Requesting reset code...");
    try {
      const payload = await requestResetCode(phone);
      const debug = payload?.debug_reset_code
        ? ` (dev code: ${payload.debug_reset_code})`
        : "";
      setMessage(`If your account exists, a reset code is now available${debug}`);
    } catch (error) {
      setMessage(error.message || "Could not request reset code.", false);
    }
  });
}

if (confirmForm) {
  if (prefillPhone) {
    const confirmPhone = confirmForm.querySelector('input[name="phone"]');
    if (confirmPhone) confirmPhone.value = prefillPhone;
  }
  confirmForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fd = new FormData(confirmForm);
    const phone = String(fd.get("phone") || "").trim();
    const resetCode = String(fd.get("reset_code") || "").trim();
    const newPassword = String(fd.get("new_password") || "");

    if (!phone || !resetCode || !newPassword) {
      setMessage("Phone, reset code, and new password are required.", false);
      return;
    }

    setMessage("Updating password...");
    try {
      await confirmPasswordReset(phone, resetCode, newPassword);
      setMessage("Password updated successfully. You can now log in.");
      confirmForm.reset();
    } catch (error) {
      setMessage(error.message || "Could not update password.", false);
    }
  });
}
