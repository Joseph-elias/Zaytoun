import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireAuth, roleHome } from "./session.js";

const session = requireAuth();
if (!session) {}
if (session && !["farmer", "customer"].includes(session.user.role)) {
  window.location.href = roleHome(session.user.role);
}

const isFarmer = session?.user?.role === "farmer";
const isCustomer = session?.user?.role === "customer";

const roleHint = document.getElementById("role-hint");
const logoutBtn = document.getElementById("logout-btn");
const appTabs = document.getElementById("app-tabs");

const farmerCreateCard = document.getElementById("farmer-create-card");
const storeProfileCard = document.getElementById("store-profile-card");
const storeProfileToggleBtn = document.getElementById("store-profile-toggle-btn");
const storeProfileContent = document.getElementById("store-profile-content");
const storeProfileForm = document.getElementById("store-profile-form");
const storeProfileMessage = document.getElementById("store-profile-message");
const listingToggleBtn = document.getElementById("listing-toggle-btn");
const listingContent = document.getElementById("listing-content");
const marketItemForm = document.getElementById("market-item-form");
const marketItemMessage = document.getElementById("market-item-message");
const quantityLabel = document.getElementById("quantity-label");

const marketListTitle = document.getElementById("market-list-title");
const marketFilterForm = document.getElementById("market-filter-form");
const marketItemsList = document.getElementById("market-items-list");
const refreshMarketBtn = document.getElementById("refresh-market-btn");

const customerStoresView = document.getElementById("customer-stores-view");
const customerStoreDetail = document.getElementById("customer-store-detail");
const storeBackBtn = document.getElementById("store-back-btn");
const storeHeader = document.getElementById("store-header");
const storeItemsList = document.getElementById("store-items-list");

const cartLines = document.getElementById("cart-lines");
const cartTotal = document.getElementById("cart-total");
const cartCheckoutForm = document.getElementById("cart-checkout-form");
const cartMessage = document.getElementById("cart-message");

const ordersTitle = document.getElementById("orders-title");
const ordersCard = document.getElementById("orders-card");
const marketOrdersList = document.getElementById("market-orders-list");
const refreshOrdersBtn = document.getElementById("refresh-orders-btn");

let farmerItems = [];
let activeItems = [];
let currentOrders = [];
let editingItemId = null;
let selectedStoreId = null;
let currentStoreProfile = null;
const cart = new Map();

if (session && roleHint) roleHint.textContent = `Logged in as ${session.user.full_name} (${session.user.role}).`;
if (session && appTabs) renderAppTabs(appTabs, session.user.role, "market.html");

if (!isFarmer) farmerCreateCard?.classList.add("is-hidden");
if (!isFarmer) storeProfileCard?.classList.add("is-hidden");
if (isFarmer) {
  marketListTitle.textContent = "My Store Listings";
  ordersTitle.textContent = "Incoming Orders";
}
if (isCustomer) {
  marketListTitle.textContent = "Stores";
  ordersTitle.textContent = "My Orders";
}

installFoldToggle(storeProfileToggleBtn, storeProfileContent);
installFoldToggle(listingToggleBtn, listingContent);

logoutBtn.addEventListener("click", () => {
  clearSession();
  window.location.href = "./login.html";
});

function setFormMessage(text, ok = true) {
  if (!marketItemMessage) return;
  marketItemMessage.textContent = text;
  marketItemMessage.className = `message ${ok ? "success" : "error"}`;
}

function setStoreProfileMessage(text, ok = true) {
  if (!storeProfileMessage) return;
  storeProfileMessage.textContent = text;
  storeProfileMessage.className = `message ${ok ? "success" : "error"}`;
}

function setCartMessage(text, ok = true) {
  if (!cartMessage) return;
  cartMessage.textContent = text;
  cartMessage.className = `message ${ok ? "success" : "error"}`;
}

function setFoldState(button, content, expanded) {
  if (!button || !content) return;
  button.setAttribute("aria-expanded", String(expanded));
  button.textContent = expanded ? "Hide" : "Show";
  content.classList.toggle("is-hidden", !expanded);
}

function installFoldToggle(button, content) {
  if (!button || !content) return;
  button.addEventListener("click", () => {
    const expanded = button.getAttribute("aria-expanded") === "true";
    setFoldState(button, content, !expanded);
  });
  setFoldState(button, content, true);
}

function money(value) {
  return Number(value || 0).toFixed(2);
}

