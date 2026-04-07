import { API_BASE } from "./config.js";
import { authHeaders, clearSession } from "./session.js";

function extractUploadErrorMessage(err, fallbackMessage) {
  const detail = err?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === "string") return detail[0].msg;
  return fallbackMessage;
}

export async function uploadImageFile(file, { endpoint = "/uploads/image", filename = null } = {}) {
  if (!file) return null;

  const formData = new FormData();
  if (filename) formData.append("file", file, filename);
  else formData.append("file", file);

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (response.status === 401 || response.status === 403) {
    clearSession();
    window.location.href = "./login.html";
    return null;
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractUploadErrorMessage(data, "Image upload failed"));
  }

  return String(data?.url || "").trim() || null;
}
