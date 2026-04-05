const BUTTON_SELECTOR = "button, input[type='submit']";
const ACTION_WINDOW_MS = 5000;
const RESET_DELAY_MS = 1200;

let activeButton = null;
let activeAt = 0;

const buttonState = new WeakMap();

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
      defaultLabel: String(getDefaultLabel(button) || "").trim(),
      wasDisabled: button.disabled,
    };
    buttonState.set(button, state);
  }

  if (state.resetTimer) {
    window.clearTimeout(state.resetTimer);
    state.resetTimer = null;
  }

  state.pending += 1;
  if (state.pending > 1) return;

  state.wasDisabled = button.disabled;
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

  button.classList.remove("is-loading");
  if (state.failed) {
    button.classList.add("is-error");
    setLabel(button, "Failed");
  } else {
    button.classList.add("is-done");
    setLabel(button, "Done ✓");
  }

  state.resetTimer = window.setTimeout(() => {
    button.classList.remove("is-done", "is-error");
    button.disabled = state.wasDisabled;
    setLabel(button, state.defaultLabel || "Submit");
    state.failed = false;
    state.resetTimer = null;
  }, RESET_DELAY_MS);
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
    try {
      const response = await originalFetch(...args);
      if (button) finishLoading(button, response.ok);
      return response;
    } catch (error) {
      if (button) finishLoading(button, false);
      throw error;
    }
  };
}