function formatDateTime(value) {
  return value ? new Date(value).toLocaleString() : "-";
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function safeUrl(url) {
  const raw = String(url || "").trim();
  return /^https?:\/\//i.test(raw) ? raw : null;
}

function initials(value) {
  return (
    String(value || "")
      .trim()
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "WR"
  );
}

function quantityText(value, unitLabel) {
  return value === null || value === undefined ? "Unlimited" : `${money(value)} ${unitLabel}`;
}

function starsText(value) {
  const rating = Number(value || 0);
  if (!rating || rating < 1) return "No ratings yet";
  return "★".repeat(rating) + "☆".repeat(Math.max(0, 5 - rating));
}

function ratingLabel(avg, count) {
  const safeCount = Number(count || 0);
  if (!safeCount || avg === null || avg === undefined) return "No ratings yet";
  return `${Number(avg).toFixed(1)} ★ (${safeCount})`;
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

function marketMediaBlock(item, ownerName) {
  const photoUrl = safeUrl(item.photo_url);
  const logoUrl = safeUrl(item.brand_logo_url);
  const owner = String(ownerName || item.farmer_name || "Farmer");
  return `
    <div class="market-media">
      ${photoUrl ? `<img class="market-photo" src="${escapeHtml(photoUrl)}" alt="${escapeHtml(item.item_name || owner)}" loading="lazy" />` : `<div class="market-photo placeholder"><span>${escapeHtml(initials(item.item_name || owner))}</span></div>`}
      <div class="market-brand-pill">
        ${logoUrl ? `<img class="market-logo" src="${escapeHtml(logoUrl)}" alt="${escapeHtml(owner)} logo" loading="lazy" />` : `<span class="market-logo market-logo-fallback">${escapeHtml(initials(owner))}</span>`}
        <p class="market-seller-name">${escapeHtml(owner)}</p>
      </div>
    </div>
  `;
}
function farmerItemCard(item) {
  const activeBadge = item.is_active ? "available" : "busy";
  const isEditing = editingItemId === item.id;
  const tracksStock = item.quantity_available !== null;
  return `
    <article class="worker-card market-card" data-my-item-id="${item.id}">
      ${marketMediaBlock(item, session?.user?.full_name || item.farmer_name)}
      <div class="market-main">
        <div class="list-head market-title-row">
          <h3>${escapeHtml(item.item_name)}</h3>
          <span class="badge ${activeBadge}">${item.is_active ? "Active" : "Paused"}</span>
        </div>
        <div class="market-meta-row">
          <span class="badge day">${money(item.price_per_unit)} / ${escapeHtml(item.unit_label)}</span>
          <span class="badge">${quantityText(item.quantity_available, escapeHtml(item.unit_label))}</span>
          ${item.pickup_location ? `<span class="badge">Pickup: ${escapeHtml(item.pickup_location)}</span>` : ""}
        </div>
        <p class="market-description"><strong>Product rating:</strong> ${escapeHtml(ratingLabel(item.product_rating_avg, item.product_rating_count))}</p>
        <p class="market-description">${escapeHtml(item.description || "No description added yet.")}</p>
        <div class="worker-grid market-grid"><div><strong>Updated:</strong> ${formatDateTime(item.updated_at)}</div></div>
        <div class="actions-row">
          <button class="btn ghost" type="button" data-edit-item="${item.id}">${isEditing ? "Close Edit" : "Edit"}</button>
          <button class="btn ghost" type="button" data-toggle-item="${item.id}">${item.is_active ? "Pause" : "Activate"}</button>
          <button class="btn danger" type="button" data-delete-item="${item.id}">Delete</button>
        </div>
        ${isEditing ? `<form class="booking-form market-inline-edit-form" data-edit-item-form="${item.id}">
          <h4>Edit Listing</h4>
          <label>Product Name<input name="item_name" maxlength="120" value="${escapeHtml(item.item_name)}" required /></label>
          <label>Unit Label<input name="unit_label" maxlength="50" value="${escapeHtml(item.unit_label)}" required /></label>
          <label>Price Per Unit<input name="price_per_unit" type="number" step="0.01" min="0.01" value="${money(item.price_per_unit)}" required /></label>
          <label class="inline-check">Track Quantity<input data-edit-track-qty="${item.id}" name="track_quantity" type="checkbox" ${tracksStock ? "checked" : ""} /></label>
          <label>Quantity Available<input data-edit-qty-input="${item.id}" name="quantity_available" type="number" step="0.01" min="0" ${tracksStock ? `value="${money(item.quantity_available)}"` : ""} ${tracksStock ? "required" : "disabled"} /></label>
          <label>Pickup Location<input name="pickup_location" maxlength="180" value="${escapeHtml(item.pickup_location || "")}" /></label>
          <label>Product Photo URL<input name="photo_url" type="url" maxlength="500" value="${escapeHtml(item.photo_url || "")}" /></label>
          <label>Brand Logo URL<input name="brand_logo_url" type="url" maxlength="500" value="${escapeHtml(item.brand_logo_url || "")}" /></label>
          <label class="full">Description<textarea name="description" rows="2" maxlength="400">${escapeHtml(item.description || "")}</textarea></label>
          <div class="actions-row"><button class="btn" type="submit">Save Changes</button><button class="btn ghost" type="button" data-cancel-edit-item="${item.id}">Cancel</button></div>
          <p class="message booking-submit-message"></p>
        </form>` : ""}
      </div>
    </article>
  `;
}

function storeProfileFromItem(item) {
  return {
    store_name: item?.farmer_store_name || null,
    store_banner_url: item?.farmer_store_banner_url || null,
    store_about: item?.farmer_store_about || null,
    store_opening_hours: item?.farmer_store_opening_hours || null,
  };
}

function fillStoreProfileForm(profile) {
  if (!storeProfileForm) return;
  storeProfileForm.elements.store_name.value = profile?.store_name || "";
  storeProfileForm.elements.store_banner_url.value = profile?.store_banner_url || "";
  storeProfileForm.elements.store_about.value = profile?.store_about || "";
  storeProfileForm.elements.store_opening_hours.value = profile?.store_opening_hours || "";
}

function renderFarmerItems() {
  marketItemsList.innerHTML = farmerItems.length ? farmerItems.map(farmerItemCard).join("") : "No listings yet. Add your first product above.";
}

function buildStores(items) {
  const grouped = new Map();
  for (const item of items) {
    const key = item.farmer_user_id;
    if (!grouped.has(key)) {
      grouped.set(key, {
        id: key,
        farmer_name: item.farmer_name,
        store_name: item.farmer_store_name || item.farmer_name,
        store_banner_url: item.farmer_store_banner_url || null,
        store_about: item.farmer_store_about || null,
        store_opening_hours: item.farmer_store_opening_hours || null,
        brand_logo_url: item.brand_logo_url,
        photo_url: item.photo_url,
        pickup_location: item.pickup_location,
        farmer_rating_avg: item.farmer_rating_avg ?? null,
        farmer_rating_count: Number(item.farmer_rating_count || 0),
        items: [],
      });
    }
    const store = grouped.get(key);
    store.items.push(item);
    if (!store.photo_url && item.photo_url) store.photo_url = item.photo_url;
    if (!store.brand_logo_url && item.brand_logo_url) store.brand_logo_url = item.brand_logo_url;
    if (!store.pickup_location && item.pickup_location) store.pickup_location = item.pickup_location;
  }
  return Array.from(grouped.values()).sort((a, b) => a.store_name.localeCompare(b.store_name));
}

function storeCard(store) {
  const storeLike = {
    item_name: `${store.store_name} Store`,
    photo_url: store.store_banner_url || store.photo_url,
    brand_logo_url: store.brand_logo_url,
    farmer_name: store.store_name,
  };
  return `
    <article class="worker-card market-card market-store-card" data-open-store="${store.id}">
      ${marketMediaBlock(storeLike, store.store_name)}
      <div class="market-main">
        <div class="list-head market-title-row"><h3>${escapeHtml(store.store_name)}</h3><span class="badge day">${store.items.length} listing${store.items.length > 1 ? "s" : ""}</span></div>
        <div class="market-meta-row">${store.pickup_location ? `<span class="badge">${escapeHtml(store.pickup_location)}</span>` : `<span class="badge">Pickup location shared per listing</span>`}</div>
        <p class="market-description"><strong>${escapeHtml(ratingLabel(store.farmer_rating_avg, store.farmer_rating_count))}</strong></p>
        <p class="market-description">${escapeHtml(store.store_about || "Tap to enter this store and order.")}</p>
      </div>
    </article>
  `;
}

function renderStores() {
  const stores = buildStores(activeItems);
  marketItemsList.innerHTML = stores.length ? stores.map(storeCard).join("") : "No stores available right now.";
}

function selectedStore() {
  if (!selectedStoreId) return null;
  return buildStores(activeItems).find((store) => store.id === selectedStoreId) || null;
}

function storeItemCard(item) {
  const maxAttr = item.quantity_available === null || item.quantity_available === undefined ? "" : ` max="${item.quantity_available}"`;
  return `
    <article class="worker-card market-card" data-store-item="${item.id}">
      ${marketMediaBlock(item, item.farmer_name)}
      <div class="market-main">
        <div class="list-head market-title-row"><h3>${escapeHtml(item.item_name)}</h3><span class="badge day">${money(item.price_per_unit)} / ${escapeHtml(item.unit_label)}</span></div>
        <div class="market-meta-row"><span class="badge">${quantityText(item.quantity_available, escapeHtml(item.unit_label))}</span>${item.pickup_location ? `<span class="badge">${escapeHtml(item.pickup_location)}</span>` : ""}</div>
        <p class="market-description"><strong>Product rating:</strong> ${escapeHtml(ratingLabel(item.product_rating_avg, item.product_rating_count))}</p>
        <p class="market-description">${escapeHtml(item.description || "No description provided.")}</p>
        <div class="actions-row market-add-row"><label>Qty<input data-store-qty="${item.id}" type="number" step="0.01" min="0.01"${maxAttr} value="1" /></label><button class="btn" type="button" data-add-cart="${item.id}">Add to Cart</button></div>
      </div>
    </article>
  `;
}

function renderStoreDetail() {
  const store = selectedStore();
  if (!store) {
    selectedStoreId = null;
    customerStoreDetail?.classList.add("is-hidden");
    customerStoresView?.classList.remove("is-hidden");
    return;
  }

  customerStoresView?.classList.add("is-hidden");
  customerStoreDetail?.classList.remove("is-hidden");

  const storeLike = {
    item_name: `${store.store_name} Store`,
    photo_url: store.store_banner_url || store.photo_url,
    brand_logo_url: store.brand_logo_url,
    farmer_name: store.store_name,
    pickup_location: store.pickup_location,
  };
  storeHeader.innerHTML = `<article class="worker-card market-card">${marketMediaBlock(storeLike, store.store_name)}<div class="market-main"><h3>${escapeHtml(store.store_name)}</h3><p class="market-description">${store.items.length} listing${store.items.length > 1 ? "s" : ""} available.</p><p class="market-description"><strong>${escapeHtml(ratingLabel(store.farmer_rating_avg, store.farmer_rating_count))}</strong></p>${store.store_about ? `<p class="market-description">${escapeHtml(store.store_about)}</p>` : ""}${store.store_opening_hours ? `<p class="market-description"><strong>Hours:</strong> ${escapeHtml(store.store_opening_hours)}</p>` : ""}${store.pickup_location ? `<p class="market-description"><strong>Pickup:</strong> ${escapeHtml(store.pickup_location)}</p>` : ""}</div></article>`;
  storeItemsList.innerHTML = store.items.map(storeItemCard).join("");
  renderCart();
}

function renderCart() {
  const lines = Array.from(cart.values());
  if (!lines.length) {
    cartLines.innerHTML = '<p class="sub">Your cart is empty.</p>';
    cartTotal.textContent = "Total: 0.00";
    return;
  }

  cartLines.innerHTML = lines.map((line) => {
    const lineTotal = Number(line.quantity) * Number(line.item.price_per_unit);
    return `<article class="worker-card market-cart-line" data-cart-item="${line.item.id}"><p><strong>${escapeHtml(line.item.item_name)}</strong></p><p>${money(line.item.price_per_unit)} / ${escapeHtml(line.item.unit_label)}</p><p>Line total: ${money(lineTotal)}</p><div class="actions-row"><button class="btn ghost" type="button" data-cart-dec="${line.item.id}">-</button><span>${money(line.quantity)}</span><button class="btn ghost" type="button" data-cart-inc="${line.item.id}">+</button><button class="btn danger" type="button" data-cart-remove="${line.item.id}">Remove</button></div></article>`;
  }).join("");

  const total = lines.reduce((sum, line) => sum + Number(line.quantity) * Number(line.item.price_per_unit), 0);
  cartTotal.textContent = `Total: ${money(total)}`;
}

function openStore(storeId) {
  if (selectedStoreId && selectedStoreId !== storeId && cart.size > 0) {
    const confirmed = window.confirm("Switching stores will clear your current cart. Continue?");
    if (!confirmed) return;
    cart.clear();
  }
  selectedStoreId = storeId;
  setCartMessage("", true);
  renderStoreDetail();
}

function syncCartWithActiveItems() {
  if (!cart.size) return;
  const itemMap = new Map(activeItems.map((item) => [item.id, item]));
  for (const [itemId, line] of cart.entries()) {
    const latest = itemMap.get(itemId);
    if (!latest) {
      cart.delete(itemId);
      continue;
    }
    line.item = latest;
    if (latest.quantity_available !== null && Number(line.quantity) > Number(latest.quantity_available)) {
      line.quantity = Number(latest.quantity_available);
      if (line.quantity <= 0) cart.delete(itemId);
    }
  }
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
    return { label: "WhatsApp Customer", href: `https://wa.me/${digits}?text=${encodeURIComponent(text)}` };
  }
  const digits = normalizePhoneForWhatsapp(order.farmer_phone);
  if (!digits) return null;
  const text = `Hello ${order.farmer_name}, I am contacting you about order ${order.id.slice(0, 8)} for ${order.item_name_snapshot}.`;
  return { label: "WhatsApp Farmer", href: `https://wa.me/${digits}?text=${encodeURIComponent(text)}` };
}

function orderCard(order) {
  const badgeClass = statusBadgeClass(order.status);
  const wa = whatsappTarget(order);
  const canFarmerValidate = isFarmer && order.status === "pending";
  const canCustomerReview = isCustomer && order.status === "validated";
  const contactPhoneLabel = isFarmer ? "Customer Phone" : "Farmer Phone";
  const contactPhoneValue = isFarmer ? order.customer_phone : order.farmer_phone;

  return `
    <article class="worker-card" data-order-id="${order.id}">
      <div class="list-head"><h3>${escapeHtml(order.item_name_snapshot)}</h3><span class="badge ${badgeClass}">${orderStatusLabel(order.status)}</span></div>
      <div class="worker-grid">
        <div><strong>Quantity:</strong> ${money(order.quantity_ordered)} ${escapeHtml(order.unit_label_snapshot)}</div>
        <div><strong>Total:</strong> ${money(order.total_price)}</div>
        <div><strong>Unit Price:</strong> ${money(order.unit_price_snapshot)}</div>
        <div><strong>Date:</strong> ${formatDateTime(order.created_at)}</div>
        <div><strong>Farmer:</strong> ${escapeHtml(order.farmer_name)}</div>
        <div><strong>Customer:</strong> ${escapeHtml(order.customer_name)}</div>
        <div><strong>Pickup Time:</strong> ${formatDateTime(order.pickup_at)}</div>
        <div><strong>${contactPhoneLabel}:</strong> ${escapeHtml(contactPhoneValue || "-")}</div>
        <div class="full"><strong>Order Note:</strong> ${escapeHtml(order.note || "-")}</div>
        <div class="full"><strong>Farmer Response:</strong> ${escapeHtml(order.farmer_response_note || "-")}</div>
      </div>
      <div class="actions-row">${wa ? `<a class="btn ghost" href="${wa.href}" target="_blank" rel="noreferrer">${wa.label}</a>` : ""}</div>
      ${
        canCustomerReview
          ? `<form class="booking-form market-review-form" data-review-order-id="${order.id}">
               <h4>Rate Product & Store</h4>
               <div class="market-review-block">
                 <p class="sub"><strong>Product Rating</strong></p>
                 <div class="market-star-picker" data-star-picker="${order.id}" data-star-type="product">
                   ${[1, 2, 3, 4, 5]
                     .map((value) => `<button class="star-btn ${Number(order.product_rating || 0) >= value ? "is-on" : ""}" type="button" data-star-value="${value}" data-star-order="${order.id}" data-star-type="product" aria-label="${value} product stars">${Number(order.product_rating || 0) >= value ? "★" : "☆"}</button>`)
                     .join("")}
                 </div>
                 <input type="hidden" name="product_rating" value="${order.product_rating || ""}" />
                 <p class="market-star-caption" data-star-caption="product">${escapeHtml(order.product_rating ? starsText(order.product_rating) : "Tap stars to rate product")}</p>
                 <label>Product Review<textarea name="product_review" rows="2" maxlength="800" placeholder="Share product quality and taste">${escapeHtml(order.product_review || "")}</textarea></label>
               </div>
               <div class="market-review-block">
                 <p class="sub"><strong>Market/Store Rating</strong></p>
                 <div class="market-star-picker" data-star-picker="${order.id}" data-star-type="market">
                   ${[1, 2, 3, 4, 5]
                     .map((value) => `<button class="star-btn ${Number(order.market_rating || 0) >= value ? "is-on" : ""}" type="button" data-star-value="${value}" data-star-order="${order.id}" data-star-type="market" aria-label="${value} market stars">${Number(order.market_rating || 0) >= value ? "★" : "☆"}</button>`)
                     .join("")}
                 </div>
                 <input type="hidden" name="market_rating" value="${order.market_rating || ""}" />
                 <p class="market-star-caption" data-star-caption="market">${escapeHtml(order.market_rating ? starsText(order.market_rating) : "Tap stars to rate market")}</p>
                 <label>Market Review<textarea name="market_review" rows="2" maxlength="800" placeholder="Share delivery and store experience">${escapeHtml(order.market_review || "")}</textarea></label>
               </div>
               <div class="actions-row">
                 <button class="btn" type="submit" name="review_target" value="product">Save Product Rating</button>
                 <button class="btn ghost" type="submit" name="review_target" value="market">Save Store Rating</button>
               </div>
               <p class="message booking-submit-message"></p>
             </form>`
          : ""
      }
      ${canFarmerValidate ? `<form class="booking-form" data-validate-order-id="${order.id}"><h4>Validate Order</h4><label>Pickup Time<input name="pickup_at" type="datetime-local" required /></label><label>Response Note<textarea name="note" rows="2" placeholder="Optional"></textarea></label><div class="actions-row"><button class="btn" type="submit">Validate & Set Pickup</button><button class="btn ghost" type="button" data-reject-order="${order.id}">Reject Order</button></div><p class="message booking-submit-message"></p></form>` : ""}
      <section class="chat-panel"><h4>Order Chat</h4><div class="chat-messages" data-chat-list="${order.id}">Loading chat...</div><form class="chat-form" data-chat-form="${order.id}"><label>Message<textarea name="content" rows="2" maxlength="1200" required placeholder="Write a message..."></textarea></label><button class="btn ghost" type="submit">Send Message</button><p class="message booking-submit-message"></p></form></section>
    </article>
  `;
}

function chatMessageCard(message) {
  const mine = message.sender_user_id === session.user.id;
  return `<article class="chat-message ${mine ? "mine" : "other"}"><small>${escapeHtml(message.sender_name)} (${escapeHtml(message.sender_role)}) - ${formatDateTime(message.created_at)}</small><p>${escapeHtml(message.content)}</p></article>`;
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
    if (!farmerItems.some((item) => item.id === editingItemId)) editingItemId = null;
    if (!currentStoreProfile && farmerItems.length) {
      currentStoreProfile = storeProfileFromItem(farmerItems[0]);
      fillStoreProfileForm(currentStoreProfile);
    }
    renderFarmerItems();
    return;
  }

  const query = new FormData(marketFilterForm).get("q");
  const search = String(query || "").trim();
  const url = `${API_BASE}/market/items${search ? `?q=${encodeURIComponent(search)}` : ""}`;
  activeItems = (await requestJson(url)) || [];
  syncCartWithActiveItems();
  renderStores();
  if (selectedStoreId) renderStoreDetail();
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

async function loadStoreProfile() {
  if (!isFarmer) return;
  try {
    currentStoreProfile = await requestJson(`${API_BASE}/market/store-profile/mine`);
    fillStoreProfileForm(currentStoreProfile || {});
  } catch (error) {
    setStoreProfileMessage(error.message || "Could not load store profile", false);
  }
}

function setCreateQuantityMode() {
  if (!marketItemForm) return;
  const track = marketItemForm.elements.track_quantity.checked;
  marketItemForm.elements.quantity_available.disabled = !track;
  marketItemForm.elements.quantity_available.required = track;
  quantityLabel?.classList.toggle("is-hidden", !track);
  if (!track) marketItemForm.elements.quantity_available.value = "";
}

marketItemForm?.elements.track_quantity?.addEventListener("change", setCreateQuantityMode);
setCreateQuantityMode();

storeProfileForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    store_name: String(storeProfileForm.elements.store_name.value || "").trim() || null,
    store_banner_url: String(storeProfileForm.elements.store_banner_url.value || "").trim() || null,
    store_about: String(storeProfileForm.elements.store_about.value || "").trim() || null,
    store_opening_hours: String(storeProfileForm.elements.store_opening_hours.value || "").trim() || null,
  };

  setStoreProfileMessage("Saving store profile...", true);
  try {
    currentStoreProfile = await requestJson(`${API_BASE}/market/store-profile/mine`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    setStoreProfileMessage("Store profile saved.", true);
    await loadMarketItems();
  } catch (error) {
    setStoreProfileMessage(error.message || "Could not save store profile", false);
  }
});

marketItemForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fd = new FormData(marketItemForm);
  const trackQuantity = fd.get("track_quantity") !== null;
  const qtyRaw = String(fd.get("quantity_available") || "").trim();

  if (trackQuantity && !qtyRaw) {
    setFormMessage("Quantity is required when stock tracking is enabled.", false);
    return;
  }

  const payload = {
    item_name: String(fd.get("item_name") || "").trim(),
    description: String(fd.get("description") || "").trim() || null,
    brand_logo_url: String(fd.get("brand_logo_url") || "").trim() || null,
    photo_url: String(fd.get("photo_url") || "").trim() || null,
    pickup_location: String(fd.get("pickup_location") || "").trim() || null,
    unit_label: String(fd.get("unit_label") || "").trim(),
    price_per_unit: Number(fd.get("price_per_unit") || 0),
    quantity_available: trackQuantity ? Number(qtyRaw) : null,
    is_active: fd.get("is_active") !== null,
  };

  setFormMessage("Saving listing...", true);
  try {
    await requestJson(`${API_BASE}/market/items`, { method: "POST", headers: authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify(payload) });
    marketItemForm.reset();
    marketItemForm.elements.is_active.checked = true;
    marketItemForm.elements.track_quantity.checked = true;
    setCreateQuantityMode();
    setFormMessage("Listing saved.", true);
    await Promise.all([loadMarketItems(), loadOrders()]);
  } catch (error) {
    setFormMessage(error.message || "Could not save listing", false);
  }
});
marketItemsList.addEventListener("change", (event) => {
  const trackToggle = event.target.closest("input[data-edit-track-qty]");
  if (!trackToggle) return;
  const itemId = trackToggle.dataset.editTrackQty;
  const qtyInput = marketItemsList.querySelector(`input[data-edit-qty-input="${itemId}"]`);
  if (!qtyInput) return;
  qtyInput.disabled = !trackToggle.checked;
  qtyInput.required = trackToggle.checked;
  if (!trackToggle.checked) qtyInput.value = "";
});

