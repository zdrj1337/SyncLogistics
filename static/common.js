// -------------------------------------------------------------------------
// Depot — shared utilities
// -------------------------------------------------------------------------

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function esc(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function showToast(message, type = "ok") {
  const t = document.createElement("div");
  t.className = `toast toast--${type}`;
  t.textContent = message;
  document.body.appendChild(t);
  requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add("show")));
  setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 250); }, 3200);
}

function formatCurrency(val) {
  return Number(val ?? 0).toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " RON";
}

function formatNum(val) {
  return Number(val ?? 0).toLocaleString("ro-RO");
}

function debounce(fn, ms) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ---- Live sidebar badges -------------------------------------------------
async function loadSidebarBadges() {
  try {
    const s = await api("/api/stats");

    const lowEl   = document.getElementById("badge-low-stock");
    const pendEl  = document.getElementById("badge-pending");

    if (lowEl) {
      lowEl.textContent = s.low_stock_count;
      lowEl.classList.toggle("hidden", s.low_stock_count === 0);
    }
    if (pendEl) {
      pendEl.textContent = s.pending_orders;
      pendEl.classList.toggle("hidden", s.pending_orders === 0);
    }
    const outboundEl = document.getElementById("badge-outbound");
    if (outboundEl) {
      outboundEl.textContent = s.outbound_pending;
      outboundEl.classList.toggle("hidden", s.outbound_pending === 0);
    }
  } catch { /* non-critical */ }
}

// ---- Generic modal -------------------------------------------------------
const modal = {
  el: null,
  init() {
    this.el = document.getElementById("modal");
    this.el.querySelector(".modal-overlay").addEventListener("click", () => this.close());
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") this.close(); });
  },
  open(title, bodyHTML, { footer = "", lg = false, onOpen } = {}) {
    document.getElementById("modal-title").textContent = title;
    document.getElementById("modal-body").innerHTML   = bodyHTML;
    document.getElementById("modal-footer").innerHTML = footer;
    this.el.querySelector(".modal-box").classList.toggle("modal-box--lg", lg);
    this.el.classList.add("open");
    if (onOpen) setTimeout(onOpen, 30);
  },
  close() { if (this.el) this.el.classList.remove("open"); },
};

