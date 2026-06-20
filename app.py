"""
Warehouse Manager — Flask + SQLite
Full-featured warehouse stock management system.
"""

import csv
import io
import os
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, render_template, g, Response

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")
app = Flask(__name__)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL UNIQUE,
            color TEXT    NOT NULL DEFAULT '#6b7682'
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            contact_name TEXT DEFAULT '',
            email        TEXT DEFAULT '',
            phone        TEXT DEFAULT '',
            notes        TEXT DEFAULT '',
            created_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            sku                 TEXT    NOT NULL UNIQUE,
            quantity            INTEGER NOT NULL DEFAULT 0,
            location            TEXT    DEFAULT '',
            low_stock_threshold INTEGER NOT NULL DEFAULT 5,
            created_at          TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            reference     TEXT    NOT NULL UNIQUE,
            supplier_id   INTEGER REFERENCES suppliers(id),
            status        TEXT    NOT NULL DEFAULT 'ordered',
            notes         TEXT    DEFAULT '',
            expected_date TEXT    DEFAULT '',
            created_at    TEXT    NOT NULL,
            received_at   TEXT    DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id          INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
            product_id        INTEGER NOT NULL REFERENCES products(id),
            quantity_ordered  INTEGER NOT NULL DEFAULT 0,
            quantity_received INTEGER NOT NULL DEFAULT 0,
            unit_price        REAL    DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS movements (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER NOT NULL,
            product_name TEXT    NOT NULL,
            delta        INTEGER NOT NULL,
            type         TEXT    NOT NULL DEFAULT 'adjustment',
            reference    TEXT    DEFAULT '',
            reason       TEXT    DEFAULT '',
            created_at   TEXT    NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS customers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            contact_name TEXT DEFAULT '',
            email        TEXT DEFAULT '',
            phone        TEXT DEFAULT '',
            address      TEXT DEFAULT '',
            notes        TEXT DEFAULT '',
            created_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS work_instructions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            code              TEXT NOT NULL UNIQUE,
            title             TEXT NOT NULL,
            description       TEXT DEFAULT '',
            estimated_minutes INTEGER DEFAULT 0,
            active            INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS outbound_orders (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            reference        TEXT NOT NULL UNIQUE,
            customer_id      INTEGER REFERENCES customers(id),
            status           TEXT NOT NULL DEFAULT 'pending',
            delivery_address TEXT DEFAULT '',
            notes            TEXT DEFAULT '',
            required_date    TEXT DEFAULT '',
            created_at       TEXT NOT NULL,
            shipped_at       TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS outbound_order_items (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id         INTEGER NOT NULL REFERENCES outbound_orders(id) ON DELETE CASCADE,
            product_id       INTEGER NOT NULL REFERENCES products(id),
            quantity_ordered INTEGER NOT NULL DEFAULT 0,
            quantity_shipped INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS outbound_item_instructions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            order_item_id       INTEGER NOT NULL REFERENCES outbound_order_items(id) ON DELETE CASCADE,
            work_instruction_id INTEGER NOT NULL REFERENCES work_instructions(id),
            completed           INTEGER NOT NULL DEFAULT 0,
            completed_at        TEXT DEFAULT ''
        );
    """)

    # Migrate products — add new columns if missing
    existing = {r[1] for r in db.execute("PRAGMA table_info(products)").fetchall()}
    for col, defn in [
        ("category_id",      "INTEGER REFERENCES categories(id)"),
        ("supplier_id",      "INTEGER REFERENCES suppliers(id)"),
        ("unit",             "TEXT DEFAULT 'pcs'"),
        ("cost_price",       "REAL DEFAULT 0"),
        ("reorder_quantity", "INTEGER DEFAULT 10"),
        ("notes",            "TEXT DEFAULT ''"),
        ("barcode",          "TEXT DEFAULT ''"),
    ]:
        if col not in existing:
            db.execute(f"ALTER TABLE products ADD COLUMN {col} {defn}")

    # Migrate movements — add new columns if missing
    existing_m = {r[1] for r in db.execute("PRAGMA table_info(movements)").fetchall()}
    for col, defn in [
        ("type",      "TEXT DEFAULT 'adjustment'"),
        ("reference", "TEXT DEFAULT ''"),
    ]:
        if col not in existing_m:
            db.execute(f"ALTER TABLE movements ADD COLUMN {col} {defn}")

    db.commit()
    db.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def product_to_dict(row):
    d = dict(row)
    d["low_stock"]    = d["quantity"] <= d["low_stock_threshold"]
    d["stock_value"]  = round(d["quantity"] * (d.get("cost_price") or 0), 2)
    d["unit"]         = d.get("unit") or "pcs"
    d["cost_price"]   = d.get("cost_price") or 0
    d["reorder_quantity"] = d.get("reorder_quantity") or 10
    return d


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.get("/")
def dashboard():
    return render_template("dashboard.html")

@app.get("/products")
def products_page():
    return render_template("products.html")

@app.get("/suppliers")
def suppliers_page():
    return render_template("suppliers.html")

@app.get("/orders")
def orders_page():
    return render_template("orders.html")

@app.get("/orders/<int:order_id>")
def order_detail_page(order_id):
    return render_template("order_detail.html", order_id=order_id)

@app.get("/movements")
def movements_page():
    return render_template("movements.html")

@app.get("/reports")
def reports_page():
    return render_template("reports.html")

@app.get("/customers")
def customers_page():
    return render_template("customers.html")

@app.get("/outbound")
def outbound_page():
    return render_template("outbound.html")

@app.get("/outbound/<int:order_id>")
def outbound_detail_page(order_id):
    return render_template("outbound_detail.html", order_id=order_id)

@app.get("/work-instructions")
def work_instructions_page():
    return render_template("work_instructions.html")


# ---------------------------------------------------------------------------
# Categories API
# ---------------------------------------------------------------------------
@app.get("/api/categories")
def list_categories():
    db = get_db()
    rows = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/categories")
def add_category():
    data  = request.get_json(silent=True) or {}
    name  = (data.get("name") or "").strip()
    color = (data.get("color") or "#6b7682").strip()
    if not name:
        return jsonify({"error": "Name required."}), 400
    db = get_db()
    try:
        cur = db.execute("INSERT INTO categories (name, color) VALUES (?,?)", (name, color))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Category '{name}' already exists."}), 409
    return jsonify(dict(db.execute("SELECT * FROM categories WHERE id=?", (cur.lastrowid,)).fetchone())), 201

@app.patch("/api/categories/<int:cat_id>")
def update_category(cat_id):
    data = request.get_json(silent=True) or {}
    db   = get_db()
    row  = db.execute("SELECT * FROM categories WHERE id=?", (cat_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    name  = (data.get("name") or row["name"]).strip()
    color = (data.get("color") or row["color"]).strip()
    db.execute("UPDATE categories SET name=?, color=? WHERE id=?", (name, color, cat_id))
    db.commit()
    return jsonify(dict(db.execute("SELECT * FROM categories WHERE id=?", (cat_id,)).fetchone()))

@app.delete("/api/categories/<int:cat_id>")
def delete_category(cat_id):
    db = get_db()
    db.execute("UPDATE products SET category_id=NULL WHERE category_id=?", (cat_id,))
    db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    db.commit()
    return jsonify({"deleted": cat_id})


# ---------------------------------------------------------------------------
# Suppliers API
# ---------------------------------------------------------------------------
@app.get("/api/suppliers")
def list_suppliers():
    db   = get_db()
    rows = db.execute("""
        SELECT s.*, COUNT(p.id) as product_count
        FROM suppliers s
        LEFT JOIN products p ON p.supplier_id = s.id
        GROUP BY s.id ORDER BY s.name
    """).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/suppliers")
def add_supplier():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name required."}), 400
    db  = get_db()
    cur = db.execute(
        "INSERT INTO suppliers (name, contact_name, email, phone, notes, created_at) VALUES (?,?,?,?,?,?)",
        (name,
         (data.get("contact_name") or "").strip(),
         (data.get("email") or "").strip(),
         (data.get("phone") or "").strip(),
         (data.get("notes") or "").strip(),
         now()),
    )
    db.commit()
    return jsonify(dict(db.execute(
        "SELECT *, 0 as product_count FROM suppliers WHERE id=?", (cur.lastrowid,)
    ).fetchone())), 201

@app.patch("/api/suppliers/<int:sup_id>")
def update_supplier(sup_id):
    data = request.get_json(silent=True) or {}
    db   = get_db()
    row  = db.execute("SELECT * FROM suppliers WHERE id=?", (sup_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    db.execute(
        "UPDATE suppliers SET name=?, contact_name=?, email=?, phone=?, notes=? WHERE id=?",
        ((data.get("name") or row["name"]).strip(),
         data.get("contact_name", row["contact_name"]),
         data.get("email", row["email"]),
         data.get("phone", row["phone"]),
         data.get("notes", row["notes"]),
         sup_id),
    )
    db.commit()
    return jsonify(dict(db.execute(
        "SELECT *, 0 as product_count FROM suppliers WHERE id=?", (sup_id,)
    ).fetchone()))

@app.delete("/api/suppliers/<int:sup_id>")
def delete_supplier(sup_id):
    db = get_db()
    db.execute("UPDATE products SET supplier_id=NULL WHERE supplier_id=?", (sup_id,))
    db.execute("DELETE FROM suppliers WHERE id=?", (sup_id,))
    db.commit()
    return jsonify({"deleted": sup_id})


# ---------------------------------------------------------------------------
# Products API
# ---------------------------------------------------------------------------
def _fetch_product(db, product_id):
    return db.execute("""
        SELECT p.*, c.name as category_name, c.color as category_color,
               s.name as supplier_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers  s ON s.id = p.supplier_id
        WHERE p.id = ?
    """, (product_id,)).fetchone()


@app.get("/api/products")
def list_products():
    q       = request.args.get("q", "").strip()
    cat     = request.args.get("category", "").strip()
    low     = request.args.get("low_stock", "").strip()
    sup     = request.args.get("supplier", "").strip()

    sql    = """
        SELECT p.*, c.name as category_name, c.color as category_color,
               s.name as supplier_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers  s ON s.id = p.supplier_id
        WHERE 1=1
    """
    params = []
    if q:
        like = f"%{q}%"
        sql += " AND (p.name LIKE ? OR p.sku LIKE ? OR p.barcode LIKE ?)"
        params.extend([like, like, like])
    if cat:
        sql += " AND p.category_id = ?"
        params.append(cat)
    if sup:
        sql += " AND p.supplier_id = ?"
        params.append(sup)
    if low == "1":
        sql += " AND p.quantity <= p.low_stock_threshold"
    sql += " ORDER BY p.name"

    db   = get_db()
    rows = db.execute(sql, params).fetchall()
    return jsonify([product_to_dict(r) for r in rows])


@app.post("/api/products")
def add_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    sku  = (data.get("sku") or "").strip()
    if not name or not sku:
        return jsonify({"error": "Name and SKU are required."}), 400
    try:
        quantity  = int(data.get("quantity", 0))
        threshold = int(data.get("low_stock_threshold", 5))
        reorder   = int(data.get("reorder_quantity", 10))
        cost      = float(data.get("cost_price", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Numeric fields must be numbers."}), 400
    if quantity < 0 or threshold < 0 or cost < 0:
        return jsonify({"error": "Values cannot be negative."}), 400

    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO products
               (name, sku, quantity, location, low_stock_threshold, reorder_quantity,
                category_id, supplier_id, unit, cost_price, notes, barcode, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, sku, quantity,
             (data.get("location") or "").strip(),
             threshold, reorder,
             data.get("category_id") or None,
             data.get("supplier_id") or None,
             (data.get("unit") or "pcs").strip(),
             cost,
             (data.get("notes") or "").strip(),
             (data.get("barcode") or "").strip(),
             now()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": f"SKU '{sku}' already exists."}), 409

    if quantity > 0:
        db.execute(
            "INSERT INTO movements (product_id, product_name, delta, type, reason, created_at)"
            " VALUES (?,?,?,'purchase','initial stock',?)",
            (cur.lastrowid, name, quantity, now()),
        )
        db.commit()

    return jsonify(product_to_dict(_fetch_product(db, cur.lastrowid))), 201


@app.patch("/api/products/<int:product_id>")
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    db   = get_db()
    row  = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404

    name = (data.get("name") or row["name"]).strip()
    if not name:
        return jsonify({"error": "Name cannot be empty."}), 400
    try:
        threshold = int(data.get("low_stock_threshold", row["low_stock_threshold"]))
        reorder   = int(data.get("reorder_quantity", row["reorder_quantity"] or 10))
        cost      = float(data.get("cost_price", row["cost_price"] or 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Numeric fields must be numbers."}), 400

    db.execute(
        """UPDATE products SET name=?, location=?, low_stock_threshold=?, reorder_quantity=?,
           category_id=?, supplier_id=?, unit=?, cost_price=?, notes=?, barcode=?
           WHERE id=?""",
        (name,
         data.get("location", row["location"]),
         threshold, reorder,
         data.get("category_id") or None,
         data.get("supplier_id") or None,
         data.get("unit", row["unit"] or "pcs"),
         cost,
         data.get("notes", row["notes"] or ""),
         data.get("barcode", row["barcode"] or ""),
         product_id),
    )
    db.commit()
    return jsonify(product_to_dict(_fetch_product(db, product_id)))


@app.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    db = get_db()
    if not db.execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone():
        return jsonify({"error": "Not found."}), 404
    db.execute("DELETE FROM movements WHERE product_id=?", (product_id,))
    db.execute("DELETE FROM products WHERE id=?", (product_id,))
    db.commit()
    return jsonify({"deleted": product_id})


@app.post("/api/products/<int:product_id>/adjust")
def adjust_stock(product_id):
    data      = request.get_json(silent=True) or {}
    reason    = (data.get("reason") or "").strip()
    mov_type  = (data.get("type") or "adjustment").strip()
    reference = (data.get("reference") or "").strip()
    try:
        delta = int(data.get("delta"))
    except (TypeError, ValueError):
        return jsonify({"error": "delta must be a number."}), 400

    db  = get_db()
    row = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404

    new_qty = row["quantity"] + delta
    if new_qty < 0:
        return jsonify({"error": f"Insufficient stock. Current: {row['quantity']}, requested: {delta}."}), 400

    db.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, product_id))
    db.execute(
        "INSERT INTO movements (product_id, product_name, delta, type, reference, reason, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (product_id, row["name"], delta, mov_type, reference, reason, now()),
    )
    db.commit()
    return jsonify(product_to_dict(_fetch_product(db, product_id)))


# ---------------------------------------------------------------------------
# Purchase Orders API
# ---------------------------------------------------------------------------
@app.get("/api/orders")
def list_orders():
    db   = get_db()
    rows = db.execute("""
        SELECT o.*, s.name as supplier_name,
               COUNT(i.id) as item_count,
               COALESCE(SUM(i.quantity_ordered * i.unit_price), 0) as total_value
        FROM purchase_orders o
        LEFT JOIN suppliers s ON s.id = o.supplier_id
        LEFT JOIN purchase_order_items i ON i.order_id = o.id
        GROUP BY o.id ORDER BY o.id DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/orders")
def create_order():
    data          = request.get_json(silent=True) or {}
    supplier_id   = data.get("supplier_id") or None
    notes         = (data.get("notes") or "").strip()
    expected_date = (data.get("expected_date") or "").strip()
    items         = data.get("items") or []
    if not items:
        return jsonify({"error": "At least one item required."}), 400

    db    = get_db()
    count = db.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0] + 1
    ref   = f"PO-{datetime.now().year}-{count:04d}"

    cur = db.execute(
        "INSERT INTO purchase_orders (reference, supplier_id, status, notes, expected_date, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (ref, supplier_id, "ordered", notes, expected_date, now()),
    )
    order_id = cur.lastrowid

    for item in items:
        pid   = item.get("product_id")
        qty   = int(item.get("quantity_ordered", 0))
        price = float(item.get("unit_price", 0))
        if pid and qty > 0:
            db.execute(
                "INSERT INTO purchase_order_items (order_id, product_id, quantity_ordered, unit_price)"
                " VALUES (?,?,?,?)",
                (order_id, pid, qty, price),
            )
    db.commit()
    return jsonify({"id": order_id, "reference": ref}), 201


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    db = get_db()
    o  = db.execute("""
        SELECT o.*, s.name as supplier_name, s.email as supplier_email, s.phone as supplier_phone
        FROM purchase_orders o
        LEFT JOIN suppliers s ON s.id = o.supplier_id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    if not o:
        return jsonify({"error": "Not found."}), 404

    items = db.execute("""
        SELECT i.*, p.name as product_name, p.sku, p.unit
        FROM purchase_order_items i
        JOIN products p ON p.id = i.product_id
        WHERE i.order_id=? ORDER BY p.name
    """, (order_id,)).fetchall()

    result         = dict(o)
    result["items"] = [dict(i) for i in items]
    return jsonify(result)


@app.post("/api/orders/<int:order_id>/receive")
def receive_order(order_id):
    data           = request.get_json(silent=True) or {}
    received_items = data.get("items") or []

    db    = get_db()
    order = db.execute("SELECT * FROM purchase_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return jsonify({"error": "Not found."}), 404
    if order["status"] == "received":
        return jsonify({"error": "Order already fully received."}), 400

    for item in received_items:
        item_id = item.get("item_id")
        qty     = int(item.get("quantity_received", 0))
        if qty <= 0:
            continue
        row = db.execute(
            "SELECT i.*, p.name as product_name FROM purchase_order_items i"
            " JOIN products p ON p.id = i.product_id"
            " WHERE i.id=? AND i.order_id=?",
            (item_id, order_id),
        ).fetchone()
        if not row:
            continue
        db.execute(
            "UPDATE purchase_order_items SET quantity_received=quantity_received+? WHERE id=?",
            (qty, item_id),
        )
        db.execute("UPDATE products SET quantity=quantity+? WHERE id=?", (qty, row["product_id"]))
        db.execute(
            "INSERT INTO movements (product_id, product_name, delta, type, reference, reason, created_at)"
            " VALUES (?,?,?,'purchase',?,?,?)",
            (row["product_id"], row["product_name"], qty, order["reference"], "goods received", now()),
        )

    all_items = db.execute(
        "SELECT quantity_ordered, quantity_received FROM purchase_order_items WHERE order_id=?",
        (order_id,),
    ).fetchall()
    all_done = all(r["quantity_received"] >= r["quantity_ordered"] for r in all_items)
    any_done = any(r["quantity_received"] > 0 for r in all_items)
    status   = "received" if all_done else ("partial" if any_done else order["status"])

    db.execute(
        "UPDATE purchase_orders SET status=?, received_at=? WHERE id=?",
        (status, now() if all_done else order["received_at"], order_id),
    )
    db.commit()
    return jsonify({"status": status})


@app.patch("/api/orders/<int:order_id>")
def update_order_status(order_id):
    data   = request.get_json(silent=True) or {}
    db     = get_db()
    order  = db.execute("SELECT * FROM purchase_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return jsonify({"error": "Not found."}), 404
    status = data.get("status", order["status"])
    db.execute("UPDATE purchase_orders SET status=? WHERE id=?", (status, order_id))
    db.commit()
    return jsonify({"status": status})


# ---------------------------------------------------------------------------
# Movements API
# ---------------------------------------------------------------------------
@app.get("/api/movements")
def list_movements():
    limit      = min(int(request.args.get("limit", 100)), 500)
    product_id = request.args.get("product_id", "").strip()
    mov_type   = request.args.get("type", "").strip()
    date_from  = request.args.get("from", "").strip()
    date_to    = request.args.get("to", "").strip()

    sql    = "SELECT * FROM movements WHERE 1=1"
    params = []
    if product_id:
        sql += " AND product_id=?"
        params.append(product_id)
    if mov_type:
        sql += " AND type=?"
        params.append(mov_type)
    if date_from:
        sql += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND created_at <= ?"
        params.append(date_to + " 23:59")
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    db   = get_db()
    rows = db.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Customers API
# ---------------------------------------------------------------------------
@app.get("/api/customers")
def list_customers():
    db = get_db()
    rows = db.execute("""
        SELECT c.*, COUNT(o.id) as order_count
        FROM customers c
        LEFT JOIN outbound_orders o ON o.customer_id = c.id
        GROUP BY c.id ORDER BY c.name
    """).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/customers")
def add_customer():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name required."}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO customers (name, contact_name, email, phone, address, notes, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (name,
             (data.get("contact_name") or "").strip(),
             (data.get("email") or "").strip(),
             (data.get("phone") or "").strip(),
             (data.get("address") or "").strip(),
             (data.get("notes") or "").strip(),
             now()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Customer '{name}' already exists."}), 409
    return jsonify(dict(db.execute(
        "SELECT *, 0 as order_count FROM customers WHERE id=?", (cur.lastrowid,)
    ).fetchone())), 201

@app.patch("/api/customers/<int:cid>")
def update_customer(cid):
    data = request.get_json(silent=True) or {}
    db   = get_db()
    row  = db.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    db.execute(
        "UPDATE customers SET name=?, contact_name=?, email=?, phone=?, address=?, notes=? WHERE id=?",
        ((data.get("name") or row["name"]).strip(),
         data.get("contact_name", row["contact_name"]),
         data.get("email",        row["email"]),
         data.get("phone",        row["phone"]),
         data.get("address",      row["address"]),
         data.get("notes",        row["notes"]),
         cid),
    )
    db.commit()
    return jsonify(dict(db.execute(
        "SELECT *, 0 as order_count FROM customers WHERE id=?", (cid,)
    ).fetchone()))

@app.delete("/api/customers/<int:cid>")
def delete_customer(cid):
    db = get_db()
    db.execute("DELETE FROM outbound_orders WHERE customer_id=?", (cid,))
    db.execute("DELETE FROM customers WHERE id=?", (cid,))
    db.commit()
    return jsonify({"deleted": cid})


# ---------------------------------------------------------------------------
# Work Instructions API
# ---------------------------------------------------------------------------
@app.get("/api/work-instructions")
def list_wi():
    db = get_db()
    rows = db.execute("SELECT * FROM work_instructions ORDER BY code").fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/work-instructions")
def add_wi():
    data  = request.get_json(silent=True) or {}
    code  = (data.get("code") or "").strip().upper()
    title = (data.get("title") or "").strip()
    if not code or not title:
        return jsonify({"error": "Code and title required."}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO work_instructions (code, title, description, estimated_minutes, active)"
            " VALUES (?,?,?,?,1)",
            (code, title,
             (data.get("description") or "").strip(),
             int(data.get("estimated_minutes") or 0)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Code '{code}' already exists."}), 409
    return jsonify(dict(db.execute(
        "SELECT * FROM work_instructions WHERE id=?", (cur.lastrowid,)
    ).fetchone())), 201

@app.patch("/api/work-instructions/<int:wi_id>")
def update_wi(wi_id):
    data = request.get_json(silent=True) or {}
    db   = get_db()
    row  = db.execute("SELECT * FROM work_instructions WHERE id=?", (wi_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    db.execute(
        "UPDATE work_instructions SET title=?, description=?, estimated_minutes=?, active=? WHERE id=?",
        ((data.get("title") or row["title"]).strip(),
         data.get("description",       row["description"]),
         int(data.get("estimated_minutes", row["estimated_minutes"])),
         1 if data.get("active", row["active"]) else 0,
         wi_id),
    )
    db.commit()
    return jsonify(dict(db.execute(
        "SELECT * FROM work_instructions WHERE id=?", (wi_id,)
    ).fetchone()))

@app.delete("/api/work-instructions/<int:wi_id>")
def delete_wi(wi_id):
    db = get_db()
    db.execute("DELETE FROM work_instructions WHERE id=?", (wi_id,))
    db.commit()
    return jsonify({"deleted": wi_id})


# ---------------------------------------------------------------------------
# Outbound Orders API
# ---------------------------------------------------------------------------
@app.get("/api/outbound")
def list_outbound():
    db   = get_db()
    rows = db.execute("""
        SELECT o.*, c.name as customer_name,
               COUNT(i.id) as item_count,
               COALESCE(SUM(i.quantity_ordered), 0) as total_units
        FROM outbound_orders o
        LEFT JOIN customers c ON c.id = o.customer_id
        LEFT JOIN outbound_order_items i ON i.order_id = o.id
        GROUP BY o.id ORDER BY o.id DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/outbound")
def create_outbound():
    data             = request.get_json(silent=True) or {}
    customer_id      = data.get("customer_id") or None
    delivery_address = (data.get("delivery_address") or "").strip()
    notes            = (data.get("notes") or "").strip()
    required_date    = (data.get("required_date") or "").strip()
    items            = data.get("items") or []
    if not items:
        return jsonify({"error": "At least one item required."}), 400

    db    = get_db()
    count = db.execute("SELECT COUNT(*) FROM outbound_orders").fetchone()[0] + 1
    ref   = f"OB-{datetime.now().year}-{count:04d}"

    cur = db.execute(
        "INSERT INTO outbound_orders"
        " (reference, customer_id, status, delivery_address, notes, required_date, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (ref, customer_id, "pending", delivery_address, notes, required_date, now()),
    )
    order_id = cur.lastrowid

    for item in items:
        pid = item.get("product_id")
        qty = int(item.get("quantity_ordered", 0))
        if not pid or qty <= 0:
            continue
        item_cur = db.execute(
            "INSERT INTO outbound_order_items (order_id, product_id, quantity_ordered)"
            " VALUES (?,?,?)",
            (order_id, pid, qty),
        )
        item_id = item_cur.lastrowid
        for wi_id in (item.get("wi_ids") or []):
            try:
                db.execute(
                    "INSERT INTO outbound_item_instructions (order_item_id, work_instruction_id)"
                    " VALUES (?,?)",
                    (item_id, int(wi_id)),
                )
            except Exception:
                pass

    db.commit()
    return jsonify({"id": order_id, "reference": ref}), 201


@app.get("/api/outbound/<int:order_id>")
def get_outbound(order_id):
    db = get_db()
    o  = db.execute("""
        SELECT o.*, c.name as customer_name, c.email as customer_email,
               c.phone as customer_phone, c.address as customer_address
        FROM outbound_orders o
        LEFT JOIN customers c ON c.id = o.customer_id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    if not o:
        return jsonify({"error": "Not found."}), 404

    items = db.execute("""
        SELECT i.*, p.name as product_name, p.sku, p.unit, p.quantity as stock_qty,
               p.location as product_location
        FROM outbound_order_items i
        JOIN products p ON p.id = i.product_id
        WHERE i.order_id=? ORDER BY p.name
    """, (order_id,)).fetchall()

    result         = dict(o)
    result["items"] = []
    for item in items:
        item_dict = dict(item)
        wi_rows   = db.execute("""
            SELECT ii.*, w.code, w.title, w.estimated_minutes, w.description
            FROM outbound_item_instructions ii
            JOIN work_instructions w ON w.id = ii.work_instruction_id
            WHERE ii.order_item_id = ? ORDER BY w.code
        """, (item_dict["id"],)).fetchall()
        item_dict["instructions"] = [dict(w) for w in wi_rows]
        result["items"].append(item_dict)
    return jsonify(result)


@app.patch("/api/outbound/<int:order_id>")
def update_outbound(order_id):
    data  = request.get_json(silent=True) or {}
    db    = get_db()
    order = db.execute("SELECT * FROM outbound_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return jsonify({"error": "Not found."}), 404
    status = data.get("status", order["status"])
    db.execute("UPDATE outbound_orders SET status=? WHERE id=?", (status, order_id))
    db.commit()
    return jsonify({"status": status})


@app.post("/api/outbound/<int:order_id>/process")
def process_outbound(order_id):
    db    = get_db()
    order = db.execute("SELECT * FROM outbound_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return jsonify({"error": "Not found."}), 404
    if order["status"] != "pending":
        return jsonify({"error": "Only pending orders can be started."}), 400
    db.execute("UPDATE outbound_orders SET status='processing' WHERE id=?", (order_id,))
    db.commit()
    return jsonify({"status": "processing"})


@app.post("/api/outbound/<int:order_id>/ship")
def ship_outbound(order_id):
    db    = get_db()
    order = db.execute("SELECT * FROM outbound_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return jsonify({"error": "Not found."}), 404
    if order["status"] == "shipped":
        return jsonify({"error": "Order already shipped."}), 400
    if order["status"] == "cancelled":
        return jsonify({"error": "Cannot ship a cancelled order."}), 400

    items = db.execute("""
        SELECT i.*, p.name as product_name, p.quantity as stock_qty
        FROM outbound_order_items i
        JOIN products p ON p.id = i.product_id
        WHERE i.order_id=?
    """, (order_id,)).fetchall()

    for item in items:
        remaining = item["quantity_ordered"] - item["quantity_shipped"]
        if remaining <= 0:
            continue
        if item["stock_qty"] < remaining:
            return jsonify({
                "error": f"Insufficient stock for '{item['product_name']}'."
                         f" Available: {item['stock_qty']}, needed: {remaining}."
            }), 400

    for item in items:
        remaining = item["quantity_ordered"] - item["quantity_shipped"]
        if remaining <= 0:
            continue
        db.execute("UPDATE products SET quantity=quantity-? WHERE id=?",
                   (remaining, item["product_id"]))
        db.execute("UPDATE outbound_order_items SET quantity_shipped=quantity_ordered WHERE id=?",
                   (item["id"],))
        db.execute(
            "INSERT INTO movements"
            " (product_id, product_name, delta, type, reference, reason, created_at)"
            " VALUES (?,?,?,'sale',?,?,?)",
            (item["product_id"], item["product_name"], -remaining,
             order["reference"], "shipped to customer", now()),
        )

    db.execute(
        "UPDATE outbound_orders SET status='shipped', shipped_at=? WHERE id=?",
        (now(), order_id),
    )
    db.commit()
    return jsonify({"status": "shipped"})


@app.post("/api/outbound/<int:order_id>/items/<int:item_id>/instructions/<int:inst_id>/toggle")
def toggle_instruction(order_id, item_id, inst_id):
    db  = get_db()
    row = db.execute(
        "SELECT * FROM outbound_item_instructions WHERE id=? AND order_item_id=?",
        (inst_id, item_id),
    ).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    new_done     = 0 if row["completed"] else 1
    completed_at = now() if new_done else ""
    db.execute(
        "UPDATE outbound_item_instructions SET completed=?, completed_at=? WHERE id=?",
        (new_done, completed_at, inst_id),
    )
    db.commit()
    return jsonify({"completed": new_done})


# ---------------------------------------------------------------------------
# Stats & Dashboard API
# ---------------------------------------------------------------------------
@app.get("/api/stats")
def stats():
    db      = get_db()
    total   = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    low     = db.execute("SELECT COUNT(*) FROM products WHERE quantity <= low_stock_threshold").fetchone()[0]
    units   = db.execute("SELECT COALESCE(SUM(quantity), 0) FROM products").fetchone()[0]
    value   = db.execute("SELECT COALESCE(SUM(quantity * cost_price), 0) FROM products").fetchone()[0]
    pending  = db.execute("SELECT COUNT(*) FROM purchase_orders WHERE status IN ('ordered','partial')").fetchone()[0]
    outbound = db.execute("SELECT COUNT(*) FROM outbound_orders WHERE status IN ('pending','processing')").fetchone()[0]
    return jsonify({
        "total_products":   total,
        "low_stock_count":  low,
        "total_units":      units,
        "total_value":      round(value, 2),
        "pending_orders":   pending,
        "outbound_pending": outbound,
    })


@app.get("/api/stats/chart")
def movement_chart():
    db   = get_db()
    rows = db.execute("""
        SELECT DATE(created_at) as day,
               SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END)      as stock_in,
               SUM(CASE WHEN delta < 0 THEN ABS(delta) ELSE 0 END) as stock_out
        FROM movements
        WHERE created_at >= DATE('now', '-6 days')
          AND NOT (type = 'purchase' AND reason = 'initial stock')
        GROUP BY day ORDER BY day
    """).fetchall()
    by_day = {r["day"]: {"stock_in": r["stock_in"] or 0, "stock_out": r["stock_out"] or 0}
              for r in rows}
    today  = date.today()
    result = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        v = by_day.get(d, {"stock_in": 0, "stock_out": 0})
        result.append({"day": d, "stock_in": v["stock_in"], "stock_out": v["stock_out"]})
    return jsonify(result)


# ---------------------------------------------------------------------------
# Reports API
# ---------------------------------------------------------------------------
@app.get("/api/reports/reorder")
def reorder_report():
    db   = get_db()
    rows = db.execute("""
        SELECT p.*, c.name as category_name, c.color as category_color,
               s.name as supplier_name, s.email as supplier_email, s.phone as supplier_phone
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers  s ON s.id = p.supplier_id
        WHERE p.quantity <= p.low_stock_threshold
        ORDER BY p.quantity ASC
    """).fetchall()
    return jsonify([product_to_dict(r) for r in rows])


@app.get("/api/reports/stock-value")
def stock_value_report():
    db   = get_db()
    rows = db.execute("""
        SELECT p.*, c.name as category_name, c.color as category_color,
               s.name as supplier_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers  s ON s.id = p.supplier_id
        ORDER BY (p.quantity * p.cost_price) DESC
    """).fetchall()
    return jsonify([product_to_dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@app.get("/api/export/products.csv")
def export_csv():
    db   = get_db()
    rows = db.execute("""
        SELECT p.name, p.sku, p.barcode, c.name as category, s.name as supplier,
               p.unit, p.quantity, p.location, p.cost_price,
               ROUND(p.quantity * p.cost_price, 2) as stock_value,
               p.low_stock_threshold, p.reorder_quantity, p.notes, p.created_at
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN suppliers  s ON s.id = p.supplier_id
        ORDER BY p.name
    """).fetchall()
    out = io.StringIO()
    w   = csv.writer(out)
    w.writerow(["Name","SKU","Barcode","Category","Supplier","Unit","Quantity","Location",
                "Cost Price","Stock Value","Low Stock Threshold","Reorder Qty","Notes","Created At"])
    for r in rows:
        w.writerow(list(r))
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory.csv"},
    )


init_db()

if __name__ == "__main__":
    app.run(debug=False)
