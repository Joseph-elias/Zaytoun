import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import {
  authHeaders,
  clearSession,
  getSession,
  redirectToLoginWithNotice,
  renderAppTabs,
  requireAuth,
  saveSession,
} from "./session.js";

const session = requireAuth();
if (!session) {
  // redirected
}

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");

const profileForm = document.getElementById("profile-form");
const profileSaveBtn = document.getElementById("profile-save-btn");
const profileNameInput = document.getElementById("profile-full-name");
const profilePhoneInput = document.getElementById("profile-phone");
const profileEmailInput = document.getElementById("profile-email");
const profileCurrentPasswordInput = document.getElementById("profile-current-password");
const profileMessage = document.getElementById("profile-message");

const passwordForm = document.getElementById("password-form");
const passwordSaveBtn = document.getElementById("password-save-btn");
const currentPasswordInput = document.getElementById("current-password");
const newPasswordInput = document.getElementById("new-password");
const confirmPasswordInput = document.getElementById("confirm-password");
const sendResetCodeBtn = document.getElementById("send-reset-code-btn");
const openResetFormLink = document.getElementById("open-reset-form-link");
const securityMessage = document.getElementById("security-message");
const passwordMatchHint = document.getElementById("password-match-hint");
const passwordToggleButtons = [...document.querySelectorAll("[data-password-toggle]")];

const deleteForm = document.getElementById("delete-account-form");
const deleteInput = document.getElementById("delete-confirm-input");
const deleteAckCheckbox = document.getElementById("delete-ack-checkbox");
const deleteButton = document.getElementById("delete-account-btn");
const deleteReadyHint = document.getElementById("delete-ready-hint");
const message = document.getElementById("settings-message");

function extractApiErrorMessage(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    for (const item of detail) {
      const nested = extractApiErrorMessage(item);
      if (nested) return nested;
    }
    return "";
  }
  if (typeof detail === "object") {
    if (typeof detail.msg === "string" && detail.msg.trim()) return detail.msg;
    if (typeof detail.message === "string" && detail.message.trim()) return detail.message;
    if (typeof detail.detail === "string" && detail.detail.trim()) return detail.detail;
    if (detail.detail) {
      const nested = extractApiErrorMessage(detail.detail);
      if (nested) return nested;
    }
  }
  return "";
}

function apiErrorText(body, fallback) {
  const messageText = extractApiErrorMessage(body?.detail ?? body);
  return messageText || fallback;
}

function setMessage(node, text, ok = true) {
  if (!node) return;
  node.textContent = text;
  node.className = `message ${ok ? "success" : "error"}`;
}

function updateRoleHint() {
  const current = getSession();
  if (current && roleHint) {
    roleHint.textContent = `Logged in as ${current.user.full_name} (${current.user.role}).`;
  }
}

function populateProfileForm() {
  const current = getSession();
  if (!current?.user) return;
  if (profileNameInput) profileNameInput.value = current.user.full_name || "";
  if (profilePhoneInput) profilePhoneInput.value = current.user.phone || "";
  if (profileEmailInput) profileEmailInput.value = current.user.email || "";
}

function updatePasswordMatchHint() {
  if (!passwordMatchHint || !newPasswordInput || !confirmPasswordInput) return;
  const newValue = String(newPasswordInput.value || "");
  const confirmValue = String(confirmPasswordInput.value || "");
  if (!newValue && !confirmValue) {
    passwordMatchHint.textContent = "";
    passwordMatchHint.className = "field-hint";
    return;
  }
  if (!confirmValue) {
    passwordMatchHint.textContent = "Please confirm your new password.";
    passwordMatchHint.className = "field-hint";
    return;
  }
  if (newValue === confirmValue) {
    passwordMatchHint.textContent = "Passwords match.";
    passwordMatchHint.className = "field-hint success";
    return;
  }
  passwordMatchHint.textContent = "Passwords do not match yet.";
  passwordMatchHint.className = "field-hint error";
}

function updateDeleteAccountReadiness() {
  const token = String(deleteInput?.value || "").trim();
  const acknowledged = Boolean(deleteAckCheckbox?.checked);
  const ready = token === "DELETE" && acknowledged;
  if (deleteButton) deleteButton.disabled = !ready;
  if (!deleteReadyHint) return;
  if (ready) {
    deleteReadyHint.textContent = "Ready to delete account.";
    deleteReadyHint.className = "field-hint error";
    return;
  }
  if (token !== "DELETE" && !acknowledged) {
    deleteReadyHint.textContent = "Type DELETE and confirm the checkbox to enable deletion.";
    deleteReadyHint.className = "field-hint";
    return;
  }
  if (token !== "DELETE") {
    deleteReadyHint.textContent = "Type DELETE exactly.";
    deleteReadyHint.className = "field-hint";
    return;
  }
  deleteReadyHint.textContent = "Please confirm the permanent action checkbox.";
  deleteReadyHint.className = "field-hint";
}

async function refreshCurrentUser() {
  try {
    const response = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
    if (response.status === 401 || response.status === 403) {
      clearSession();
      redirectToLoginWithNotice("session_expired");
      return;
    }
    if (!response.ok) return;
    const body = await response.json();
    const current = getSession();
    saveSession({ ...current, user: body });
    updateRoleHint();
    populateProfileForm();
  } catch {
    // Keep last known session values if refresh fails.
  }
}

if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "settings.html");
}
updateRoleHint();
populateProfileForm();
refreshCurrentUser();
updatePasswordMatchHint();
updateDeleteAccountReadiness();