marketItemsList.addEventListener("click", async (event) => {
  const storeCard = event.target.closest("[data-open-store]");
  if (storeCard && isCustomer) {
    openStore(storeCard.dataset.openStore);
    return;
  }

  const cancelEditBtn = event.target.closest("button[data-cancel-edit-item]");
  if (cancelEditBtn) {
    editingItemId = null;
    renderFarmerItems();
    return;
  }

  const editBtn = event.target.closest("button[data-edit-item]");
  if (editBtn) {
    const item = farmerItems.find((row) => row.id === editBtn.dataset.editItem);
    if (!item) return;
    editingItemId = editingItemId === item.id ? null : item.id;
    renderFarmerItems();
    return;
  }

  const toggleBtn = event.target.closest("button[data-toggle-item]");
  if (toggleBtn) {
    const item = farmerItems.find((row) => row.id === toggleBtn.dataset.toggleItem);
    if (!item) return;
    try {
      await requestJson(`${API_BASE}/market/items/${item.id}`, { method: "PATCH", headers: authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify({ is_active: !item.is_active }) });
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
      await requestJson(`${API_BASE}/market/items/${item.id}`, { method: "DELETE", headers: authHeaders() });
      await loadMarketItems();
    } catch (error) {
      setFormMessage(error.message || "Could not delete listing", false);
    }
  }
});

