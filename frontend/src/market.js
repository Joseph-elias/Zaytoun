import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireAuth, roleHome } from "./session.js";

const session = requireAuth();
if (!session) {
  // redirected
}
if (session && !["farmer", "customer"].includes(session.user.role)) {
  window.location.href = roleHome(session.user.role);
}

const isFarmer = session?.user?.role === "farmer";
const isCustomer = session?.user?.role === "customer";

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");

const farmerCreateCard = document.getElementById("farmer-create-card");
const marketItemForm = document.getElementById("market-item-form");
const marketItemMessage = document.getElementById("market-item-message");

const marketListTitle = document.getElementById("market-list-title");
const marketFilterForm = document.getElementById("market-filter-form");
const marketItemsList = document.getElementById("market-items-list");
const refreshMarketBtn = document.getElementById("refresh-market-btn");

const ordersTitle = document.getElementById("orders-title");
const ordersCard = document.getElementById("orders-card");
const marketOrdersList = document.getElementById("market-orders-list");
const refreshOrdersBtn = document.getElementById("refresh-orders-btn");

let farmerItems = [];
let activeItems = [];
let currentOrders = [];

if (session && roleHint) {
  roleHint.textContent = `Logged in as ${session.user.full_name} (${session.user.role}).`;
}
if (session && appTabs) {
  renderAppTabs(appTabs, session.user.role, "market.html");
}

if (!isFarmer) {
  farmerCreateCard?.classList.add("is-hidden");
  marketListTitle.textContent = "Market Products";
}
if (isFarmer) {
  marketListTitle.textContent = "My Market Listings";
  ordersTitle.textContent = "Incoming Orders";
}
if (isCustomer) {
  ordersTitle.textContent = "My Orders";
}

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setFormMessage(text, ok = true) {
  if (!marketItemMessage) return;
  marketItemMessage.textContent = text;
  marketItemMessage.className = `message ${ok ? "success" : "error"}`;
}

function money(value) {
  return Number(value || 0).toFixed(2);
}

function formatDateTime(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function normalizePhoneForWhatsapp(value) {
  return String(value || "").replace(/[^\d]/g, "");
}

function extractApiErrorMessage(err, fallbackMessage) {
  const detail = err?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === "string") return detail[0].msg;
  return fallbackMessage;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, { headers: authHeaders(), ...options });
  if (response.status === 401 || response.status === 403) {
    clearSession();
    window.location.href = "./login.html";
    return null;
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, "Request failed"));
  }

  if (response.status === 204) return null;
  return response.json();
}

function farmerItemCard(item) {
  const activeBadge = item.is_active ? "available" : "busy";
  return `
    <article class="worker-card" data-my-item-id="${item.id}">
      <div class="list-head">
        <h3>${item.item_name}</h3>
        <span class="badge ${activeBadge}">${item.is_active ? "Active" : "Paused"}</span>
      </div>
      <div class="worker-grid">
        <div><strong>Price:</strong> ${money(item.price_per_unit)} / ${item.unit_label}</div>
        <div><strong>Stock:</strong> ${money(item.quantity_available)} ${item.unit_label}</div>
        <div class="full"><strong>Description:</strong> ${item.description || "-"}</div>
        <div><strong>Updated:</strong> ${formatDateTime(item.updated_at)}</div>
      </div>
      <div class="actions-row">
        <button class="btn ghost" type="button" data-edit-item="${item.id}">Edit</button>
        <button class="btn ghost" type="button" data-toggle-item="${item.id}">${item.is_active ? "Pause" : "Activate"}</button>
        <button class="btn danger" type="button" data-delete-item="${item.id}">Delete</button>
      </div>
    </article>
  `;
}

function marketCard(item) {
  return `
    <article class="worker-card" data-market-item-id="${item.id}">
      <div class="list-head">
        <h3>${item.item_name}</h3>
        <span class="badge day">${money(item.price_per_unit)} / ${item.unit_label}</span>
      </div>
      <div class="worker-grid">
        <div><strong>Farmer:</strong> ${item.farmer_name}</div>
        <div><strong>Available:</strong> ${money(item.quantity_available)} ${item.unit_label}</div>
        <div class="full"><strong>Description:</strong> ${item.description || "-"}</div>
      </div>
      ${
        isCustomer
          ? `<form class="booking-form" data-order-item-id="${item.id}">
               <h4>Place Order</h4>
               <label>Quantity (${item.unit_label})<input name="quantity_ordered" type="number" step="0.01" min="0.01" max="${item.quantity_available}" required /></label>
               <label>Note<textarea name="note" rows="2" placeholder="Optional"></textarea></label>
               <button class="btn" type="submit">Order Now</button>
               <p class="message booking-submit-message"></p>
             </form>`
          : ""
      }
    </article>
  `;
}

