function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read image file."));
    reader.onload = () => resolve(String(reader.result || ""));
    reader.readAsDataURL(file);
  });
}

function formatList(items) {
  if (!Array.isArray(items) || !items.length) {
    return "<li>No details provided.</li>";
  }
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function buildAssistantHtml(data) {
  return `
    <div class="olive-msg-title">${escapeHtml(data?.probable_issue || "Unknown issue")}</div>
    <div class="olive-msg-meta">
      <span class="olive-chip">confidence: ${escapeHtml(data?.confidence_band || "unknown")}</span>
      <span class="olive-chip">urgency: ${escapeHtml(data?.urgency || "unknown")}</span>
      <span class="olive-chip">lang: ${escapeHtml(data?.language || "en")}</span>
    </div>
    <div class="olive-msg-section">
      <div class="olive-msg-section-title">Why</div>
      <ul>${formatList(data?.why_it_thinks_that)}</ul>
    </div>
    <div class="olive-msg-section">
      <div class="olive-msg-section-title">What to check next</div>
      <ul>${formatList(data?.what_to_check_next)}</ul>
    </div>
    <div class="olive-msg-section">
      <div class="olive-msg-section-title">Safe actions</div>
      <ul>${formatList(data?.safe_actions)}</ul>
    </div>
    <details class="olive-msg-details">
      <summary>More details</summary>
      <div class="olive-msg-section">
        <div class="olive-msg-section-title">Alternative causes</div>
        <ul>${formatList(data?.alternative_causes)}</ul>
      </div>
      <div class="olive-msg-section">
        <div class="olive-msg-section-title">When to call agronomist</div>
        <p>${escapeHtml(data?.when_to_call_agronomist || "")}</p>
      </div>
      <div class="olive-msg-section">
        <div class="olive-msg-section-title">Follow-up questions</div>
        <ul>${formatList(data?.recommended_followup_questions)}</ul>
      </div>
      <div class="olive-trace">${escapeHtml(data?.model_trace_summary || "")}</div>
    </details>
  `;
}

async function requestJsonWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort("timeout"), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const text = await response.text();
    let parsed = {};
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch (_error) {
        throw new Error("Server returned non-JSON response.");
      }
    }
    if (!response.ok) {
      const detail = parsed?.detail || response.statusText;
      throw new Error(`HTTP ${response.status}: ${String(detail)}`);
    }
    return parsed;
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw new Error("Request timed out. Please retry.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export class OliveChatWidget {
  constructor(root, config = {}) {
    if (!root) {
      throw new Error("OliveChatWidget requires a root element.");
    }
    this.root = root;
    this.config = {
      apiBaseUrl: config.apiBaseUrl || "",
      endpointPath: config.endpointPath || "/api/v1/chat",
      language: config.language || "en",
      requestTimeoutMs: Number(config.requestTimeoutMs || 120000),
      maxImageMb: Number(config.maxImageMb || 8),
      requestHeaders: config.requestHeaders || {},
      onResponse: typeof config.onResponse === "function" ? config.onResponse : null,
      onError: typeof config.onError === "function" ? config.onError : null,
      title: config.title || "Olive Copilot",
      subtitle: config.subtitle || "Ask about olive diseases, treatment, and field actions.",
    };

    this.imageBase64 = null;
    this.imageName = "";

    this.render();
    this.bindEvents();
    this.addAssistantMessage("Hello. Describe what you see on your olive trees, and optionally attach a leaf photo.");
  }

  render() {
    this.root.innerHTML = `
      <div class="olive-chat-shell">
        <header class="olive-chat-header">
          <div>
            <h1>${escapeHtml(this.config.title)}</h1>
            <p>${escapeHtml(this.config.subtitle)}</p>
          </div>
          <label class="olive-lang-wrap">
            <span>Language</span>
            <select id="olive-language">
              <option value="en">English</option>
              <option value="fr">Francais</option>
              <option value="ar">Arabic</option>
            </select>
          </label>
        </header>

        <main id="olive-messages" class="olive-chat-messages"></main>

        <footer class="olive-chat-composer">
          <div id="olive-attach-state" class="olive-attach-state"></div>
          <div class="olive-composer-row">
            <textarea id="olive-input" placeholder="Type your message..." rows="2"></textarea>
          </div>
          <div class="olive-composer-actions">
            <label class="olive-attach-btn">
              Attach Photo
              <input id="olive-image" type="file" accept="image/*" hidden />
            </label>
            <button id="olive-remove-image" class="olive-secondary-btn" type="button">Remove Photo</button>
            <button id="olive-send" class="olive-send-btn" type="button">Send</button>
          </div>
          <div id="olive-status" class="olive-status"></div>
        </footer>
      </div>
    `;

    this.messagesEl = this.root.querySelector("#olive-messages");
    this.inputEl = this.root.querySelector("#olive-input");
    this.imageEl = this.root.querySelector("#olive-image");
    this.removeImageEl = this.root.querySelector("#olive-remove-image");
    this.sendEl = this.root.querySelector("#olive-send");
    this.statusEl = this.root.querySelector("#olive-status");
    this.langEl = this.root.querySelector("#olive-language");
    this.attachStateEl = this.root.querySelector("#olive-attach-state");
    this.langEl.value = this.config.language;
  }

  bindEvents() {
    this.sendEl.addEventListener("click", () => this.send());
    this.inputEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        this.send();
      }
    });
    this.imageEl.addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) {
        return;
      }
      const sizeMb = file.size / (1024 * 1024);
      if (sizeMb > this.config.maxImageMb) {
        this.setStatus(`Image too large (max ${this.config.maxImageMb} MB).`, true);
        this.clearImage();
        return;
      }
      try {
        this.imageBase64 = await fileToBase64(file);
        this.imageName = file.name;
        this.attachStateEl.textContent = `Attached: ${file.name}`;
        this.setStatus("Image ready.");
      } catch (error) {
        this.clearImage();
        this.setStatus(String(error?.message || error), true);
      }
    });
    this.removeImageEl.addEventListener("click", () => {
      this.clearImage();
      this.setStatus("Image removed.");
    });
  }

  clearImage() {
    this.imageBase64 = null;
    this.imageName = "";
    this.imageEl.value = "";
    this.attachStateEl.textContent = "";
  }

  setStatus(message, isError = false) {
    this.statusEl.textContent = message;
    this.statusEl.classList.toggle("error", Boolean(isError));
  }

  scrollToBottom() {
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  addUserMessage(text, imageName = "") {
    const block = document.createElement("article");
    block.className = "olive-msg olive-msg-user";
    block.innerHTML = `
      <div class="olive-msg-bubble">
        <p>${escapeHtml(text)}</p>
        ${imageName ? `<div class="olive-msg-attachment">Photo: ${escapeHtml(imageName)}</div>` : ""}
      </div>
    `;
    this.messagesEl.appendChild(block);
    this.scrollToBottom();
  }

  addAssistantMessage(html) {
    const block = document.createElement("article");
    block.className = "olive-msg olive-msg-assistant";
    block.innerHTML = `<div class="olive-msg-bubble">${html}</div>`;
    this.messagesEl.appendChild(block);
    this.scrollToBottom();
  }

  setTyping(isTyping) {
    const existing = this.root.querySelector("#olive-typing");
    if (!isTyping && existing) {
      existing.remove();
      return;
    }
    if (isTyping && !existing) {
      const block = document.createElement("article");
      block.id = "olive-typing";
      block.className = "olive-msg olive-msg-assistant";
      block.innerHTML = `<div class="olive-msg-bubble"><span class="olive-typing">Copilot is thinking...</span></div>`;
      this.messagesEl.appendChild(block);
      this.scrollToBottom();
    }
  }

  buildPayload(message) {
    return {
      message,
      observed_symptoms: [],
      language: this.langEl.value || "en",
      image_urls: [],
      image_base64: this.imageBase64 || null,
      image_path: null,
    };
  }

  async send() {
    const message = this.inputEl.value.trim();
    if (!message) {
      this.setStatus("Please type a message first.", true);
      return;
    }

    const payload = this.buildPayload(message);
    const url = `${this.config.apiBaseUrl}${this.config.endpointPath}`;

    this.inputEl.value = "";
    this.addUserMessage(message, this.imageName);
    this.sendEl.disabled = true;
    this.setTyping(true);
    this.setStatus("Sending...");

    try {
      const data = await requestJsonWithTimeout(
        url,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...this.config.requestHeaders,
          },
          body: JSON.stringify(payload),
        },
        this.config.requestTimeoutMs
      );
      this.setTyping(false);
      this.addAssistantMessage(buildAssistantHtml(data));
      this.setStatus("Done.");
      this.clearImage();
      if (this.config.onResponse) {
        this.config.onResponse(data);
      }
    } catch (error) {
      this.setTyping(false);
      const messageText = String(error?.message || error);
      this.addAssistantMessage(`<p>${escapeHtml(messageText)}</p>`);
      this.setStatus(messageText, true);
      if (this.config.onError) {
        this.config.onError(error);
      }
    } finally {
      this.sendEl.disabled = false;
    }
  }
}

export function mountOliveChatWidget(selector, config = {}) {
  const root = document.querySelector(selector);
  if (!root) {
    throw new Error(`Cannot find widget root element: ${selector}`);
  }
  return new OliveChatWidget(root, config);
}
