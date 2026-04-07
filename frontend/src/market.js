import "./ui-feedback.js";
import { API_BASE } from "./config.js";
import { authHeaders, clearSession, renderAppTabs, requireAuth, roleHome } from "./session.js";
import { uploadImageFile } from "./upload.js";

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
const linkedInventorySelect = document.getElementById("linked-inventory-select");
const marketUnitLabelInput = document.getElementById("market-unit-label-input");

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
const imageFitModal = document.getElementById("image-fit-modal");
const imageFitTitle = document.getElementById("image-fit-title");
const imageFitSubtitle = document.getElementById("image-fit-subtitle");
const imageFitStage = document.getElementById("image-fit-stage");
const imageFitPreview = document.getElementById("image-fit-preview");
const imageFitZoom = document.getElementById("image-fit-zoom");
const imageFitSaveBtn = document.getElementById("image-fit-save-btn");
const imageFitCancelBtn = document.getElementById("image-fit-cancel-btn");

let farmerItems = [];
let activeItems = [];
let currentOrders = [];
let editingItemId = null;
let selectedStoreId = null;
let currentStoreProfile = null;
let farmerInventoryItems = [];
const cart = new Map();
let imageFitSession = null;

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

function findInventoryItemById(itemId) {
  if (!itemId) return null;
  return farmerInventoryItems.find((row) => row.id === itemId) || null;
}

function renderLinkedInventoryOptions(selectedId = "") {
  if (!linkedInventorySelect) return;
  const options = ['<option value="">None (standalone listing)</option>'];
  for (const item of farmerInventoryItems) {
    const selected = String(item.id) === String(selectedId) ? " selected" : "";
    const label = `${item.item_name} (${money(item.quantity_on_hand)} ${item.unit_label} on hand)`;
    options.push(`<option value="${escapeHtml(item.id)}"${selected}>${escapeHtml(label)}</option>`);
  }
  linkedInventorySelect.innerHTML = options.join("");
}

function applyCreateLinkedInventorySelection() {
  if (!linkedInventorySelect || !marketUnitLabelInput) return;
  const selected = findInventoryItemById(linkedInventorySelect.value);
  if (selected) {
    marketUnitLabelInput.value = selected.unit_label || "";
    marketUnitLabelInput.readOnly = true;
  } else {
    marketUnitLabelInput.readOnly = false;
  }
}

async function loadFarmerInventoryOptions() {
  if (!isFarmer || !linkedInventorySelect) return;
  farmerInventoryItems = (await requestJson(`${API_BASE}/olive-inventory-items/mine`)) || [];
  renderLinkedInventoryOptions(linkedInventorySelect.value);
  applyCreateLinkedInventorySelection();
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



function normalizeImageMimeType(value) {
  const type = String(value || "").toLowerCase();
  if (type === "image/png" || type === "image/webp" || type === "image/jpeg" || type === "image/jpg") return type === "image/jpg" ? "image/jpeg" : type;
  return "image/jpeg";
}

function croppedFileName(originalName, mimeType) {
  const clean = String(originalName || "image").trim();
  const dot = clean.lastIndexOf(".");
  const base = dot > 0 ? clean.slice(0, dot) : clean;
  const ext = mimeType === "image/png" ? "png" : mimeType === "image/webp" ? "webp" : "jpg";
  return `${base}-framed.${ext}`;
}

function clampImageOffset(state) {
  const minX = Math.min(0, state.frameWidth - state.imageWidth * state.scale);
  const minY = Math.min(0, state.frameHeight - state.imageHeight * state.scale);
  state.offsetX = Math.min(0, Math.max(minX, state.offsetX));
  state.offsetY = Math.min(0, Math.max(minY, state.offsetY));
}

function applyImageFitTransform() {
  if (!imageFitPreview || !imageFitSession) return;
  imageFitPreview.style.transform = `translate(${imageFitSession.offsetX}px, ${imageFitSession.offsetY}px) scale(${imageFitSession.scale})`;
}

function setImageFitScale(nextScale, anchorX, anchorY) {
  if (!imageFitSession) return;
  const state = imageFitSession;
  const targetScale = Math.max(state.minScale, Math.min(state.maxScale, Number(nextScale) || state.scale));
  const fromScale = state.scale;
  const focusX = Number.isFinite(anchorX) ? anchorX : state.frameWidth / 2;
  const focusY = Number.isFinite(anchorY) ? anchorY : state.frameHeight / 2;
  const sourceX = (focusX - state.offsetX) / fromScale;
  const sourceY = (focusY - state.offsetY) / fromScale;
  state.scale = targetScale;
  state.offsetX = focusX - sourceX * targetScale;
  state.offsetY = focusY - sourceY * targetScale;
  clampImageOffset(state);
  applyImageFitTransform();
}

function clearImageFitSession() {
  imageFitSession = null;
  if (imageFitPreview) {
    imageFitPreview.removeAttribute("src");
    imageFitPreview.style.transform = "";
    imageFitPreview.style.width = "";
    imageFitPreview.style.height = "";
  }
  if (imageFitZoom) {
    imageFitZoom.min = "1";
    imageFitZoom.max = "3";
    imageFitZoom.step = "0.01";
    imageFitZoom.value = "1";
  }
}

function closeImageFitModal() {
  imageFitModal?.classList.add("is-hidden");
  imageFitStage?.classList.remove("is-dragging");
  document.body.classList.remove("image-fit-open");
  clearImageFitSession();
}

function loadImageMetaFromFile(file) {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight, src: objectUrl });
    };
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Could not load selected image."));
    };
    img.src = objectUrl;
  });
}

