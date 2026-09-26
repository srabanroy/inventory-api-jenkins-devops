/* Inventory dashboard: a small dependency-free client for the existing REST API. */

const state = {
  items: [],
  apiKey: sessionStorage.getItem("inventoryApiKey") || "",
};

const elements = {
  connectionForm: document.querySelector("#connection-form"),
  apiKey: document.querySelector("#api-key"),
  connectionHelp: document.querySelector("#connection-help"),
  serviceState: document.querySelector("#service-state"),
  itemForm: document.querySelector("#item-form"),
  itemId: document.querySelector("#item-id"),
  sku: document.querySelector("#sku"),
  name: document.querySelector("#name"),
  quantity: document.querySelector("#quantity"),
  saveButton: document.querySelector("#save-button"),
  cancelButton: document.querySelector("#cancel-button"),
  search: document.querySelector("#search"),
  inventoryBody: document.querySelector("#inventory-body"),
  productCount: document.querySelector("#product-count"),
  unitCount: document.querySelector("#unit-count"),
  lowStockCount: document.querySelector("#low-stock-count"),
  toast: document.querySelector("#toast"),
};

let toastTimer;

function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.classList.add("is-visible");
  toastTimer = setTimeout(() => elements.toast.classList.remove("is-visible"), 3200);
}

function setServiceState(label, statusClass = "") {
  elements.serviceState.className = `service-state ${statusClass}`.trim();
  elements.serviceState.querySelector("span:last-child").textContent = label;
}

// A single request helper keeps authentication and API error handling consistent.
async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-API-Key", state.apiKey);
  if (options.body) headers.set("Content-Type", "application/json");

  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const validation = Array.isArray(data.details) ? `: ${data.details.join(", ")}` : "";
    throw new Error(`${data.error || "Request failed"}${validation}`);
  }

  return data;
}

function formatDate(value) {
  if (!value) return "Recently updated";
  const parsed = new Date(value.replace(" ", "T") + "Z");
  if (Number.isNaN(parsed.valueOf())) return "Recently updated";
  return `Updated ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(parsed)}`;
}

// Build table rows with DOM APIs so values returned by the API are never interpreted as HTML.
function renderItems() {
  const query = elements.search.value.trim().toLowerCase();
  const visibleItems = state.items.filter((item) =>
    `${item.name} ${item.sku}`.toLowerCase().includes(query),
  );

  elements.inventoryBody.replaceChildren();

  if (!visibleItems.length) {
    const row = document.createElement("tr");
    row.className = "message-row";
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = state.items.length ? "No items match your search." : "No inventory yet. Add the first item.";
    row.append(cell);
    elements.inventoryBody.append(row);
    return;
  }

  visibleItems.forEach((item) => {
    const row = document.createElement("tr");

    const itemCell = document.createElement("td");
    const itemName = document.createElement("span");
    itemName.className = "item-name";
    itemName.textContent = item.name;
    const itemDate = document.createElement("span");
    itemDate.className = "item-date";
    itemDate.textContent = formatDate(item.updated_at);
    itemCell.append(itemName, itemDate);

    const skuCell = document.createElement("td");
    const skuCode = document.createElement("span");
    skuCode.className = "sku-code";
    skuCode.textContent = item.sku;
    skuCell.append(skuCode);

    const quantityCell = document.createElement("td");
    const quantity = document.createElement("span");
    quantity.className = `quantity-pill${item.quantity <= 5 ? " is-low" : ""}`;
    quantity.textContent = item.quantity;
    quantityCell.append(quantity);

    const actionsCell = document.createElement("td");
    actionsCell.className = "row-actions";
    const editButton = document.createElement("button");
    editButton.className = "icon-button";
    editButton.type = "button";
    editButton.textContent = "Edit";
    editButton.addEventListener("click", () => beginEdit(item));
    const deleteButton = document.createElement("button");
    deleteButton.className = "icon-button danger";
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => deleteItem(item));
    actionsCell.append(editButton, deleteButton);

    row.append(itemCell, skuCell, quantityCell, actionsCell);
    elements.inventoryBody.append(row);
  });
}

function updateSummary() {
  elements.productCount.textContent = state.items.length;
  elements.unitCount.textContent = state.items.reduce((total, item) => total + item.quantity, 0);
  elements.lowStockCount.textContent = state.items.filter((item) => item.quantity <= 5).length;
}

async function loadItems() {
  if (!state.apiKey) return;

  elements.inventoryBody.innerHTML = '<tr class="message-row"><td colspan="4">Loading inventory…</td></tr>';
  try {
    const data = await apiRequest("/api/items");
    state.items = data.items;
    sessionStorage.setItem("inventoryApiKey", state.apiKey);
    elements.connectionHelp.textContent = "Connected. The key is stored for this browser session.";
    renderItems();
    updateSummary();
    showToast("Inventory connected");
  } catch (error) {
    sessionStorage.removeItem("inventoryApiKey");
    state.items = [];
    elements.inventoryBody.innerHTML = '<tr class="message-row"><td colspan="4">Unable to load inventory. Check your API key.</td></tr>';
    elements.connectionHelp.textContent = "Connection failed. Check the key and try again.";
    updateSummary();
    showToast(error.message, true);
  }
}

function resetEditor() {
  elements.itemForm.reset();
  elements.itemId.value = "";
  elements.quantity.value = "0";
  elements.saveButton.textContent = "Add item";
  elements.cancelButton.hidden = true;
  document.querySelector("#editor-title").textContent = "Add an item";
}

function beginEdit(item) {
  elements.itemId.value = item.id;
  elements.sku.value = item.sku;
  elements.name.value = item.name;
  elements.quantity.value = item.quantity;
  elements.saveButton.textContent = "Save changes";
  elements.cancelButton.hidden = false;
  document.querySelector("#editor-title").textContent = "Edit item";
  elements.sku.focus();
}

async function deleteItem(item) {
  if (!window.confirm(`Delete ${item.name}? This cannot be undone.`)) return;

  try {
    await apiRequest(`/api/items/${item.id}`, { method: "DELETE" });
    showToast(`${item.name} deleted`);
    if (String(item.id) === elements.itemId.value) resetEditor();
    await loadItems();
  } catch (error) {
    showToast(error.message, true);
  }
}

elements.connectionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  state.apiKey = elements.apiKey.value.trim();
  await loadItems();
});

elements.itemForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.apiKey) {
    showToast("Connect with an API key first", true);
    elements.apiKey.focus();
    return;
  }

  const itemId = elements.itemId.value;
  const payload = {
    sku: elements.sku.value,
    name: elements.name.value,
    quantity: Number(elements.quantity.value),
  };

  elements.saveButton.disabled = true;
  try {
    await apiRequest(itemId ? `/api/items/${itemId}` : "/api/items", {
      method: itemId ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    showToast(itemId ? "Item updated" : "Item added");
    resetEditor();
    await loadItems();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    elements.saveButton.disabled = false;
  }
});

elements.cancelButton.addEventListener("click", resetEditor);
elements.search.addEventListener("input", renderItems);

// Health is public so it can be displayed before an API key is entered.
fetch("/health")
  .then((response) => {
    if (!response.ok) throw new Error("Service unavailable");
    setServiceState("Service healthy", "is-ready");
  })
  .catch(() => setServiceState("Service unavailable", "is-down"));

if (state.apiKey) {
  elements.apiKey.value = state.apiKey;
  loadItems();
}