// ---- Confirm dialog ------------------------------------------------------
const CDLG_ICONS = {
  danger: `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
  warn:   `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  info:   `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
};

function confirmDialog(title, message, onConfirm, { confirmText = "Confirm", type = "danger" } = {}) {
  const dlg       = document.getElementById("confirm-dlg");
  const iconEl    = document.getElementById("confirm-dlg-icon");
  const titleEl   = document.getElementById("confirm-dlg-title");
  const msgEl     = document.getElementById("confirm-dlg-msg");
  const okBtn     = document.getElementById("confirm-dlg-ok");
  const cancelBtn = document.getElementById("confirm-dlg-cancel");

  iconEl.className = `confirm-dlg-icon confirm-dlg-icon--${type}`;
  iconEl.innerHTML = CDLG_ICONS[type] || CDLG_ICONS.warn;
  titleEl.textContent = title;
  msgEl.textContent   = message;
  okBtn.textContent   = confirmText;
  okBtn.className     = `btn ${type === "danger" ? "btn-danger" : type === "warn" ? "btn-primary" : "btn-primary"}`;

  dlg.classList.add("open");

  function cleanup() {
    dlg.classList.remove("open");
    okBtn.removeEventListener("click", handleOk);
    cancelBtn.removeEventListener("click", cleanup);
    dlg.removeEventListener("click", handleOverlay);
    document.removeEventListener("keydown", handleKey);
  }
  function handleOk() { cleanup(); onConfirm(); }
  function handleOverlay(e) { if (e.target === dlg || e.target.classList.contains("confirm-dlg-overlay")) cleanup(); }
  function handleKey(e) { if (e.key === "Escape") cleanup(); }

  okBtn.addEventListener("click", handleOk);
  cancelBtn.addEventListener("click", cleanup);
  dlg.addEventListener("click", handleOverlay);
  document.addEventListener("keydown", handleKey);
}

// ---- Sort helper ---------------------------------------------------------
function sortRows(rows, { col, dir }) {
  if (!col) return rows;
  return [...rows].sort((a, b) => {
    let av = a[col] ?? "", bv = b[col] ?? "";
    if (typeof av === "string") av = av.toLowerCase();
    if (typeof bv === "string") bv = bv.toLowerCase();
    if (av < bv) return dir === "asc" ? -1 : 1;
    if (av > bv) return dir === "asc" ? 1 : -1;
    return 0;
  });
}

function makeSortable(getRows, renderFn) {
  let state = { col: null, dir: "asc" };
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.classList.add("sortable");
    const icon = document.createElement("span");
    icon.className = "sort-icon";
    th.appendChild(icon);
    th.addEventListener("click", () => {
      const col = th.dataset.sort;
      state = { col, dir: state.col === col && state.dir === "asc" ? "desc" : "asc" };
      document.querySelectorAll("th[data-sort]").forEach((h) => {
        h.classList.remove("sort-active");
        h.querySelector(".sort-icon").textContent = "";
      });
      th.classList.add("sort-active");
      icon.textContent = state.dir === "asc" ? " ↑" : " ↓";
      renderFn(sortRows(getRows(), state));
    });
  });
  return (rows) => sortRows(rows, state);
}

// ---- Status badge --------------------------------------------------------
function statusBadge(status) {
  const labels = { ordered: "Ordered", partial: "Partial", received: "Received", cancelled: "Cancelled" };
  return `<span class="badge status-${esc(status)}">${esc(labels[status] || status)}</span>`;
}

// ---- Category dot --------------------------------------------------------
function catBadge(name, color) {
  if (!name) return '<span class="muted-text">—</span>';
  return `<span style="display:inline-flex;align-items:center;gap:4px">
    <span class="cat-dot" style="background:${esc(color || "#999")}"></span>${esc(name)}
  </span>`;
}

// ---- Enter-to-submit on modal --------------------------------------------
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.target.tagName === "TEXTAREA" || e.target.tagName === "BUTTON") return;
  const m = document.getElementById("modal");
  if (!m || !m.classList.contains("open")) return;
  const primaryBtn = m.querySelector(".modal-footer .btn-primary");
  if (primaryBtn) primaryBtn.click();
});

// ---- Mobile sidebar toggle -----------------------------------------------
function initMobileNav() {
  const btn     = document.getElementById("hamburgerBtn");
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("mobileNavOverlay");
  if (!btn || !sidebar || !overlay) return;

  function openNav() {
    sidebar.classList.add("mobile-open");
    overlay.classList.add("active");
    btn.classList.add("open");
    document.body.style.overflow = "hidden";
  }
  function closeNav() {
    sidebar.classList.remove("mobile-open");
    overlay.classList.remove("active");
    btn.classList.remove("open");
    document.body.style.overflow = "";
  }

  btn.addEventListener("click", () =>
    sidebar.classList.contains("mobile-open") ? closeNav() : openNav()
  );
  overlay.addEventListener("click", closeNav);
  sidebar.querySelectorAll(".nav-link").forEach((a) =>
    a.addEventListener("click", closeNav)
  );
}

// ---- Date pickers --------------------------------------------------------
function initDatePickers(root = document) {
  if (typeof flatpickr === "undefined") return;
  root.querySelectorAll('input[type="date"]').forEach(el => {
    if (el._flatpickr) return;
    flatpickr(el, {
      dateFormat: "Y-m-d",
      allowInput: true,
      disableMobile: true,
    });
  });
}

function clearDateInput(idOrEl) {
  const el = typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
  if (!el) return;
  if (el._flatpickr) el._flatpickr.clear();
  else el.value = "";
}

// ---- Init ----------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("modal")) {
    modal.init();
    const _origOpen = modal.open.bind(modal);
    modal.open = function(title, bodyHTML, options) {
      _origOpen(title, bodyHTML, options);
      setTimeout(() => initDatePickers(document.getElementById("modal-body")), 40);
    };
  }
  loadSidebarBadges();
  initMobileNav();
  initDatePickers();
});
