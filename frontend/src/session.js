import { API_BASE } from "./config.js";

const SESSION_KEY = "worker_radar_session";

export function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function getSession() {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

export function authHeaders(extra = {}) {
  const session = getSession();
  if (!session?.access_token) return extra;
  return {
    ...extra,
    Authorization: `Bearer ${session.access_token}`,
  };
}

export function requireAuth(redirect = "./login.html") {
  const session = getSession();
  if (!session?.access_token || !session?.user?.role) {
    window.location.href = redirect;
    return null;
  }
  return session;
}

export function requireRole(role, redirect = "./workers.html") {
  const session = requireAuth();
  if (!session) return null;

  if (session.user.role !== role) {
    window.location.href = redirect;
    return null;
  }

  return session;
}

export async function login(phone, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, password }),
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err?.detail || "Login failed");
  }

  const session = await response.json();
  saveSession(session);
  return session;
}

export async function registerAccount(payload) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err?.detail || "Registration failed");
  }

  return response.json();
}
