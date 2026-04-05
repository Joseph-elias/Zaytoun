const BUTTON_SELECTOR = "button, input[type='submit']";
const ACTION_WINDOW_MS = 5000;
const RESET_DELAY_MS = 1200;
const TOAST_DEDUPE_MS = 2200;

let activeButton = null;
let activeAt = 0;
let activeRequests = 0;

const buttonState = new WeakMap();
const recentToasts = new Map();

function canDecorate(button) {
  if (!button) return false;
  if (button.dataset.uiFeedback === "off") return false;
  return true;
}

function inferLoadingLabel(defaultLabel) {
  const text = String(defaultLabel || "").trim().toLowerCase();
  if (!text) return "Loading...";
  if (text.includes("save")) return "Saving...";
  if (text.includes("delete") || text.includes("remove")) return "Deleting...";
  if (text.includes("clear")) return "Clearing...";
  if (text.includes("add") || text.includes("create")) return "Adding...";
  if (text.includes("update") || text.includes("edit")) return "Updating...";
  if (text.includes("send")) return "Sending...";
  if (text.includes("refresh")) return "Refreshing...";
  return "Loading...";
}

function getDefaultLabel(button) {
  if (button.tagName === "INPUT") return button.value;
  return button.textContent;
}

function setLabel(button, text) {
  if (button.tagName === "INPUT") {
    button.value = text;
  } else {
    button.textContent = text;
  }
}

function rememberActiveButton(button) {
  if (!canDecorate(button)) return;
  activeButton = button;
  activeAt = Date.now();
}

function getActionButton() {
  if (!activeButton) return null;
  if (Date.now() - activeAt > ACTION_WINDOW_MS) {
    activeButton = null;
    return null;
  }
  return activeButton;
}

function startLoading(button) {
  if (!canDecorate(button)) return;

  let state = buttonState.get(button);
  if (!state) {
    state = {
      pending: 0,
      failed: false,
      resetTimer: null,
      watchdogTimer: null,
      defaultLabel: String(getDefaultLabel(button) || "").trim(),
      initialDisabled: button.hasAttribute("disabled"),
    };
    buttonState.set(button, state);
  }

  if (state.resetTimer) {
    window.clearTimeout(state.resetTimer);
    state.resetTimer = null;
  }

  state.pending += 1;

  if (state.watchdogTimer) {
    window.clearTimeout(state.watchdogTimer);
  }
  state.watchdogTimer = window.setTimeout(() => {
    forceReset(button);
  }, 15000);

  if (state.pending > 1) return;

  button.disabled = true;
  button.classList.remove("is-done", "is-error");
  button.classList.add("is-loading");
  const loadingLabel = button.dataset.loadingLabel || inferLoadingLabel(state.defaultLabel);
  setLabel(button, loadingLabel);
}

function finishLoading(button, ok) {
  const state = buttonState.get(button);
  if (!state) return;

  state.pending = Math.max(0, state.pending - 1);
  state.failed = state.failed || !ok;
  if (state.pending > 0) return;

  if (state.watchdogTimer) {
    window.clearTimeout(state.watchdogTimer);
    state.watchdogTimer = null;
  }

  button.classList.remove("is-loading");
  if (state.failed) {
    button.classList.add("is-error");
    setLabel(button, "Failed");
  } else {
    button.classList.add("is-done");
    setLabel(button, "Done ✓");
  }

  state.resetTimer = window.setTimeout(() => {
    forceReset(button);
  }, RESET_DELAY_MS);
}

function forceReset(button) {
  const state = buttonState.get(button);
  if (!state) return;

  if (state.resetTimer) {
    window.clearTimeout(state.resetTimer);
    state.resetTimer = null;
  }
  if (state.watchdogTimer) {
    window.clearTimeout(state.watchdogTimer);
    state.watchdogTimer = null;
  }

  state.pending = 0;
  state.failed = false;
  button.classList.remove("is-loading", "is-done", "is-error");
  button.disabled = Boolean(state.initialDisabled);
  setLabel(button, state.defaultLabel || "Submit");
}

function ensureTopProgress() {
  let progress = document.querySelector(".ui-top-progress");
  if (progress) return progress;
  progress = document.createElement("div");
  progress.className = "ui-top-progress";
  progress.setAttribute("aria-hidden", "true");
  document.body.appendChild(progress);
  return progress;
}

