// -------------------------------------------------------------------------
// Inventory Tracker - frontend logic
// -------------------------------------------------------------------------

const els = {
  name:     document.getElementById("name"),
  sku:      document.getElementById("sku"),
  quantity: document.getElementById("quantity"),
  location: document.getElementById("location"),
  threshold:document.getElementById("threshold"),
  addBtn:   document.getElementById("add-btn"),
  formMsg:  document.getElementById("form-msg"),
  search:   document.getElementById("search"),
  products: document.getElementById("products"),
  empty:    document.getElementById("empty"),
  movements:document.getElementById("movements"),
};

// Client-side state
let lastProducts = [];
let sortState = { col: "name", dir: "asc" };

// --- Helpers --------------------------------------------------------------

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function showFormMsg(text, type) {
  els.formMsg.textContent = text;
  els.formMsg.className = "msg " + (type || "");
  if (type === "ok") {
    setTimeout(() => {
      els.formMsg.textContent = "";
      els.formMsg.className = "msg";
    }, 2500);
  }
}

function esc(str) {
  return String(str).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function getAdjustAmount(id) {
  const input = els.products.querySelector(`.qty-input[data-id="${id}"]`);
  return Math.max(1, parseInt(input?.value) || 1);
}

// --- Sorting --------------------------------------------------------------

function sortedProducts(products) {
  const { col, dir } = sortState;
  return [...products].sort((a, b) => {
    let av = a[col] ?? "";
    let bv = b[col] ?? "";
    if (typeof av === "string") av = av.toLowerCase();
    if (typeof bv === "string") bv = bv.toLowerCase();
    if (av < bv) return dir === "asc" ? -1 : 1;
    if (av > bv) return dir === "asc" ? 1 : -1;
    return 0;
  });
}

function updateSortHeaders() {
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    const icon = th.querySelector(".sort-icon");
    if (!icon) return;
    if (th.dataset.sort === sortState.col) {
      icon.textContent = sortState.dir === "asc" ? "↑" : "↓";
      th.classList.add("sort-active");
    } else {
      icon.textContent = "";
      th.classList.remove("sort-active");
    }
  });
}

// --- Rendering ------------------------------------------------------------

function renderProducts(products) {
  lastProducts = products;
  const list = sortedProducts(products);
  updateSortHeaders();

  els.products.innerHTML = "";
  if (list.length === 0) {
    els.empty.classList.remove("hidden");
    return;
  }
  els.empty.classList.add("hidden");

  for (const p of list) {
    const tr = document.createElement("tr");
    if (p.low_stock) tr.classList.add("low");
    tr.innerHTML = `
      <td>${esc(p.name)}${p.low_stock ? '<span class="low-tag">LOW</span>' : ""}</td>
      <td class="muted-text">${esc(p.sku)}</td>
      <td>${esc(p.location) || "&mdash;"}</td>
      <td class="qty-cell"><span class="qty-badge">${p.quantity}</span></td>
      <td>
        <div class="adjust">
          <button class="btn-step" data-action="out" data-id="${p.id}" title="Stock out">−</button>
          <input type="number" class="qty-input" value="1" min="1" data-id="${p.id}" />
          <button class="btn-step" data-action="in" data-id="${p.id}" title="Stock in">+</button>
        </div>
      </td>
      <td class="actions-cell">
        <button class="btn-link" data-action="edit" data-id="${p.id}">Edit</button>
        <button class="btn-link btn-link--danger" data-action="delete" data-id="${p.id}">Delete</button>
      </td>
    `;
    els.products.appendChild(tr);
  }
}

function renderEditRow(p) {
  const tr = document.createElement("tr");
  tr.classList.add("editing");
  tr.innerHTML = `
    <td><input type="text" class="edit-input" data-field="name" value="${esc(p.name)}" /></td>
    <td class="muted-text">${esc(p.sku)}</td>
    <td><input type="text" class="edit-input" data-field="location" value="${esc(p.location)}" placeholder="—" /></td>
    <td class="qty-cell">
      <span class="qty-badge">${p.quantity}</span>
      <div class="threshold-edit">
        alert at <input type="number" class="edit-input edit-input--tiny" data-field="threshold" value="${p.low_stock_threshold}" min="0" />
      </div>
    </td>
    <td></td>
    <td class="actions-cell">
      <button class="btn-link btn-link--ok" data-action="save" data-id="${p.id}">Save</button>
      <button class="btn-link" data-action="cancel" data-id="${p.id}">Cancel</button>
    </td>
  `;
  return tr;
}