marketItemsList.addEventListener("submit", async (event) => {
  const editForm = event.target.closest("form[data-edit-item-form]");
  if (!editForm) return;
  event.preventDefault();

  const messageEl = editForm.querySelector(".booking-submit-message");
  const trackQuantity = editForm.elements.track_quantity.checked;
  const qtyRaw = String(editForm.elements.quantity_available.value || "").trim();

  if (trackQuantity && !qtyRaw) {
    messageEl.textContent = "Quantity is required when stock tracking is enabled.";
    messageEl.className = "message error";
    return;
  }

  const payload = {
    item_name: String(editForm.elements.item_name.value || "").trim(),
    description: String(editForm.elements.description.value || "").trim() || null,
    unit_label: String(editForm.elements.unit_label.value || "").trim(),
    price_per_unit: Number(editForm.elements.price_per_unit.value || 0),
    quantity_available: trackQuantity ? Number(qtyRaw) : null,
    pickup_location: String(editForm.elements.pickup_location.value || "").trim() || null,
    photo_url: String(editForm.elements.photo_url.value || "").trim() || null,
    brand_logo_url: String(editForm.elements.brand_logo_url.value || "").trim() || null,
  };

  messageEl.textContent = "Saving changes...";
  messageEl.className = "message success";

  try {
    await requestJson(`${API_BASE}/market/items/${editForm.dataset.editItemForm}`, { method: "PATCH", headers: authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify(payload) });
    editingItemId = null;
    setFormMessage("Listing updated.", true);
    await loadMarketItems();
  } catch (error) {
    messageEl.textContent = error.message || "Could not update listing";
    messageEl.className = "message error";
  }
});