function setGlobalLoadingState(loading) {
  const progress = ensureTopProgress();
  document.body.classList.toggle("is-network-loading", loading);
  progress.classList.toggle("is-active", loading);
}

function startGlobalLoad() {
  activeRequests += 1;
  if (activeRequests === 1) setGlobalLoadingState(true);
}

function finishGlobalLoad() {
  activeRequests = Math.max(0, activeRequests - 1);
  if (activeRequests === 0) setGlobalLoadingState(false);
}

function ensureToastHost() {
  let host = document.querySelector(".ui-toast-host");
  if (host) return host;
  host = document.createElement("section");
  host.className = "ui-toast-host";
  host.setAttribute("aria-live", "polite");
  host.setAttribute("aria-atomic", "false");
  document.body.appendChild(host);
  return host;
}

function shouldToast(message, kind) {
  const text = String(message || "").trim();
  if (!text) return false;
  if (text.endsWith("...")) return false;
  if (kind !== "success" && kind !== "error") return false;
  const key = `${kind}:${text.toLowerCase()}`;
  const now = Date.now();
  const last = recentToasts.get(key) || 0;
  if (now - last < TOAST_DEDUPE_MS) return false;
  recentToasts.set(key, now);
  return true;
}

function pushToast(message, kind) {
  if (!shouldToast(message, kind)) return;
  const host = ensureToastHost();
  const toast = document.createElement("article");
  toast.className = `ui-toast ${kind}`;
  toast.textContent = message;
  host.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("in"));
  window.setTimeout(() => {
    toast.classList.remove("in");
    toast.classList.add("out");
    window.setTimeout(() => toast.remove(), 260);
  }, 2800);
}

function inspectMessageNode(node) {
  if (!(node instanceof HTMLElement)) return;
  if (!node.classList.contains("message")) return;
  const text = node.textContent?.trim();
  if (!text) return;
  const kind = node.classList.contains("error") ? "error" : node.classList.contains("success") ? "success" : "";
  if (!kind) return;
  pushToast(text, kind);
}

function setupMessageObserver() {
  if (window.__uiMessageObserverBootstrapped) return;
  window.__uiMessageObserverBootstrapped = true;
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "attributes") {
        inspectMessageNode(mutation.target);
        continue;
      }
      if (mutation.type === "characterData") {
        if (mutation.target?.parentElement) inspectMessageNode(mutation.target.parentElement);
        continue;
      }
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        inspectMessageNode(node);
        node.querySelectorAll(".message").forEach((msgNode) => inspectMessageNode(msgNode));
      });
    }
  });
  observer.observe(document.body, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ["class"],
  });
}

document.addEventListener(
  "click",
  (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest(BUTTON_SELECTOR);
    if (button) rememberActiveButton(button);
  },
  true,
);

document.addEventListener(
  "submit",
  (event) => {
    const form = event.target instanceof HTMLFormElement ? event.target : null;
    if (!form) return;
    const submitter = event.submitter || form.querySelector("button[type='submit'], input[type='submit']");
    if (submitter instanceof HTMLElement) rememberActiveButton(submitter);
  },
  true,
);

if (!window.__uiFeedbackPatchedFetch) {
  window.__uiFeedbackPatchedFetch = true;
  const originalFetch = window.fetch.bind(window);

  window.fetch = async (...args) => {
    const button = getActionButton();
    if (button) startLoading(button);
    startGlobalLoad();
    try {
      const response = await originalFetch(...args);
      if (button) finishLoading(button, response.ok);
      return response;
    } catch (error) {
      if (button) finishLoading(button, false);
      throw error;
    } finally {
      finishGlobalLoad();
    }
  };
}

if (!window.__uiRevealBootstrapped) {
  window.__uiRevealBootstrapped = true;
  const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revealTargets = Array.from(
    document.querySelectorAll(".card, .worker-card, .request-group, .insight-kpi-card, .season-year-group"),
  );

  if (!reduceMotion) {
    revealTargets.forEach((el, index) => {
      el.classList.add("reveal-prep");
      el.style.setProperty("--reveal-delay", `${Math.min(index, 18) * 38}ms`);
    });

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("reveal-in");
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.14, rootMargin: "0px 0px -8% 0px" },
    );

    revealTargets.forEach((el) => observer.observe(el));
  } else {
    revealTargets.forEach((el) => {
      el.classList.add("reveal-in");
    });
  }
}

setupMessageObserver();