async function openImageFitDialog(file, { title, subtitle, aspectRatio = 16 / 9, outputWidth = 1600 } = {}) {
  if (!imageFitModal || !imageFitStage || !imageFitPreview || !imageFitZoom || !imageFitSaveBtn || !imageFitCancelBtn) return file;

  const metadata = await loadImageMetaFromFile(file);
  imageFitTitle.textContent = title || "Fit Image";
  imageFitSubtitle.textContent = subtitle || "Drag image to frame. Use zoom to fit perfectly.";
  imageFitStage.style.aspectRatio = String(aspectRatio);

  imageFitPreview.src = metadata.src;
  imageFitPreview.style.width = `${metadata.width}px`;
  imageFitPreview.style.height = `${metadata.height}px`;

  imageFitModal.classList.remove("is-hidden");
  document.body.classList.add("image-fit-open");

  const stageRect = imageFitStage.getBoundingClientRect();
  const frameWidth = Math.max(120, stageRect.width);
  const frameHeight = Math.max(80, stageRect.height);
  const minScale = Math.max(frameWidth / metadata.width, frameHeight / metadata.height);
  const maxScale = minScale * 3;

  imageFitSession = {
    file,
    mimeType: normalizeImageMimeType(file.type),
    imageWidth: metadata.width,
    imageHeight: metadata.height,
    frameWidth,
    frameHeight,
    minScale,
    maxScale,
    scale: minScale,
    offsetX: (frameWidth - metadata.width * minScale) / 2,
    offsetY: (frameHeight - metadata.height * minScale) / 2,
    dragging: false,
    dragStartX: 0,
    dragStartY: 0,
    dragOriginX: 0,
    dragOriginY: 0,
    resolve: null,
    aspectRatio,
    outputWidth,
  };

  imageFitZoom.min = String(minScale);
  imageFitZoom.max = String(maxScale);
  imageFitZoom.step = String((maxScale - minScale) / 200 || 0.01);
  imageFitZoom.value = String(minScale);
  clampImageOffset(imageFitSession);
  applyImageFitTransform();

  return new Promise((resolve) => {
    imageFitSession.resolve = resolve;
    imageFitSaveBtn.textContent = "Apply & Upload";
    imageFitCancelBtn.focus();
  });
}