storeBackBtn?.addEventListener("click", () => {
  selectedStoreId = null;
  customerStoreDetail?.classList.add("is-hidden");
  customerStoresView?.classList.remove("is-hidden");
});

storeItemsList?.addEventListener("click", (event) => {
  const addBtn = event.target.closest("button[data-add-cart]");
  if (!addBtn) return;
  const itemId = addBtn.dataset.addCart;
  const item = activeItems.find((row) => row.id === itemId);
  if (!item) return;

  const qtyInput = storeItemsList.querySelector(`input[data-store-qty="${itemId}"]`);
  const qty = Number(qtyInput?.value || 0);
  if (!Number.isFinite(qty) || qty <= 0) {
    setCartMessage("Please choose a valid quantity.", false);
    return;
  }

  if (item.quantity_available !== null && qty > Number(item.quantity_available)) {
    setCartMessage("Quantity exceeds available stock.", false);
    return;
  }

  const existing = cart.get(itemId);
  const nextQty = (existing?.quantity || 0) + qty;
  if (item.quantity_available !== null && nextQty > Number(item.quantity_available)) {
    setCartMessage("Total cart quantity exceeds available stock.", false);
    return;
  }

  cart.set(itemId, { item, quantity: nextQty });
  setCartMessage("Added to cart.", true);
  renderCart();
});