function statusBadgeClass(status) {
  if (status === "validated") return "available";
  if (status === "rejected") return "busy";
  return "day";
}

function orderStatusLabel(status) {
  if (status === "validated") return "Validated";
  if (status === "rejected") return "Rejected";
  return "Pending";
}

function whatsappTarget(order) {
  if (isFarmer) {
    const digits = normalizePhoneForWhatsapp(order.customer_phone);
    if (!digits) return null;
    const text = `Hello ${order.customer_name}, I am contacting you about your order ${order.id.slice(0, 8)} for ${order.item_name_snapshot}.`;
    return {
      label: "WhatsApp Customer",
      href: `https://wa.me/${digits}?text=${encodeURIComponent(text)}`,
    };
  }

  const digits = normalizePhoneForWhatsapp(order.farmer_phone);
  if (!digits) return null;
  const text = `Hello ${order.farmer_name}, I am contacting you about order ${order.id.slice(0, 8)} for ${order.item_name_snapshot}.`;
  return {
    label: "WhatsApp Farmer",
    href: `https://wa.me/${digits}?text=${encodeURIComponent(text)}`,
  };
}

function orderCard(order) {
  const badgeClass = statusBadgeClass(order.status);
  const wa = whatsappTarget(order);
  const canFarmerValidate = isFarmer && order.status === "pending";
  const contactPhoneLabel = isFarmer ? "Customer Phone" : "Farmer Phone";
  const contactPhoneValue = isFarmer ? order.customer_phone : order.farmer_phone;

  return `
    <article class="worker-card" data-order-id="${order.id}">
      <div class="list-head">
        <h3>${order.item_name_snapshot}</h3>
        <span class="badge ${badgeClass}">${orderStatusLabel(order.status)}</span>
      </div>
      <div class="worker-grid">
        <div><strong>Quantity:</strong> ${money(order.quantity_ordered)} ${order.unit_label_snapshot}</div>
        <div><strong>Total:</strong> ${money(order.total_price)}</div>
        <div><strong>Unit Price:</strong> ${money(order.unit_price_snapshot)}</div>
        <div><strong>Date:</strong> ${formatDateTime(order.created_at)}</div>
        <div><strong>Farmer:</strong> ${order.farmer_name}</div>
        <div><strong>Customer:</strong> ${order.customer_name}</div>
        <div><strong>Pickup Time:</strong> ${formatDateTime(order.pickup_at)}</div>
        <div><strong>${contactPhoneLabel}:</strong> ${contactPhoneValue || "-"}</div>
        <div class="full"><strong>Order Note:</strong> ${order.note || "-"}</div>
        <div class="full"><strong>Farmer Response:</strong> ${order.farmer_response_note || "-"}</div>
      </div>
      <div class="actions-row">
        ${wa ? `<a class="btn ghost" href="${wa.href}" target="_blank" rel="noreferrer">${wa.label}</a>` : ""}
      </div>
      ${
        canFarmerValidate
          ? `<form class="booking-form" data-validate-order-id="${order.id}">
               <h4>Validate Order</h4>
               <label>Pickup Time<input name="pickup_at" type="datetime-local" required /></label>
               <label>Response Note<textarea name="note" rows="2" placeholder="Optional"></textarea></label>
               <div class="actions-row">
                 <button class="btn" type="submit">Validate & Set Pickup</button>
                 <button class="btn ghost" type="button" data-reject-order="${order.id}">Reject Order</button>
               </div>
               <p class="message booking-submit-message"></p>
             </form>`
          : ""
      }
      <section class="chat-panel">
        <h4>Order Chat</h4>
        <div class="chat-messages" data-chat-list="${order.id}">Loading chat...</div>
        <form class="chat-form" data-chat-form="${order.id}">
          <label>Message<textarea name="content" rows="2" maxlength="1200" required placeholder="Write a message..."></textarea></label>
          <button class="btn ghost" type="submit">Send Message</button>
          <p class="message booking-submit-message"></p>
        </form>
      </section>
    </article>
  `;
}

