import { API_BASE } from "./config.js";

const SESSION_KEY = "worker_radar_session";
const ROLE_TABS = {
  worker: [
    { href: "./register.html", label: "Register Worker", page: "register.html" },
    { href: "./my-profiles.html", label: "My Profiles", page: "my-profiles.html" },
    { href: "./workers.html", label: "Workers Directory", page: "workers.html" },
    { href: "./settings.html", label: "Settings", page: "settings.html" },
  ],
  farmer: [
    { href: "./workers.html", label: "Workers Directory", page: "workers.html" },
    { href: "./market.html", label: "Market", page: "market.html" },
    { href: "./bookings.html", label: "My Bookings", page: "bookings.html" },
    { href: "./olive-season.html", label: "Olive Season", page: "olive-season.html" },
    { href: "./agro-copilot.html", label: "Agro Copilot", page: "agro-copilot.html" },
    { href: "./settings.html", label: "Settings", page: "settings.html" },
  ],
  customer: [
    { href: "./market.html", label: "Market", page: "market.html" },
    { href: "./settings.html", label: "Settings", page: "settings.html" },
  ],
};

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

export function redirectToLoginWithNotice(notice = "session_expired") {
  const url = new URL("./index.html", window.location.href);
  if (notice) {
    url.searchParams.set("notice", notice);
  }
  window.location.href = url.toString();
}

export function isConsentReacceptRequired(session) {
  return Boolean(session?.consent_reaccept_required);
}

export function authHeaders(extra = {}) {
  const session = getSession();
  if (!session?.access_token) return extra;
  return {
    ...extra,
    Authorization: `Bearer ${session.access_token}`,
  };
}

export function requireAuth(redirect = "./index.html") {
  const session = getSession();
  if (!session?.access_token || !session?.user?.role) {
    window.location.href = redirect;
    return null;
  }
  const consentPage = String(window.location.pathname || "").endsWith("/consent.html") || String(window.location.pathname || "").endsWith("consent.html");
  if (isConsentReacceptRequired(session) && !consentPage) {
    window.location.href = "./consent.html";
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

export function roleHome(role) {
  if (role === "worker") return "./register.html";
  if (role === "customer") return "./market.html";
  return "./workers.html";
}

export function redirectToRoleHome(session) {
  if (!session?.user?.role) {
    window.location.href = "./index.html";
    return;
  }
  if (isConsentReacceptRequired(session)) {
    window.location.href = "./consent.html";
    return;
  }
  window.location.href = roleHome(session.user.role);
}

export function renderAppTabs(container, role, currentPage) {
  const session = getSession();
  const pageEl = container.closest(".page");
  if (pageEl && !pageEl.classList.contains("auth-page") && !pageEl.classList.contains("embedded-view")) {
    const existingWrapper = pageEl.querySelector(":scope > .app-content-stack");
    if (!existingWrapper) {
      const contentWrapper = document.createElement("div");
      contentWrapper.className = "app-content-stack";

      const directChildren = Array.from(pageEl.children);
      for (const child of directChildren) {
        if (child.classList.contains("hero")) continue;
        contentWrapper.appendChild(child);
      }
      pageEl.appendChild(contentWrapper);
    }
  }

  const tabs = ROLE_TABS[role] || [];
  const fullName = session?.user?.full_name || "User";
  const initials =
    fullName
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "U";
  const roleLabel = session?.user?.role ? String(session.user.role).toUpperCase() : "USER";

  container.innerHTML = `
    <section class="side-profile-banner">
      <div class="side-avatar">${initials}</div>
      <div class="side-profile-meta">
        <p class="side-profile-name">${fullName}</p>
        <p class="side-profile-role">${roleLabel}</p>
      </div>
      <a class="side-settings-link" href="./settings.html">Account & Settings</a>
    </section>
    <p class="side-nav-title">Workspace</p>
    <div class="side-nav-links">
      ${tabs
        .map((tab) => {
          const activeClass = tab.page === currentPage ? " active" : "";
          return `<a class="tab side-nav-link${activeClass}" href="${tab.href}">${tab.label}</a>`;
        })
        .join("")}
    </div>
  `;
}

export async function login(phone, password, legalAcknowledged = true) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, password, legal_acknowledged: Boolean(legalAcknowledged) }),
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