cartLines?.addEventListener("click", (event) => {
  const decBtn = event.target.closest("button[data-cart-dec]");
  if (decBtn) {
    const line = cart.get(decBtn.dataset.cartDec);
    if (!line) return;
    line.quantity = Number(line.quantity) - 1;
    if (line.quantity <= 0) cart.delete(decBtn.dataset.cartDec);
    renderCart();
    return;
  }

  const incBtn = event.target.closest("button[data-cart-inc]");
  if (incBtn) {
    const line = cart.get(incBtn.dataset.cartInc);
    if (!line) return;
    if (line.item.quantity_available !== null && Number(line.quantity) + 1 > Number(line.item.quantity_available)) {
      setCartMessage("Cannot go above available stock.", false);
      return;
    }
    line.quantity = Number(line.quantity) + 1;
    renderCart();
    return;
  }

  const removeBtn = event.target.closest("button[data-cart-remove]");
  if (removeBtn) {
    cart.delete(removeBtn.dataset.cartRemove);
    renderCart();
  }
});
cartCheckoutForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const lines = Array.from(cart.values());
  if (!lines.length) {
    setCartMessage("Your cart is empty.", false);
    return;
  }

  const note = String(cartCheckoutForm.elements.note.value || "").trim();
  setCartMessage("Placing cart orders...", true);

  try {
    for (const line of lines) {
      await requestJson(`${API_BASE}/market/orders`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ market_item_id: line.item.id, quantity_ordered: Number(line.quantity), note: note || null }),
      });
    }

    cart.clear();
    cartCheckoutForm.reset();
    setCartMessage("Order placed successfully.", true);
    await Promise.all([loadMarketItems(), loadOrders()]);
  } catch (error) {
    setCartMessage(error.message || "Could not checkout cart", false);
  }
});