async function finalizeImageFitSession() {
  if (!imageFitSession?.resolve) return;
  const state = imageFitSession;
  const outputWidth = Math.max(600, Number(state.outputWidth) || 1600);
  const outputHeight = Math.max(300, Math.round(outputWidth / state.aspectRatio));
  const sx = Math.max(0, Math.min(state.imageWidth - state.frameWidth / state.scale, -state.offsetX / state.scale));
  const sy = Math.max(0, Math.min(state.imageHeight - state.frameHeight / state.scale, -state.offsetY / state.scale));
  const sw = Math.min(state.imageWidth, state.frameWidth / state.scale);
  const sh = Math.min(state.imageHeight, state.frameHeight / state.scale);

  const canvas = document.createElement("canvas");
  canvas.width = outputWidth;
  canvas.height = outputHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    state.resolve(null);
    if (imageFitPreview?.src.startsWith("blob:")) URL.revokeObjectURL(imageFitPreview.src);
    closeImageFitModal();
    return;
  }

  ctx.drawImage(imageFitPreview, sx, sy, sw, sh, 0, 0, outputWidth, outputHeight);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, state.mimeType, 0.92));
  if (!blob) {
    state.resolve(null);
    if (imageFitPreview?.src.startsWith("blob:")) URL.revokeObjectURL(imageFitPreview.src);
    closeImageFitModal();
    return;
  }

  const fileName = croppedFileName(state.file?.name, state.mimeType);
  const outputFile = new File([blob], fileName, { type: state.mimeType, lastModified: Date.now() });
  state.resolve(outputFile);
  if (imageFitPreview?.src.startsWith("blob:")) URL.revokeObjectURL(imageFitPreview.src);
  closeImageFitModal();
}

function cancelImageFitSession() {
  if (!imageFitSession?.resolve) return;
  imageFitSession.resolve(null);
  if (imageFitPreview?.src.startsWith("blob:")) URL.revokeObjectURL(imageFitPreview.src);
  closeImageFitModal();
}

async function fitAndUploadImage(file, slot, { messageSetter } = {}) {
  if (!file) return null;
  const slots = {
    store_banner: { title: "Fit Store Banner", subtitle: "Drag to choose what appears on your store cover.", aspectRatio: 16 / 6, outputWidth: 1800 },
    product_photo: { title: "Fit Product Photo", subtitle: "Drag to center your product in the listing card.", aspectRatio: 16 / 10, outputWidth: 1600 },
    brand_logo: { title: "Fit Brand Logo", subtitle: "Drag to frame your logo nicely in the badge.", aspectRatio: 1, outputWidth: 1000 },
  };
  const config = slots[slot] || slots.product_photo;

  messageSetter?.("Open image editor...", true);
  const fittedFile = await openImageFitDialog(file, config);
  if (!fittedFile) throw new Error("Image selection canceled.");
  messageSetter?.("Uploading image...", true);
  return uploadImageFile(fittedFile, { filename: fittedFile.name });
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
  const linkedInventory = findInventoryItemById(item.linked_inventory_item_id);
  const linkedBadge = linkedInventory ? `<span class="badge">Inventory-linked: ${escapeHtml(linkedInventory.item_name)}</span>` : "";

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
          ${linkedBadge}
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
          <label>Unit Label<input name="unit_label" maxlength="50" value="${escapeHtml(item.unit_label)}" ${item.linked_inventory_item_id ? "readonly" : ""} required /></label>
          <label>Link To Inventory Item
            <select name="linked_inventory_item_id" data-edit-linked-item="${item.id}">
              <option value="">None (standalone listing)</option>
              ${farmerInventoryItems
                .map((inv) => `<option value="${escapeHtml(inv.id)}" ${String(inv.id) === String(item.linked_inventory_item_id || "") ? "selected" : ""}>${escapeHtml(`${inv.item_name} (${money(inv.quantity_on_hand)} ${inv.unit_label})`)}</option>`)
                .join("")}
            </select>
          </label>
          <label>Price Per Unit<input name="price_per_unit" type="number" step="0.01" min="0.01" value="${money(item.price_per_unit)}" required /></label>
          <label class="inline-check">Track Quantity<input data-edit-track-qty="${item.id}" name="track_quantity" type="checkbox" ${tracksStock ? "checked" : ""} /></label>
          <label>Quantity Available<input data-edit-qty-input="${item.id}" name="quantity_available" type="number" step="0.01" min="0" ${tracksStock ? `value="${money(item.quantity_available)}"` : ""} ${tracksStock ? "required" : "disabled"} /></label>
          <label>Pickup Location<input name="pickup_location" maxlength="180" value="${escapeHtml(item.pickup_location || "")}" /></label>
          <label>Product Photo (PNG/JPG)<input name="photo_file" type="file" accept="image/png,image/jpeg,image/jpg,image/webp" /></label>
          <input name="photo_url" type="hidden" value="${escapeHtml(item.photo_url || "")}" />
          <label>Brand Logo (PNG/JPG)<input name="brand_logo_file" type="file" accept="image/png,image/jpeg,image/jpg,image/webp" /></label>
          <input name="brand_logo_url" type="hidden" value="${escapeHtml(item.brand_logo_url || "")}" />
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
  if (status === "validated" || status === "picked_up") return "available";
  if (status === "rejected" || status === "canceled") return "busy";
  return "day";
}