function chatMessageCard(message) {
  const mine = message.sender_user_id === session.user.id;
  return `
    <article class="chat-message ${mine ? "mine" : "other"}">
      <small>${message.sender_name} (${message.sender_role}) - ${formatDateTime(message.created_at)}</small>
      <p>${message.content}</p>
    </article>
  `;
}

async function loadOrderMessages(orderId) {
  const messages = (await requestJson(`${API_BASE}/market/orders/${orderId}/messages`)) || [];
  const container = marketOrdersList.querySelector(`[data-chat-list="${orderId}"]`);
  if (!container) return;
  container.innerHTML = messages.length ? messages.map(chatMessageCard).join("") : '<p class="sub">No messages yet.</p>';
}

async function loadAllOrderMessages() {
  await Promise.all(currentOrders.map((order) => loadOrderMessages(order.id)));
}

async function loadMarketItems() {
  if (isFarmer) {
    farmerItems = (await requestJson(`${API_BASE}/market/items/mine`)) || [];
    marketItemsList.innerHTML = farmerItems.length ? farmerItems.map(farmerItemCard).join("") : "No listings yet. Add your first product above.";
    return;
  }

  const query = new FormData(marketFilterForm).get("q");
  const search = String(query || "").trim();
  const url = `${API_BASE}/market/items${search ? `?q=${encodeURIComponent(search)}` : ""}`;
  activeItems = (await requestJson(url)) || [];
  marketItemsList.innerHTML = activeItems.length ? activeItems.map(marketCard).join("") : "No products available right now.";
}

async function loadOrders() {
  if (isFarmer) {
    currentOrders = (await requestJson(`${API_BASE}/market/orders/incoming`)) || [];
    marketOrdersList.innerHTML = currentOrders.length ? currentOrders.map(orderCard).join("") : "No incoming orders yet.";
    await loadAllOrderMessages();
    return;
  }

  if (isCustomer) {
    currentOrders = (await requestJson(`${API_BASE}/market/orders/mine`)) || [];
    marketOrdersList.innerHTML = currentOrders.length ? currentOrders.map(orderCard).join("") : "No orders yet.";
    await loadAllOrderMessages();
    return;
  }

  ordersCard?.classList.add("is-hidden");
}

marketItemForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fd = new FormData(marketItemForm);

  const payload = {
    item_name: String(fd.get("item_name") || "").trim(),
    description: String(fd.get("description") || "").trim() || null,
    unit_label: String(fd.get("unit_label") || "").trim(),
    price_per_unit: Number(fd.get("price_per_unit") || 0),
    quantity_available: Number(fd.get("quantity_available") || 0),
    is_active: fd.get("is_active") !== null,
  };

  setFormMessage("Saving listing...", true);
  try {
    await requestJson(`${API_BASE}/market/items`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    marketItemForm.reset();
    marketItemForm.elements.is_active.checked = true;
    setFormMessage("Listing saved.", true);
    await Promise.all([loadMarketItems(), loadOrders()]);
  } catch (error) {
    setFormMessage(error.message || "Could not save listing", false);
  }
});