if (openResetFormLink) {
  const phone = String(getSession()?.user?.phone || "").trim();
  const base = "./forgot-password.html?allow_logged_in=1";
  const nextHref = phone ? `${base}&phone=${encodeURIComponent(phone)}` : base;
  openResetFormLink.setAttribute("href", nextHref);
}

newPasswordInput?.addEventListener("input", updatePasswordMatchHint);
confirmPasswordInput?.addEventListener("input", updatePasswordMatchHint);
deleteInput?.addEventListener("input", updateDeleteAccountReadiness);
deleteAckCheckbox?.addEventListener("change", updateDeleteAccountReadiness);

for (const button of passwordToggleButtons) {
  button.addEventListener("click", () => {
    const targetId = String(button.getAttribute("data-password-toggle") || "");
    const target = targetId ? document.getElementById(targetId) : null;
    if (!target) return;
    const show = target.type === "password";
    target.type = show ? "text" : "password";
    button.textContent = show ? "Hide" : "Show";
    button.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
}

logoutBtn?.addEventListener("click", () => {
  clearSession();
  redirectToLoginWithNotice("");
});

profileForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fd = new FormData(profileForm);

  const payload = {
    full_name: String(fd.get("full_name") || "").trim(),
    phone: String(fd.get("phone") || "").trim(),
    email: String(fd.get("email") || "").trim().toLowerCase() || null,
    current_password: String(fd.get("current_password") || "") || null,
  };

  if (!payload.full_name || !payload.phone) {
    setMessage(profileMessage, "Full name and phone are required.", false);
    return;
  }

  const current = getSession();
  const oldPhone = String(current?.user?.phone || "");
  const oldEmail = (current?.user?.email || "").toLowerCase();
  const phoneChanged = payload.phone !== oldPhone;
  const emailChanged = (payload.email || "") !== oldEmail;
  if ((phoneChanged || emailChanged) && !payload.current_password) {
    setMessage(profileMessage, "Current password is required to change phone or email.", false);
    return;
  }

  profileSaveBtn.disabled = true;
  setMessage(profileMessage, "Saving profile...");

  try {
    const response = await fetch(`${API_BASE}/auth/me/profile`, {
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
      throw new Error(apiErrorText(body, "Could not save profile"));
    }

    const current = getSession();
    const nextSession = { ...current, user: body };
    saveSession(nextSession);
    updateRoleHint();
    populateProfileForm();
    if (profileCurrentPasswordInput) profileCurrentPasswordInput.value = "";
    setMessage(profileMessage, "Profile updated successfully.");
  } catch (error) {
    setMessage(profileMessage, error.message || "Could not save profile", false);
  } finally {
    profileSaveBtn.disabled = false;
  }
});

passwordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fd = new FormData(passwordForm);

  const currentPassword = String(fd.get("current_password") || "");
  const newPassword = String(fd.get("new_password") || "");
  const confirmPassword = String(fd.get("confirm_password") || "");

  if (!currentPassword || !newPassword) {
    setMessage(securityMessage, "Current and new password are required.", false);
    return;
  }

  if (newPassword !== confirmPassword) {
    setMessage(securityMessage, "New password and confirmation do not match.", false);
    return;
  }

  passwordSaveBtn.disabled = true;
  setMessage(securityMessage, "Changing password...");

  try {
    const response = await fetch(`${API_BASE}/auth/me/password`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      redirectToLoginWithNotice("session_expired");
      return;
    }

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiErrorText(body, "Could not change password"));
    }

    passwordForm.reset();
    updatePasswordMatchHint();
    setMessage(securityMessage, "Password changed. Redirecting to login...");
    clearSession();
    redirectToLoginWithNotice("session_expired");
  } catch (error) {
    setMessage(securityMessage, error.message || "Could not change password", false);
  } finally {
    passwordSaveBtn.disabled = false;
  }
});

sendResetCodeBtn?.addEventListener("click", async () => {
  const current = getSession();
  const phone = String(current?.user?.phone || "").trim();
  const email = String(current?.user?.email || "").trim();
  if (!phone) {
    setMessage(securityMessage, "No phone found on your account.", false);
    return;
  }
  if (!email) {
    setMessage(
      securityMessage,
      "No recovery email is saved yet. Add Recovery Email in Account Profile first.",
      false
    );
    return;
  }

  sendResetCodeBtn.disabled = true;
  setMessage(securityMessage, "Sending recovery code...");

  try {
    const response = await fetch(`${API_BASE}/auth/password-reset/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(apiErrorText(body, "Could not send recovery code"));
    }
    setMessage(securityMessage, body?.message || "Recovery code requested.");
  } catch (error) {
    setMessage(securityMessage, error.message || "Could not send recovery code", false);
  } finally {
    sendResetCodeBtn.disabled = false;
  }
});

deleteForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const token = String(deleteInput?.value || "").trim();
  if (token !== "DELETE") {
    setMessage(message, "Please type DELETE exactly to confirm.", false);
    updateDeleteAccountReadiness();
    return;
  }
  if (!deleteAckCheckbox?.checked) {
    setMessage(message, "Please confirm the permanent action checkbox first.", false);
    updateDeleteAccountReadiness();
    return;
  }

  deleteButton.disabled = true;
  setMessage(message, "Deleting account...");

  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      method: "DELETE",
      headers: authHeaders(),
    });

    if (response.status === 401 || response.status === 403) {
      clearSession();
      redirectToLoginWithNotice("session_expired");
      return;
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(apiErrorText(err, "Could not delete account"));
    }

    clearSession();
    window.location.href = "./signup.html";
  } catch (error) {
    updateDeleteAccountReadiness();
    setMessage(message, error.message || "Could not delete account", false);
  }
});