function orderStatusLabel(status) {
  if (status === "validated") return "Validated";
  if (status === "picked_up") return "Picked Up";
  if (status === "rejected") return "Rejected";
  if (status === "canceled") return "Canceled";
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
  const canFarmerCancel = isFarmer && order.status === "validated";
  const canFarmerConfirmPickup = isFarmer && order.status === "validated";
  const canCustomerReview = isCustomer && (order.status === "validated" || order.status === "picked_up");
  const contactPhoneLabel = isFarmer ? "Customer Phone" : "Farmer Phone";
  const contactPhoneValue = isFarmer ? order.customer_phone : order.farmer_phone;
  const inventoryWarning = order.inventory_shortage_alert ? `<p class="message error">Inventory alert: ${escapeHtml(order.inventory_shortage_note || "Stock was lower than requested. You can still fulfill manually.")}</p>` : "";
  const pickupCodeForCustomer = isCustomer && order.status === "validated" && order.pickup_code
    ? `<p class="message success"><strong>Your pickup code:</strong> ${escapeHtml(order.pickup_code)}</p>`
    : "";

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
        <div><strong>Picked Up At:</strong> ${formatDateTime(order.picked_up_at)}</div>
        <div><strong>${contactPhoneLabel}:</strong> ${escapeHtml(contactPhoneValue || "-")}</div>
        <div><strong>Reserved From Inventory:</strong> ${money(order.inventory_reserved_quantity)} ${escapeHtml(order.unit_label_snapshot)}</div>
        <div class="full"><strong>Order Note:</strong> ${escapeHtml(order.note || "-")}</div>
        <div class="full"><strong>Farmer Response:</strong> ${escapeHtml(order.farmer_response_note || "-")}</div>
      </div>
      ${pickupCodeForCustomer}
      ${inventoryWarning}
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
      ${canFarmerCancel ? `<div class="actions-row"><button class="btn ghost" type="button" data-cancel-order="${order.id}">Cancel Validated Order</button></div>` : ""}
      ${canFarmerConfirmPickup ? `<form class="booking-form" data-pickup-order-id="${order.id}"><h4>Confirm Pickup</h4><label>Customer Pickup Code<input name="pickup_code" minlength="4" maxlength="12" required placeholder="Enter code from customer" /></label><button class="btn" type="submit">Mark As Picked Up</button><p class="message booking-submit-message"></p></form>` : ""}
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
    await loadFarmerInventoryOptions();
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
linkedInventorySelect?.addEventListener("change", applyCreateLinkedInventorySelection);
setCreateQuantityMode();
applyCreateLinkedInventorySelection();

imageFitZoom?.addEventListener("input", () => {
  if (!imageFitSession) return;
  setImageFitScale(Number(imageFitZoom.value));
});

imageFitStage?.addEventListener("pointerdown", (event) => {
  if (!imageFitSession) return;
  imageFitSession.dragging = true;
  imageFitSession.dragStartX = event.clientX;
  imageFitSession.dragStartY = event.clientY;
  imageFitSession.dragOriginX = imageFitSession.offsetX;
  imageFitSession.dragOriginY = imageFitSession.offsetY;
  imageFitStage.classList.add("is-dragging");
  imageFitStage.setPointerCapture(event.pointerId);
});

imageFitStage?.addEventListener("pointermove", (event) => {
  if (!imageFitSession?.dragging) return;
  const dx = event.clientX - imageFitSession.dragStartX;
  const dy = event.clientY - imageFitSession.dragStartY;
  imageFitSession.offsetX = imageFitSession.dragOriginX + dx;
  imageFitSession.offsetY = imageFitSession.dragOriginY + dy;
  clampImageOffset(imageFitSession);
  applyImageFitTransform();
});

imageFitStage?.addEventListener("pointerup", (event) => {
  if (!imageFitSession) return;
  imageFitSession.dragging = false;
  imageFitStage.classList.remove("is-dragging");
  if (imageFitStage.hasPointerCapture(event.pointerId)) imageFitStage.releasePointerCapture(event.pointerId);
});

imageFitStage?.addEventListener("pointercancel", (event) => {
  if (!imageFitSession) return;
  imageFitSession.dragging = false;
  imageFitStage.classList.remove("is-dragging");
  if (imageFitStage.hasPointerCapture(event.pointerId)) imageFitStage.releasePointerCapture(event.pointerId);
});

imageFitCancelBtn?.addEventListener("click", cancelImageFitSession);
imageFitSaveBtn?.addEventListener("click", () => {
  void finalizeImageFitSession();
});

document.addEventListener("keydown", (event) => {
  if (!imageFitSession) return;
  if (event.key === "Escape") {
    event.preventDefault();
    cancelImageFitSession();
  }
});

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
    const bannerFile = storeProfileForm.elements.store_banner_file?.files?.[0] || null;
    if (bannerFile) {
      payload.store_banner_url = await fitAndUploadImage(bannerFile, "store_banner", { messageSetter: setStoreProfileMessage });
      storeProfileForm.elements.store_banner_url.value = payload.store_banner_url || "";
    }

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

  const linkedInventoryItemIdRaw = String(fd.get("linked_inventory_item_id") || "").trim();
  const payload = {
    item_name: String(fd.get("item_name") || "").trim(),
    description: String(fd.get("description") || "").trim() || null,
    brand_logo_url: String(fd.get("brand_logo_url") || "").trim() || null,
    photo_url: String(fd.get("photo_url") || "").trim() || null,
    pickup_location: String(fd.get("pickup_location") || "").trim() || null,
    unit_label: String(fd.get("unit_label") || "").trim(),
    linked_inventory_item_id: linkedInventoryItemIdRaw || null,
    price_per_unit: Number(fd.get("price_per_unit") || 0),
    quantity_available: trackQuantity ? Number(qtyRaw) : null,
    is_active: fd.get("is_active") !== null,
  };

  setFormMessage("Saving listing...", true);
  try {
    const brandFile = marketItemForm.elements.brand_logo_file?.files?.[0] || null;
    const photoFile = marketItemForm.elements.photo_file?.files?.[0] || null;
    if (brandFile) payload.brand_logo_url = await fitAndUploadImage(brandFile, "brand_logo", { messageSetter: setFormMessage });
    if (photoFile) payload.photo_url = await fitAndUploadImage(photoFile, "product_photo", { messageSetter: setFormMessage });

    await requestJson(`${API_BASE}/market/items`, { method: "POST", headers: authHeaders({ "Content-Type": "application/json" }), body: JSON.stringify(payload) });
    marketItemForm.reset();
    marketItemForm.elements.is_active.checked = true;
    marketItemForm.elements.track_quantity.checked = true;
    marketItemForm.elements.photo_url.value = "";
    marketItemForm.elements.brand_logo_url.value = "";
    if (linkedInventorySelect) linkedInventorySelect.value = "";
    applyCreateLinkedInventorySelection();
    setCreateQuantityMode();
    setFormMessage("Listing saved.", true);
    await Promise.all([loadMarketItems(), loadOrders()]);
  } catch (error) {
    setFormMessage(error.message || "Could not save listing", false);
  }
});
marketItemsList.addEventListener("change", (event) => {
  const trackToggle = event.target.closest("input[data-edit-track-qty]");
  if (trackToggle) {
    const itemId = trackToggle.dataset.editTrackQty;
    const qtyInput = marketItemsList.querySelector(`input[data-edit-qty-input="${itemId}"]`);
    if (!qtyInput) return;
    qtyInput.disabled = !trackToggle.checked;
    qtyInput.required = trackToggle.checked;
    if (!trackToggle.checked) qtyInput.value = "";
    return;
  }

  const linkedSelect = event.target.closest("select[data-edit-linked-item]");
  if (!linkedSelect) return;
  const editForm = linkedSelect.closest("form[data-edit-item-form]");
  if (!editForm) return;

  const unitInput = editForm.elements.unit_label;
  const selected = findInventoryItemById(linkedSelect.value);
  if (selected) {
    unitInput.value = selected.unit_label;
    unitInput.readOnly = true;
  } else {
    unitInput.readOnly = false;
  }
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
    linked_inventory_item_id: String(editForm.elements.linked_inventory_item_id.value || "").trim() || null,
    price_per_unit: Number(editForm.elements.price_per_unit.value || 0),
    quantity_available: trackQuantity ? Number(qtyRaw) : null,
    pickup_location: String(editForm.elements.pickup_location.value || "").trim() || null,
    photo_url: String(editForm.elements.photo_url.value || "").trim() || null,
    brand_logo_url: String(editForm.elements.brand_logo_url.value || "").trim() || null,
  };

  messageEl.textContent = "Saving changes...";
  messageEl.className = "message success";

  try {
    const editBrandFile = editForm.elements.brand_logo_file?.files?.[0] || null;
    const editPhotoFile = editForm.elements.photo_file?.files?.[0] || null;
    if (editBrandFile) payload.brand_logo_url = await fitAndUploadImage(editBrandFile, "brand_logo", { messageSetter: (text, ok) => {
      messageEl.textContent = text;
      messageEl.className = `message ${ok ? "success" : "error"}`;
    } });
    if (editPhotoFile) payload.photo_url = await fitAndUploadImage(editPhotoFile, "product_photo", { messageSetter: (text, ok) => {
      messageEl.textContent = text;
      messageEl.className = `message ${ok ? "success" : "error"}`;
    } });

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

  const pickupForm = event.target.closest("form[data-pickup-order-id]");
  if (pickupForm) {
    event.preventDefault();
    const messageEl = pickupForm.querySelector(".booking-submit-message");
    const pickupCode = String(pickupForm.elements.pickup_code.value || "").trim();

    messageEl.textContent = "Validating pickup code...";
    messageEl.className = "message success";

    try {
      await requestJson(`${API_BASE}/market/orders/${pickupForm.dataset.pickupOrderId}/pickup-confirmation`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ pickup_code: pickupCode }),
      });
      messageEl.textContent = "Order marked as picked up.";
      messageEl.className = "message success";
      await loadOrders();
    } catch (error) {
      messageEl.textContent = error.message || "Could not confirm pickup";
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
      const updated = await requestJson(`${API_BASE}/market/orders/${validateForm.dataset.validateOrderId}/farmer-validation`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      if (updated?.inventory_shortage_alert) {
        messageEl.textContent = updated.inventory_shortage_note || "Validated with inventory shortage alert.";
        messageEl.className = "message error";
      } else {
        messageEl.textContent = "Order validated with pickup time.";
        messageEl.className = "message success";
      }
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

  const cancelBtn = event.target.closest("button[data-cancel-order]");
  if (cancelBtn) {
    const note = window.prompt("Reason for canceling this validated order (optional)", "") ?? "";
    try {
      await requestJson(`${API_BASE}/market/orders/${cancelBtn.dataset.cancelOrder}/farmer-validation`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ action: "cancel", note: note.trim() || null }),
      });
      await loadOrders();
    } catch (error) {
      window.alert(error.message || "Could not cancel order");
    }
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















