function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function createSessionId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `olive-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
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
    return "";
  }
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderListSection(title, items) {
  const html = formatList(items);
  if (!html) return "";
  return `
    <div class="olive-msg-section">
      <div class="olive-msg-section-title">${escapeHtml(title)}</div>
      <ul>${html}</ul>
    </div>
  `;
}

function renderTextSection(title, text) {
  const value = String(text || "").trim();
  if (!value) return "";
  return `
    <div class="olive-msg-section">
      <div class="olive-msg-section-title">${escapeHtml(title)}</div>
      <p>${escapeHtml(value)}</p>
    </div>
  `;
}

function buildAssistantHtml(data) {
  const mainReply = String(data?.probable_issue || "").trim() || "I’m not sure yet. Could you share more details?";
  const trace = String(data?.model_trace_summary || "").trim();
  const source = String(data?.response_source || "fallback").trim() || "fallback";
  return `
    <p>${escapeHtml(mainReply)}</p>
    <div class="olive-msg-meta">
      <span class="olive-chip">confidence: ${escapeHtml(data?.confidence_band || "unknown")}</span>
      <span class="olive-chip">urgency: ${escapeHtml(data?.urgency || "unknown")}</span>
      <span class="olive-chip">lang: ${escapeHtml(data?.language || "en")}</span>
      <span class="olive-chip">source: ${escapeHtml(source)}</span>
    </div>
    ${(data?.fallback_reason || trace)
      ? `<details class="olive-msg-details"><summary>Trace</summary>
          ${data?.fallback_reason ? `<div class="olive-trace">fallback_reason: ${escapeHtml(data.fallback_reason)}</div>` : ""}
          ${trace ? `<div class="olive-trace">${escapeHtml(trace)}</div>` : ""}
        </details>`
      : ""}
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
      sessionsEndpointPath: config.sessionsEndpointPath || "/agro-copilot/chat/sessions",
      onResponse: typeof config.onResponse === "function" ? config.onResponse : null,
      onError: typeof config.onError === "function" ? config.onError : null,
      title: config.title || "Olive Copilot",
      subtitle: config.subtitle || "Ask about olive diseases, treatment, and field actions.",
      sessionId: config.sessionId || createSessionId(),
    };

    this.imageBase64 = null;
    this.imageName = "";
    this.sessions = [];

    this.render();
    this.bindEvents();
    this.bootstrapSessions().catch((error) => {
      this.setStatus(String(error?.message || error), true);
      this.addAssistantMessage("Hello. Describe what you see on your olive trees, and optionally attach a leaf photo.");
    });
  }

  render() {
    this.root.innerHTML = `
      <div class="olive-chat-shell">
        <aside class="olive-chat-sidebar">
          <div class="olive-sidebar-head">
            <h2>Chats</h2>
            <button id="olive-new-chat" class="olive-secondary-btn olive-new-chat-btn" type="button">+ New Chat</button>
          </div>
          <div id="olive-session-list" class="olive-session-list"></div>
        </aside>

        <div class="olive-chat-main">
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
      </div>
    `;

    this.messagesEl = this.root.querySelector("#olive-messages");
    this.inputEl = this.root.querySelector("#olive-input");
    this.imageEl = this.root.querySelector("#olive-image");
    this.removeImageEl = this.root.querySelector("#olive-remove-image");
    this.sendEl = this.root.querySelector("#olive-send");
    this.statusEl = this.root.querySelector("#olive-status");
    this.langEl = this.root.querySelector("#olive-language");
    this.sessionListEl = this.root.querySelector("#olive-session-list");
    this.newChatEl = this.root.querySelector("#olive-new-chat");
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
    this.newChatEl.addEventListener("click", () => this.createNewChat());
    this.sessionListEl.addEventListener("click", (event) => {
      const deleteTarget = event.target.closest("[data-delete-session-id]");
      if (deleteTarget) {
        const deleteId = deleteTarget.getAttribute("data-delete-session-id") || "";
        if (deleteId) {
          this.deleteSession(deleteId);
        }
        return;
      }
      const target = event.target.closest("[data-session-id]");
      const nextId = target?.getAttribute("data-session-id") || "";
      if (nextId) {
        this.switchSession(nextId);
      }
    });
  }

  async bootstrapSessions() {
    await this.loadSessionsFromServer();
    if (!this.sessions.length) {
      await this.createNewChat();
      return;
    }
    const hasCurrent = this.sessions.some((row) => row.session_id === this.config.sessionId);
    if (!hasCurrent) {
      this.config.sessionId = this.sessions[0].session_id;
    }
    this.refreshSessionList();
    await this.loadCurrentSessionHistory();
  }

  async loadSessionsFromServer() {
    const url = `${this.config.apiBaseUrl}${this.config.sessionsEndpointPath}`;
    const rows = await requestJsonWithTimeout(
      url,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...this.config.requestHeaders,
        },
      },
      this.config.requestTimeoutMs
    );
    this.sessions = Array.isArray(rows) ? rows : [];
  }

  async createNewChat() {
    const url = `${this.config.apiBaseUrl}${this.config.sessionsEndpointPath}`;
    const created = await requestJsonWithTimeout(
      url,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...this.config.requestHeaders,
        },
      },
      this.config.requestTimeoutMs
    );
    const newId = created?.session_id || createSessionId();
    await this.loadSessionsFromServer();
    this.config.sessionId = newId;
    this.refreshSessionList();
    this.messagesEl.innerHTML = "";
    this.addAssistantMessage("New chat started. Tell me what you see and we will analyze it together.");
    this.setStatus("New chat ready.");
  }

  refreshSessionList() {
    const rows = this.sessions.length
      ? this.sessions
      : [{ session_id: this.config.sessionId, preview: "Current chat", updated_at: "" }];
    const cards = rows.map((row, idx) => {
      const labelBase = row.preview ? row.preview.slice(0, 40) : `Chat ${idx + 1}`;
      const active = row.session_id === this.config.sessionId ? "is-active" : "";
      return `
        <div class="olive-session-row ${active}">
          <button type="button" class="olive-session-item ${active}" data-session-id="${escapeHtml(row.session_id)}">
            ${escapeHtml(labelBase || `Chat ${idx + 1}`)}
          </button>
          <button type="button" class="olive-session-delete" data-delete-session-id="${escapeHtml(row.session_id)}" title="Delete chat">
            x
          </button>
        </div>
      `;
    });
    this.sessionListEl.innerHTML = cards.join("");
  }

  async switchSession(sessionId) {
    this.config.sessionId = sessionId;
    this.refreshSessionList();
    await this.loadCurrentSessionHistory();
    this.setStatus("Switched chat.");
  }

  async deleteSession(sessionId) {
    const yes = window.confirm("Delete this chat session?");
    if (!yes) {
      return;
    }
    const url = `${this.config.apiBaseUrl}${this.config.sessionsEndpointPath}/${encodeURIComponent(sessionId)}`;
    await requestJsonWithTimeout(
      url,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          ...this.config.requestHeaders,
        },
      },
      this.config.requestTimeoutMs
    );

    await this.loadSessionsFromServer();
    if (!this.sessions.length) {
      await this.createNewChat();
      return;
    }
    if (this.config.sessionId === sessionId) {
      this.config.sessionId = this.sessions[0].session_id;
      await this.loadCurrentSessionHistory();
    }
    this.refreshSessionList();
    this.setStatus("Chat deleted.");
  }

  async loadCurrentSessionHistory() {
    const url = `${this.config.apiBaseUrl}${this.config.sessionsEndpointPath}/${encodeURIComponent(this.config.sessionId)}/history`;
    const payload = await requestJsonWithTimeout(
      url,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...this.config.requestHeaders,
        },
      },
      this.config.requestTimeoutMs
    );
    const turns = Array.isArray(payload?.history) ? payload.history : [];
    this.messagesEl.innerHTML = "";
    if (!turns.length) {
      this.addAssistantMessage("Hello. Describe what you see on your olive trees, and optionally attach a leaf photo.");
      return;
    }
    turns.forEach((turn) => {
      if (turn?.user) {
        this.addUserMessage(String(turn.user));
      }
      if (turn?.assistant) {
        this.addAssistantMessage(`<p>${escapeHtml(String(turn.assistant))}</p>`);
      }
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
      session_id: this.config.sessionId,
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
      if (data?.session_id) {
        this.config.sessionId = String(data.session_id);
      }
      await this.loadSessionsFromServer();
      this.refreshSessionList();
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