marketItemsList.addEventListener("click", async (event) => {
  const editBtn = event.target.closest("button[data-edit-item]");
  if (editBtn) {
    const item = farmerItems.find((row) => row.id === editBtn.dataset.editItem);
    if (!item) return;

    const qtyRaw = window.prompt("New quantity available", String(item.quantity_available));
    if (qtyRaw === null) return;
    const priceRaw = window.prompt("New unit price", String(item.price_per_unit));
    if (priceRaw === null) return;

    try {
      await requestJson(`${API_BASE}/market/items/${item.id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          quantity_available: Number(qtyRaw),
          price_per_unit: Number(priceRaw),
        }),
      });
      await loadMarketItems();
    } catch (error) {
      setFormMessage(error.message || "Could not update listing", false);
    }
    return;
  }

  const toggleBtn = event.target.closest("button[data-toggle-item]");
  if (toggleBtn) {
    const item = farmerItems.find((row) => row.id === toggleBtn.dataset.toggleItem);
    if (!item) return;

    try {
      await requestJson(`${API_BASE}/market/items/${item.id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ is_active: !item.is_active }),
      });
      await loadMarketItems();
    } catch (error) {
      setFormMessage(error.message || "Could not update listing", false);
    }
    return;
  }

  const deleteBtn = event.target.closest("button[data-delete-item]");
  if (deleteBtn) {
    const item = farmerItems.find((row) => row.id === deleteBtn.dataset.deleteItem);
    if (!item) return;
    if (!window.confirm("Delete this listing?")) return;

    try {
      await requestJson(`${API_BASE}/market/items/${item.id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      await loadMarketItems();
    } catch (error) {
      setFormMessage(error.message || "Could not delete listing", false);
    }
  }
});

marketItemsList.addEventListener("submit", async (event) => {
  const orderForm = event.target.closest("form[data-order-item-id]");
  if (!orderForm) return;
  event.preventDefault();

  const messageEl = orderForm.querySelector(".booking-submit-message");
  const payload = {
    market_item_id: orderForm.dataset.orderItemId,
    quantity_ordered: Number(orderForm.elements.quantity_ordered.value || 0),
    note: String(orderForm.elements.note.value || "").trim() || null,
  };

  messageEl.textContent = "Placing order...";
  messageEl.className = "message success";

  try {
    await requestJson(`${API_BASE}/market/orders`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    messageEl.textContent = "Order placed successfully. Waiting for farmer validation.";
    messageEl.className = "message success";
    orderForm.reset();
    await Promise.all([loadMarketItems(), loadOrders()]);
  } catch (error) {
    messageEl.textContent = error.message || "Could not place order";
    messageEl.className = "message error";
  }
});

marketOrdersList.addEventListener("submit", async (event) => {
  const validateForm = event.target.closest("form[data-validate-order-id]");
  if (validateForm) {
    event.preventDefault();
    const messageEl = validateForm.querySelector(".booking-submit-message");

    const pickupLocal = String(validateForm.elements.pickup_at.value || "").trim();
    const payload = {
      action: "validate",
      pickup_at: pickupLocal ? new Date(pickupLocal).toISOString() : null,
      note: String(validateForm.elements.note.value || "").trim() || null,
    };

    messageEl.textContent = "Validating order...";
    messageEl.className = "message success";

    try {
      await requestJson(`${API_BASE}/market/orders/${validateForm.dataset.validateOrderId}/farmer-validation`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      messageEl.textContent = "Order validated with pickup time.";
      messageEl.className = "message success";
      await loadOrders();
    } catch (error) {
      messageEl.textContent = error.message || "Could not validate order";
      messageEl.className = "message error";
    }
    return;
  }

  const chatForm = event.target.closest("form[data-chat-form]");
  if (!chatForm) return;
  event.preventDefault();

  const messageEl = chatForm.querySelector(".booking-submit-message");
  const content = String(chatForm.elements.content.value || "").trim();
  if (!content) return;

  messageEl.textContent = "Sending message...";
  messageEl.className = "message success";

  try {
    await requestJson(`${API_BASE}/market/orders/${chatForm.dataset.chatForm}/messages`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ content }),
    });
    chatForm.reset();
    messageEl.textContent = "Message sent.";
    messageEl.className = "message success";
    await loadOrderMessages(chatForm.dataset.chatForm);
  } catch (error) {
    messageEl.textContent = error.message || "Could not send message";
    messageEl.className = "message error";
  }
});

marketOrdersList.addEventListener("click", async (event) => {
  const rejectBtn = event.target.closest("button[data-reject-order]");
  if (!rejectBtn) return;

  const note = window.prompt("Optional rejection note", "") ?? "";
  try {
    await requestJson(`${API_BASE}/market/orders/${rejectBtn.dataset.rejectOrder}/farmer-validation`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ action: "reject", note: note.trim() || null }),
    });
    await loadOrders();
  } catch (error) {
    window.alert(error.message || "Could not reject order");
  }
});

marketFilterForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  loadMarketItems();
});

refreshMarketBtn?.addEventListener("click", loadMarketItems);
refreshOrdersBtn?.addEventListener("click", loadOrders);

Promise.all([loadMarketItems(), loadOrders()]).catch((error) => {
  marketItemsList.innerHTML = `<p class="message error">${error.message || "Could not load market"}</p>`;
});

