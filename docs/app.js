/* Browser-only GitHub Pages demo. The production application uses the Flask API. */

const storageKey = "stockroomDemoItems";
const sampleItems = [
  { id: 1, sku: "KB-001", name: "Mechanical keyboard", quantity: 8 },
  { id: 2, sku: "DOCK-12", name: "USB-C dock", quantity: 4 },
  { id: 3, sku: "STAND-7", name: "Laptop stand", quantity: 13 },
];

const elements = {
  itemForm: document.querySelector("#item-form"),
  itemId: document.querySelector("#item-id"),
  sku: document.querySelector("#sku"),
  name: document.querySelector("#name"),
  quantity: document.querySelector("#quantity"),
  saveButton: document.querySelector("#save-button"),
  cancelButton: document.querySelector("#cancel-button"),
  resetDemo: document.querySelector("#reset-demo"),
  search: document.querySelector("#search"),
  inventoryBody: document.querySelector("#inventory-body"),
  productCount: document.querySelector("#product-count"),
  unitCount: document.querySelector("#unit-count"),
  lowStockCount: document.querySelector("#low-stock-count"),
  toast: document.querySelector("#toast"),
};

let toastTimer;

function newTimestamp() {
  return new Date().toISOString().replace("T", " ").replace("Z", "").split(".")[0];
}

function seededItems() {
  const timestamp = newTimestamp();
  return sampleItems.map((item) => ({ ...item, updated_at: timestamp }));
}

function loadStoredItems() {
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey));
    return Array.isArray(stored) ? stored : seededItems();
  } catch {
    return seededItems();
  }
}

const state = { items: loadStoredItems() };

function persistItems() {
  localStorage.setItem(storageKey, JSON.stringify(state.items));
}

function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.classList.add("is-visible");
  toastTimer = setTimeout(() => elements.toast.classList.remove("is-visible"), 3200);
}

function formatDate(value) {
  if (!value) return "Recently updated";
  const parsed = new Date(value.replace(" ", "T") + "Z");
  if (Number.isNaN(parsed.valueOf())) return "Recently updated";
  return `Updated ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(parsed)}`;
}

function updateSummary() {
  elements.productCount.textContent = state.items.length;
  elements.unitCount.textContent = state.items.reduce((total, item) => total + item.quantity, 0);
  elements.lowStockCount.textContent = state.items.filter((item) => item.quantity <= 5).length;
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

function resetEditor() {
  elements.itemForm.reset();
  elements.itemId.value = "";
  elements.quantity.value = "0";
  elements.saveButton.textContent = "Add item";
  elements.cancelButton.hidden = true;
  document.querySelector("#editor-title").textContent = "Add an item";
}

function deleteItem(item) {
  if (!window.confirm(`Delete ${item.name}? This cannot be undone.`)) return;
  state.items = state.items.filter((candidate) => candidate.id !== item.id);
  persistItems();
  if (String(item.id) === elements.itemId.value) resetEditor();
  renderItems();
  showToast(`${item.name} deleted`);
}

function createActionButton(label, className, handler) {
  const button = document.createElement("button");
  button.className = className;
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

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
    cell.textContent = state.items.length
      ? "No items match your search."
      : "No inventory yet. Add the first item.";
    row.append(cell);
    elements.inventoryBody.append(row);
    updateSummary();
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
    actionsCell.append(
      createActionButton("Edit", "icon-button", () => beginEdit(item)),
      createActionButton("Delete", "icon-button danger", () => deleteItem(item)),
    );

    row.append(itemCell, skuCell, quantityCell, actionsCell);
    elements.inventoryBody.append(row);
  });

  updateSummary();
}

elements.itemForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const itemId = Number(elements.itemId.value);
  const sku = elements.sku.value.trim();
  const name = elements.name.value.trim();
  const quantity = Number(elements.quantity.value);

  if (!sku || !name || !Number.isInteger(quantity) || quantity < 0) {
    showToast("Enter a name, SKU, and non-negative whole quantity", true);
    return;
  }

  const duplicate = state.items.some(
    (item) => item.sku.toLowerCase() === sku.toLowerCase() && item.id !== itemId,
  );
  if (duplicate) {
    showToast("That SKU is already in use", true);
    return;
  }

  if (itemId) {
    const item = state.items.find((candidate) => candidate.id === itemId);
    if (item) Object.assign(item, { sku, name, quantity, updated_at: newTimestamp() });
  } else {
    const nextId = state.items.reduce((maximum, item) => Math.max(maximum, item.id), 0) + 1;
    state.items.push({ id: nextId, sku, name, quantity, updated_at: newTimestamp() });
  }

  persistItems();
  showToast(itemId ? "Item updated" : "Item added");
  resetEditor();
  renderItems();
});

elements.cancelButton.addEventListener("click", resetEditor);
elements.search.addEventListener("input", renderItems);
elements.resetDemo.addEventListener("click", () => {
  state.items = seededItems();
  persistItems();
  resetEditor();
  elements.search.value = "";
  renderItems();
  showToast("Sample inventory restored");
});

persistItems();
renderItems();