marketOrdersList.addEventListener("submit", async (event) => {
  const reviewForm = event.target.closest("form[data-review-order-id]");
  if (reviewForm) {
    event.preventDefault();
    const messageEl = reviewForm.querySelector(".booking-submit-message");
    const target = event.submitter?.value === "market" ? "market" : "product";
    const productRating = Number(reviewForm.elements.product_rating.value || 0);
    const marketRating = Number(reviewForm.elements.market_rating.value || 0);
    const productReview = String(reviewForm.elements.product_review.value || "").trim();
    const marketReview = String(reviewForm.elements.market_review.value || "").trim();

    const payload = {
      product_rating: null,
      product_review: null,
      market_rating: null,
      market_review: null,
    };

    if (target === "product") {
      if (!Number.isFinite(productRating) || productRating < 1 || productRating > 5) {
        messageEl.textContent = "Please select a product star rating.";
        messageEl.className = "message error";
        return;
      }
      payload.product_rating = productRating;
      payload.product_review = productReview || null;
    } else {
      if (!Number.isFinite(marketRating) || marketRating < 1 || marketRating > 5) {
        messageEl.textContent = "Please select a store star rating.";
        messageEl.className = "message error";
        return;
      }
      payload.market_rating = marketRating;
      payload.market_review = marketReview || null;
    }

    messageEl.textContent = target === "product" ? "Saving product rating..." : "Saving store rating...";
    messageEl.className = "message success";
    try {
      await requestJson(`${API_BASE}/market/orders/${reviewForm.dataset.reviewOrderId}/customer-review`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      messageEl.textContent = target === "product" ? "Product rating saved." : "Store rating saved.";
      messageEl.className = "message success";
      await Promise.all([loadOrders(), loadMarketItems()]);
    } catch (error) {
      messageEl.textContent = error.message || "Could not save review";
      messageEl.className = "message error";
    }
    return;
  }

  const validateForm = event.target.closest("form[data-validate-order-id]");
  if (validateForm) {
    event.preventDefault();
    const messageEl = validateForm.querySelector(".booking-submit-message");
    const pickupLocal = String(validateForm.elements.pickup_at.value || "").trim();
    const payload = { action: "validate", pickup_at: pickupLocal ? new Date(pickupLocal).toISOString() : null, note: String(validateForm.elements.note.value || "").trim() || null };

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
  const starBtn = event.target.closest("button[data-star-order]");
  if (starBtn) {
    const orderId = starBtn.dataset.starOrder;
    const rating = Number(starBtn.dataset.starValue || 0);
    const starType = starBtn.dataset.starType || "product";
    const form = marketOrdersList.querySelector(`form[data-review-order-id="${orderId}"]`);
    if (!form) return;

    const inputName = starType === "market" ? "market_rating" : "product_rating";
    const input = form.elements[inputName];
    if (!input) return;
    input.value = String(rating);

    const caption = form.querySelector(`[data-star-caption="${starType}"]`);
    if (caption) caption.textContent = starsText(rating);

    const stars = form.querySelectorAll(`button[data-star-order="${orderId}"][data-star-type="${starType}"]`);
    stars.forEach((btn) => {
      const val = Number(btn.dataset.starValue || 0);
      btn.classList.toggle("is-on", val <= rating);
      btn.textContent = val <= rating ? "★" : "☆";
    });
    return;
  }

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

Promise.all([loadMarketItems(), loadOrders(), isFarmer ? loadStoreProfile() : Promise.resolve()]).catch((error) => {
  marketItemsList.innerHTML = `<p class="message error">${escapeHtml(error.message || "Could not load market")}</p>`;
});











