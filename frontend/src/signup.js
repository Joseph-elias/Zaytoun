import "./ui-feedback.js";
import { AUTH_CONSENT_VERSION } from "./config.js";
import { initLocationPicker } from "./location-picker.js";
import { getSession, login, redirectToRoleHome, registerAccount } from "./session.js";

const existing = getSession();
if (existing?.user?.role) {
  redirectToRoleHome(existing);
}

const registerForm = document.getElementById("register-user-form");
const registerMessage = document.getElementById("register-message");
const roleInput = registerForm?.querySelector('select[name="role"]');
const queryRole = new URLSearchParams(window.location.search).get("role");
const allowedRoles = new Set(["worker", "farmer", "customer"]);

if (roleInput && queryRole && allowedRoles.has(queryRole)) {
  roleInput.value = queryRole;
}

const locationPicker = initLocationPicker({
  mapElementId: "account-location-map",
  addressInputId: "account-address",
  latitudeInputId: "account-latitude",
  longitudeInputId: "account-longitude",
  useMyLocationButtonId: "account-use-my-location-btn",
});

function setMessage(node, text, ok = true) {
  node.textContent = text;
  node.className = `message ${ok ? "success" : "error"}`;
}

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const fd = new FormData(registerForm);
  const termsAccepted = fd.get("terms_accepted") === "on";
  const dataConsentAccepted = fd.get("data_consent_accepted") === "on";
  const password = String(fd.get("password") || "");
  const confirmPassword = String(fd.get("confirm_password") || "");

  if (!termsAccepted || !dataConsentAccepted) {
    setMessage(
      registerMessage,
      "You must accept Terms & Conditions and Data Consent Policy to create your account.",
      false,
    );
    return;
  }

  if (password !== confirmPassword) {
    setMessage(registerMessage, "Password and confirm password must match.", false);
    return;
  }

  setMessage(registerMessage, "Creating account...");

  const location = locationPicker.getValue();

  const payload = {
    full_name: String(fd.get("full_name") || "").trim(),
    email: String(fd.get("email") || "").trim().toLowerCase(),
    phone: String(fd.get("phone") || "").trim(),
    role: String(fd.get("role") || "worker"),
    password,
    terms_accepted: termsAccepted,
    data_consent_accepted: dataConsentAccepted,
    consent_version: AUTH_CONSENT_VERSION,
    address: location.address,
    latitude: location.latitude,
    longitude: location.longitude,
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