function renderMovements(movements) {
  els.movements.innerHTML = "";
  if (movements.length === 0) {
    els.movements.innerHTML = '<li><span class="when">No activity yet.</span></li>';
    return;
  }
  for (const m of movements) {
    const sign = m.delta > 0 ? "+" : "";
    const cls  = m.delta > 0 ? "delta-pos" : "delta-neg";
    const reason = m.reason ? ` &middot; ${esc(m.reason)}` : "";
    const li = document.createElement("li");
    li.innerHTML = `
      <span>${esc(m.product_name)} <span class="${cls}">${sign}${m.delta}</span>${reason}</span>
      <span class="when">${esc(m.created_at)}</span>
    `;
    els.movements.appendChild(li);
  }
}

// --- Stats ----------------------------------------------------------------

async function loadStats() {
  try {
    const s = await api("/api/stats");
    document.getElementById("stat-total").textContent = s.total_products;
    document.getElementById("stat-units").textContent = s.total_units.toLocaleString();
    const lowEl   = document.getElementById("stat-low");
    const lowTile = document.getElementById("stat-low-tile");
    lowEl.textContent = s.low_stock_count;
    lowTile.classList.toggle("stat-tile--warn", s.low_stock_count > 0);
  } catch (err) {
    console.error(err);
  }
}

// --- Data loading ---------------------------------------------------------

async function loadProducts() {
  const q = els.search.value.trim();
  const url = q ? `/api/products?q=${encodeURIComponent(q)}` : "/api/products";
  try {
    renderProducts(await api(url));
  } catch (err) {
    console.error(err);
  }
}

async function loadMovements() {
  try {
    renderMovements(await api("/api/movements"));
  } catch (err) {
    console.error(err);
  }
}

function refresh() {
  loadProducts();
  loadMovements();
  loadStats();
}

// --- Actions --------------------------------------------------------------

async function addProduct() {
  const payload = {
    name:               els.name.value,
    sku:                els.sku.value,
    quantity:           els.quantity.value,
    location:           els.location.value,
    low_stock_threshold:els.threshold.value,
  };
  try {
    await api("/api/products", { method: "POST", body: JSON.stringify(payload) });
    showFormMsg("Product added.", "ok");
    els.name.value     = "";
    els.sku.value      = "";
    els.quantity.value = "0";
    els.location.value = "";
    els.threshold.value= "5";
    refresh();
  } catch (err) {
    showFormMsg(err.message, "error");
  }
}

async function adjustStock(id, delta) {
  const reason = delta > 0 ? "stock in" : "stock out";
  try {
    await api(`/api/products/${id}/adjust`, {
      method: "POST",
      body: JSON.stringify({ delta, reason }),
    });
    refresh();
  } catch (err) {
    showFormMsg(err.message, "error");
  }
}

async function deleteProduct(id) {
  if (!confirm("Delete this product?")) return;
  try {
    await api(`/api/products/${id}`, { method: "DELETE" });
    refresh();
  } catch (err) {
    showFormMsg(err.message, "error");
  }
}

function startEdit(id) {
  const p = lastProducts.find((p) => p.id === id);
  if (!p) return;
  const btn = els.products.querySelector(`button[data-action="edit"][data-id="${id}"]`);
  if (!btn) return;
  btn.closest("tr").replaceWith(renderEditRow(p));
  els.products.querySelector('tr.editing [data-field="name"]')?.focus();
}

async function saveEdit(id) {
  const tr = els.products.querySelector("tr.editing");
  if (!tr) return;
  const name      = tr.querySelector('[data-field="name"]').value.trim();
  const location  = tr.querySelector('[data-field="location"]').value.trim();
  const threshold = parseInt(tr.querySelector('[data-field="threshold"]').value) || 0;
  if (!name) { showFormMsg("Name cannot be empty.", "error"); return; }
  try {
    await api(`/api/products/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name, location, low_stock_threshold: threshold }),
    });
    refresh();
  } catch (err) {
    showFormMsg(err.message, "error");
  }
}

// --- Wiring ---------------------------------------------------------------

els.addBtn.addEventListener("click", addProduct);

let searchTimer;
els.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadProducts, 200);
});

document.querySelectorAll("th[data-sort]").forEach((th) => {
  th.addEventListener("click", () => {
    const col = th.dataset.sort;
    if (sortState.col === col) {
      sortState.dir = sortState.dir === "asc" ? "desc" : "asc";
    } else {
      sortState.col = col;
      sortState.dir = "asc";
    }
    renderProducts(lastProducts);
  });
});

els.products.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const id     = Number(btn.dataset.id);
  const action = btn.dataset.action;
  if      (action === "in")     adjustStock(id, getAdjustAmount(id));
  else if (action === "out")    adjustStock(id, -getAdjustAmount(id));
  else if (action === "delete") deleteProduct(id);
  else if (action === "edit")   startEdit(id);
  else if (action === "save")   saveEdit(id);
  else if (action === "cancel") refresh();
});

// Initial load
refresh();
