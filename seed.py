"""
SyncLogistics — Seed script
Populates the DB with realistic IT hardware warehouse data (Dell, HP, Lenovo, Logitech, Kingston).

Usage:
    py seed.py          # inserts if not exists
    py seed.py --reset  # wipes all data first, then re-seeds
"""

import os
import sqlite3
import sys
from datetime import datetime, timedelta

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")

CATEGORIES = [
    ("Monitors",         "#2563EB"),
    ("Laptops",          "#7C3AED"),
    ("Workstations",     "#0891B2"),
    ("Peripherals",      "#059669"),
    ("Cables & Docking", "#D97706"),
    ("Storage & Memory", "#DC2626"),
]

# name, contact, email, phone, notes
SUPPLIERS = [
    ("Dell Romania SRL",        "Alexandru Popa",     "alex.popa@dell.com",          "+40 21 302 3600", "Preferred vendor — Net 30"),
    ("HP Romania SRL",          "Cristina Marin",     "cristina.marin@hp.com",       "+40 21 302 7200", "Net 45, free shipping above 5k RON"),
    ("Lenovo Romania SRL",      "Bogdan Ionescu",     "bogdan.ionescu@lenovo.com",   "+40 31 860 4300", "ThinkPad series only"),
    ("Logitech Romania",        "Diana Stan",         "diana.stan@logitech.com",     "+40 21 666 0400", "Reseller account #LO-RO-4421"),
    ("Kingston Technology EU",  "Radu Dumitrescu",    "radu.dumitrescu@kingston.com","+40 31 555 0500", "Memory & storage specialist"),
]

# name, sku, qty, location, threshold, reorder, unit, cost_ron, category, supplier, notes
PRODUCTS = [
    # --- Monitors ---
    ("Dell UltraSharp 24\" U2422H",         "DEL-MON-U2422H",  18, "R-A01", 5, 10, "pcs", 1450,  "Monitors",         "Dell Romania SRL",       "FHD IPS, USB-C hub, 3Y on-site warranty"),
    ("Dell UltraSharp 27\" U2722D",         "DEL-MON-U2722D",  12, "R-A02", 4,  8, "pcs", 2100,  "Monitors",         "Dell Romania SRL",       "QHD IPS, USB-C 90W, Thunderbolt hub"),
    ("Dell UltraSharp 32\" 4K U3223QE",     "DEL-MON-U3223QE",  3, "R-A03", 4,  4, "pcs", 4200,  "Monitors",         "Dell Romania SRL",       "4K IPS Black, USB-C 90W, KVM switch"),
    ("Dell P2422H 24\" Business",           "DEL-MON-P2422H",  26, "R-A04", 8, 15, "pcs",  890,  "Monitors",         "Dell Romania SRL",       "FHD IPS, 3Y on-site warranty, VESA"),
    ("HP E24 G5 FHD 24\"",                 "HP-MON-E24G5",    11, "R-A05", 4,  8, "pcs",  780,  "Monitors",         "HP Romania SRL",         "FHD IPS, USB-A hub, VESA 100x100"),
    ("HP Z27k G3 4K USB-C 27\"",           "HP-MON-Z27KG3",    2, "R-A06", 3,  4, "pcs", 3100,  "Monitors",         "HP Romania SRL",         "4K IPS, USB-C 65W, DisplayHDR 400"),

    # --- Laptops ---
    ("Dell Latitude 5540 15\" i5",          "DEL-LAP-LAT5540",  7, "R-B01", 3,  5, "pcs", 5200,  "Laptops",          "Dell Romania SRL",       "i5-1345U, 16GB, 512GB SSD, Intel Evo"),
    ("Dell Latitude 7440 14\" i7",          "DEL-LAP-LAT7440",  3, "R-B02", 2,  3, "pcs", 7800,  "Laptops",          "Dell Romania SRL",       "i7-1365U, 16GB, 512GB SSD, vPro"),
    ("Dell Vostro 3520 15\" i5",            "DEL-LAP-VOS3520", 12, "R-B03", 4,  8, "pcs", 3400,  "Laptops",          "Dell Romania SRL",       "i5-1235U, 8GB, 256GB SSD"),
    ("Dell XPS 13 Plus 9320",              "DEL-LAP-XPS9320",   2, "R-B04", 3,  2, "pcs", 9500,  "Laptops",          "Dell Romania SRL",       "i7-1260P, 16GB, 512GB, OLED Touch"),
    ("Lenovo ThinkPad L14 Gen4 i5",        "LEN-LAP-TPL14G4",   6, "R-B05", 3,  5, "pcs", 4900,  "Laptops",          "Lenovo Romania SRL",     "i5-1335U, 16GB, 512GB SSD, IPS"),
    ("HP EliteBook 840 G10 i7",            "HP-LAP-EB840G10",   4, "R-B06", 2,  3, "pcs", 7200,  "Laptops",          "HP Romania SRL",         "i7-1355U, 16GB, 512GB SSD, Sure View"),

    # --- Workstations ---
    ("Dell OptiPlex 7010 SFF i5",          "DEL-WRK-OPT7010",  5, "R-F01", 2,  4, "pcs", 3200,  "Workstations",     "Dell Romania SRL",       "i5-13500T, 8GB, 256GB SSD, Win 11 Pro"),
    ("Dell Precision 3660 Tower i7",       "DEL-WRK-P3660T",   1, "R-F02", 2,  2, "pcs", 8500,  "Workstations",     "Dell Romania SRL",       "i7-12700, 32GB, 512GB SSD, NVIDIA T400"),
    ("HP Z4 G5 Workstation Xeon",          "HP-WRK-Z4G5",      1, "R-F03", 2,  1, "pcs",15000,  "Workstations",     "HP Romania SRL",         "Xeon W3-2435, 64GB ECC, 1TB SSD"),
    ("Dell Wyse 5070 Thin Client",         "DEL-WRK-WYSE5070", 8, "R-F04", 3,  6, "pcs", 1200,  "Workstations",     "Dell Romania SRL",       "Pentium Silver, 4GB, 16GB eMMC, ThinOS"),

    # --- Peripherals ---
    ("Dell KM636 Wireless KB+Mouse",       "DEL-PER-KM636",   24, "R-D01", 6, 12, "pcs",  350,  "Peripherals",      "Dell Romania SRL",       "2.4GHz USB dongle, RO layout, 12-mo battery"),
    ("Dell KB216 Wired Keyboard",          "DEL-PER-KB216",   38, "R-D02",10, 20, "pcs",  120,  "Peripherals",      "Dell Romania SRL",       "USB, quiet chiclet keys, RO layout"),
    ("Dell MS3320W Wireless Mouse",        "DEL-PER-MS3320W", 22, "R-D03", 6, 12, "pcs",  150,  "Peripherals",      "Dell Romania SRL",       "2.4GHz, 3-button, 1600 DPI, ambidextrous"),
    ("Logitech MX Keys Advanced KB",       "LOG-PER-MXKEYS",   8, "R-D04", 3,  6, "pcs",  650,  "Peripherals",      "Logitech Romania",       "Backlit, multi-device Bluetooth, USB-C charge"),
    ("Logitech MX Master 3S Mouse",        "LOG-PER-MXM3S",   11, "R-D05", 4,  8, "pcs",  480,  "Peripherals",      "Logitech Romania",       "8000 DPI, silent click, 3-device, USB-C"),
    ("Dell WB3023 Full HD Webcam",         "DEL-PER-WB3023",   6, "R-D06", 2,  4, "pcs",  420,  "Peripherals",      "Dell Romania SRL",       "1080p@30fps, auto-focus, USB-A, privacy shutter"),
    ("Dell Stereo Headset UC350",          "DEL-PER-H350",     5, "R-D07", 3,  6, "pcs",  280,  "Peripherals",      "Dell Romania SRL",       "UC/Teams certified, in-line controls, 3.5mm"),

    # --- Cables & Docking ---
    ("Dell Thunderbolt Dock WD22TB4",      "DEL-DOC-WD22TB4",  9, "R-C01", 3,  6, "pcs", 1850,  "Cables & Docking", "Dell Romania SRL",       "TBT4 180W, 2xDP, 1xHDMI, 5xUSB, LAN"),
    ("Dell USB-C Dock WD19S 180W",         "DEL-DOC-WD19S",   15, "R-C02", 5, 10, "pcs", 1250,  "Cables & Docking", "Dell Romania SRL",       "USB-C 180W, 3xDP, 1xHDMI, 5xUSB, LAN"),
    ("Dell USB-C to HDMI 2.0 Cable 2m",    "DEL-CBL-USBCH2M", 35, "R-C03",10, 20, "pcs",   95,  "Cables & Docking", "Dell Romania SRL",       "4K@60Hz, 2m, nylon braided"),
    ("Dell HDMI-to-DisplayPort Adapter",   "DEL-CBL-HDMIDP",  28, "R-C04", 8, 15, "pcs",   55,  "Cables & Docking", "Dell Romania SRL",       "Active adapter, 4K@30Hz, plug & play"),
    ("Dell Power Cable C13 IEC 1.8m",      "DEL-CBL-PWR18",   55, "R-C05",15, 30, "pcs",   30,  "Cables & Docking", "Dell Romania SRL",       "3-pin IEC C13, CEE 7/7 Schuko plug"),
    ("DisplayPort 1.4 Cable 2m",           "GEN-CBL-DP14",    42, "R-C06",12, 20, "pcs",   45,  "Cables & Docking", "Dell Romania SRL",       "DP 1.4, 8K@60Hz / 4K@120Hz, 2m"),

    # --- Storage & Memory ---
    ("Kingston 16GB DDR5-4800 SODIMM",     "KNG-MEM-16G5",    20, "R-E01", 6, 12, "pcs",  280,  "Storage & Memory", "Kingston Technology EU", "Non-ECC, laptop, KCP548SS8-16"),
    ("Kingston 32GB DDR5-4800 SODIMM",     "KNG-MEM-32G5",    10, "R-E02", 4,  8, "pcs",  520,  "Storage & Memory", "Kingston Technology EU", "Non-ECC, laptop, KCP548SD8-32"),
    ("Kingston 1TB NVMe M.2 SSD",          "KNG-SSD-1TNV",    16, "R-E03", 5, 10, "pcs",  380,  "Storage & Memory", "Kingston Technology EU", "PCIe 4.0, 7000/6000 MB/s, SKC3000S"),
    ("Kingston 2TB NVMe M.2 SSD",          "KNG-SSD-2TNV",     7, "R-E04", 3,  6, "pcs",  650,  "Storage & Memory", "Kingston Technology EU", "PCIe 4.0, 7000/6000 MB/s, SKC3000S"),
    ("Kingston 8GB DDR4-3200 SODIMM",      "KNG-MEM-8G4",     14, "R-E05", 6, 10, "pcs",  140,  "Storage & Memory", "Kingston Technology EU", "Non-ECC, laptop, 1.2V, KVR32S22S6/8"),
]

# Extra movements in last 30 days — these populate the activity feed and stock chart.
# Format: (days_ago, hour, sku, delta, type, reason, reference)
RECENT_MOVEMENTS = [
    # — Day 28-25: PO-2026-0001 delivery from Dell (monitors + laptops + peripherals) —
    (28,  9, "DEL-MON-P2422H",   +20, "purchase", "goods received",             "PO-2026-0001"),
    (27, 10, "DEL-LAP-VOS3520",  +10, "purchase", "goods received",             "PO-2026-0001"),
    (26, 14, "DEL-PER-KM636",    +15, "purchase", "goods received",             "PO-2026-0001"),
    (26, 15, "DEL-PER-KB216",    +30, "purchase", "goods received",             "PO-2026-0001"),
    # — Day 25-22: First dispatches after delivery —
    (25, 11, "DEL-MON-P2422H",    -5, "sale",     "dispatch — IT Dept A",       ""),
    (25, 14, "DEL-LAP-VOS3520",   -3, "sale",     "dispatch — IT Dept B",       ""),
    (24, 10, "DEL-MON-U2422H",    -4, "sale",     "dispatch — branch Cluj",     ""),
    (23,  9, "DEL-LAP-LAT5540",   -2, "sale",     "dispatch — branch Iași",     ""),
    (22, 13, "DEL-PER-KB216",     -8, "sale",     "dispatch — HR Dept",         ""),
    # — Day 21-15: Steady outflow —
    (21, 10, "DEL-MON-P2422H",    -6, "sale",     "dispatch — IT Dept C",       ""),
    (20, 11, "DEL-DOC-WD19S",     -3, "sale",     "dispatch — project team Alpha",""),
    (19, 14, "DEL-CBL-USBCH2M",  -10, "sale",     "bulk dispatch — cable kit",  ""),
    (18,  9, "DEL-LAP-LAT7440",   -1, "sale",     "dispatch — management level",""),
    (18, 16, "KNG-MEM-16G5",     +20, "purchase", "partial receive",            "PO-2026-0002"),
    (17, 11, "DEL-MON-U2722D",    -2, "sale",     "dispatch — design studio",   ""),
    (16, 10, "LOG-PER-MXM3S",     -4, "sale",     "dispatch — creative dept",   ""),
    (15, 14, "DEL-WRK-OPT7010",   -1, "sale",     "dispatch — server room",     ""),
    # — Day 14-8: Mid-month activity —
    (14, 10, "DEL-MON-P2422H",    -3, "sale",     "dispatch — support team",    ""),
    (13, 11, "DEL-PER-KB216",     -5, "sale",     "dispatch — operations floor",""),
    (12, 14, "DEL-LAP-VOS3520",   -2, "sale",     "dispatch — finance dept",    ""),
    (11, 10, "DEL-CBL-PWR18",     -8, "sale",     "bulk dispatch — new office", ""),
    (10, 15, "DEL-PER-KM636",     -4, "sale",     "dispatch — reception desk",  ""),
    ( 9, 10, "KNG-SSD-1TNV",     +10, "purchase", "partial receive",            "PO-2026-0002"),
    ( 9, 11, "KNG-MEM-32G5",      +8, "purchase", "partial receive",            "PO-2026-0002"),
    ( 8, 14, "DEL-DOC-WD22TB4",   -2, "sale",     "dispatch — dev team",        ""),
    # — Day 7-1: This week —
    ( 7, 10, "DEL-MON-U2422H",    -3, "sale",     "dispatch — branch Timișoara",""),
    ( 6, 14, "DEL-MON-U2422H",    +8, "purchase", "goods received",             "PO-2026-0004"),
    ( 6, 11, "DEL-LAP-VOS3520",   -2, "sale",     "dispatch — HR",              ""),
    ( 5,  9, "LOG-PER-MXKEYS",    -3, "sale",     "dispatch — executive floor", ""),
    ( 4, 10, "LOG-PER-MXM3S",     +6, "purchase", "goods received",             "PO-2026-0004"),
    ( 4, 14, "DEL-CBL-USBCH2M",   -6, "sale",     "dispatch — meeting rooms",   ""),
    ( 3, 10, "DEL-MON-P2422H",    -4, "sale",     "dispatch — IT expansion",    ""),
    ( 2, 15, "KNG-SSD-1TNV",      +5, "purchase", "partial receive",            "PO-2026-0002"),
    ( 2, 11, "DEL-PER-WB3023",    -2, "sale",     "dispatch — remote workers",  ""),
    ( 1, 14, "DEL-DOC-WD19S",     +5, "purchase", "goods received",             "PO-2026-0004"),
    ( 1,  9, "DEL-LAP-LAT5540",   -1, "sale",     "dispatch — VIP request",     ""),
    # — Today —
    ( 0, 10, "GEN-CBL-DP14",      -5, "sale",     "dispatch — meeting rooms",   ""),
    ( 0, 14, "DEL-PER-KB216",     -4, "sale",     "dispatch — new hires batch", ""),
]


CUSTOMERS = [
    ("Google Romania SRL",    "Andrei Dumitrescu", "andrei.d@google.com",      "+40 21 310 9000", "Str. Fabrica de Glucoză 5, București 022965",  "Key account — SLA 24h delivery"),
    ("Microsoft Romania SRL", "Elena Popescu",     "elena.p@microsoft.com",    "+40 21 302 8200", "Calea Plevnei 139, București 060012",           "Net 30, standard delivery"),
    ("Vodafone Romania SA",   "Mihai Ionescu",     "mihai.i@vodafone.com",     "+40 21 406 8000", "Str. Logofăt Tăutu 13, București 030167",      "Monthly recurring order — IT refresh"),
    ("ING Bank Romania",      "Diana Marin",       "diana.m@ing.ro",           "+40 21 222 4400", "Str. Barbu Văcărescu 54A, București 020356",    "Net 45, schedule delivery 48h prior"),
    ("Raiffeisen Bank SA",    "Cristian Stan",     "cristian.s@raiffeisen.ro", "+40 21 306 1000", "Piața Charles de Gaulle 15, București 011857",  "IT refresh contract 2026 — Q2 batch"),
]

# (code, title, description, estimated_minutes)
WORK_INSTRUCTIONS = [
    ("WI-001", "Apply client asset tag",       "Affix client-provided barcode label on the back of the unit, bottom-left corner next to service tag.", 3),
    ("WI-002", "BIOS/UEFI configuration",      "Apply client BIOS settings per spec sheet: disable secure boot, set boot order USB→HDD, apply BIOS password.", 15),
    ("WI-003", "Keyboard layout change",       "Change keyboard language/layout to client specification (default: EN-US). Verify via OS on-screen keyboard.", 5),
    ("WI-004", "Remove retail packaging",      "Remove product from retail box, inspect for damage, repack in plain brown box with foam inserts. Retain serial.", 8),
    ("WI-005", "Attach power cable",           "Attach IEC C13 power cable to unit using velcro tie. Include cable in box. Match cable to client country spec.", 2),
    ("WI-006", "Insert warranty & support card","Place Dell warranty leaflet and SyncLogistics support card in box before sealing.", 1),
    ("WI-007", "Driver & firmware pre-install","Run Dell Command | Update to install latest BIOS, drivers, firmware. Requires 30–60 min per unit. Log version.", 45),
    ("WI-008", "Quality inspection (QC)",      "Visual check for physical damage. Power on, verify POST, display, ports. Sign QC checklist. Reject if fail.", 10),
    ("WI-009", "Photograph serial number",     "Photograph service tag and serial label. Upload to shared drive: /assets/serials/[order-ref]/[sku]/.", 3),
    ("WI-010", "Pallet wrapping",              "Arrange units on EUR 120×80cm pallet. Wrap 3 layers stretch film. Apply shock indicator. Label with order ref.", 20),
]


def ts(days_ago=0, hour=12):
    dt = datetime.now() - timedelta(days=days_ago)
    return dt.strftime(f"%Y-%m-%d {hour:02d}:30")


def seed(reset=False):
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    if reset:
        print("Resetting data…")
        db.executescript("""
            DELETE FROM outbound_item_instructions;
            DELETE FROM outbound_order_items;
            DELETE FROM outbound_orders;
            DELETE FROM work_instructions;
            DELETE FROM customers;
            DELETE FROM purchase_order_items;
            DELETE FROM purchase_orders;
            DELETE FROM movements;
            DELETE FROM products;
            DELETE FROM suppliers;
            DELETE FROM categories;
        """)
        db.commit()

    # ── Categories ─────────────────────────────────────────────────────────
    cat_ids = {}
    for name, color in CATEGORIES:
        try:
            cur = db.execute("INSERT INTO categories (name, color) VALUES (?,?)", (name, color))
            cat_ids[name] = cur.lastrowid
        except Exception:
            row = db.execute("SELECT id FROM categories WHERE name=?", (name,)).fetchone()
            if row:
                cat_ids[name] = row["id"]
    db.commit()
    print(f"Categories: {len(cat_ids)}")

    # ── Suppliers ───────────────────────────────────────────────────────────
    sup_ids = {}
    for name, contact, email, phone, notes in SUPPLIERS:
        try:
            cur = db.execute(
                "INSERT INTO suppliers (name, contact_name, email, phone, notes, created_at)"
                " VALUES (?,?,?,?,?,?)",
                (name, contact, email, phone, notes, ts(120)),
            )
            sup_ids[name] = cur.lastrowid
        except Exception:
            row = db.execute("SELECT id FROM suppliers WHERE name=?", (name,)).fetchone()
            if row:
                sup_ids[name] = row["id"]
    db.commit()
    print(f"Suppliers: {len(sup_ids)}")

    # ── Products ─────────────────────────────────────────────────────────────
    product_ids   = {}
    product_names = {}
    n = 0
    for (pname, sku, qty, location, threshold, reorder, unit, cost, cat_name, sup_name, notes) in PRODUCTS:
        created = ts(days_ago=90 + n % 30)  # spread creation 90-120 days ago
        cat_id  = cat_ids.get(cat_name)
        sup_id  = sup_ids.get(sup_name)
        try:
            cur = db.execute(
                """INSERT INTO products
                   (name, sku, quantity, location, low_stock_threshold, reorder_quantity,
                    category_id, supplier_id, unit, cost_price, notes, barcode, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pname, sku, qty, location, threshold, reorder,
                 cat_id, sup_id, unit, cost, notes, "", created),
            )
            pid = cur.lastrowid
            db.execute(
                "INSERT INTO movements (product_id, product_name, delta, type, reason, created_at)"
                " VALUES (?,?,?,'purchase','initial stock',?)",
                (pid, pname, qty, created),
            )
            product_ids[sku]   = pid
            product_names[sku] = pname
            n += 1
        except sqlite3.IntegrityError:
            row = db.execute("SELECT id FROM products WHERE sku=?", (sku,)).fetchone()
            if row:
                product_ids[sku]   = row["id"]
                product_names[sku] = db.execute("SELECT name FROM products WHERE id=?", (row["id"],)).fetchone()["name"]
    db.commit()
    print(f"Products: {n} inserted")

    # ── Recent movements (last 30 days — fills the chart) ──────────────────
    if db.execute("SELECT COUNT(*) FROM movements WHERE created_at >= DATE('now','-30 days')").fetchone()[0] == 0:
        for (days_ago, hour, sku, delta, mtype, reason, ref) in RECENT_MOVEMENTS:
            pid = product_ids.get(sku)
            if not pid:
                continue
            db.execute(
                "INSERT INTO movements (product_id, product_name, delta, type, reason, reference, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (pid, product_names[sku], delta, mtype, reason, ref, ts(days_ago, hour)),
            )
        db.commit()
        print(f"Recent movements: {len(RECENT_MOVEMENTS)} inserted")

    # ── Purchase orders ─────────────────────────────────────────────────────
    if db.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0] == 0:
        dell_id  = sup_ids.get("Dell Romania SRL")
        king_id  = sup_ids.get("Kingston Technology EU")
        logi_id  = sup_ids.get("Logitech Romania")

        # PO-2026-0001 — Dell — received (28 days ago)
        cur = db.execute(
            "INSERT INTO purchase_orders (reference, supplier_id, status, notes, expected_date, created_at, received_at)"
            " VALUES (?,?,?,?,?,?,?)",
            ("PO-2026-0001", dell_id, "received",
             "Q2 Monitor & Laptop Restock — approved by IT Manager",
             "2026-05-30", ts(30), ts(25)),
        )
        po1 = cur.lastrowid
        for sku, qty, price in [
            ("DEL-MON-P2422H",  20, 820),
            ("DEL-LAP-VOS3520", 10, 3200),
            ("DEL-PER-KM636",   15, 320),
            ("DEL-PER-KB216",   30, 110),
        ]:
            pid = product_ids.get(sku)
            if pid:
                db.execute(
                    "INSERT INTO purchase_order_items (order_id, product_id, quantity_ordered, quantity_received, unit_price)"
                    " VALUES (?,?,?,?,?)",
                    (po1, pid, qty, qty, price),
                )

        # PO-2026-0002 — Kingston — partial (some items received)
        cur = db.execute(
            "INSERT INTO purchase_orders (reference, supplier_id, status, notes, expected_date, created_at, received_at)"
            " VALUES (?,?,?,?,?,?,?)",
            ("PO-2026-0002", king_id, "partial",
             "Memory & SSD procurement — Q3 upgrade project",
             "2026-06-20", ts(8), ""),
        )
        po2 = cur.lastrowid
        for sku, qty_ord, qty_rec, price in [
            ("KNG-MEM-16G5", 30, 20, 260),
            ("KNG-SSD-1TNV", 20, 10, 360),
            ("KNG-MEM-32G5", 10,  8, 490),
        ]:
            pid = product_ids.get(sku)
            if pid:
                db.execute(
                    "INSERT INTO purchase_order_items (order_id, product_id, quantity_ordered, quantity_received, unit_price)"
                    " VALUES (?,?,?,?,?)",
                    (po2, pid, qty_ord, qty_rec, price),
                )

        # PO-2026-0003 — Logitech — ordered (pending)
        cur = db.execute(
            "INSERT INTO purchase_orders (reference, supplier_id, status, notes, expected_date, created_at, received_at)"
            " VALUES (?,?,?,?,?,?,?)",
            ("PO-2026-0003", logi_id, "ordered",
             "Q3 peripherals — executive and creative dept refresh",
             "2026-07-05", ts(1), ""),
        )
        po3 = cur.lastrowid
        for sku, qty, price in [
            ("LOG-PER-MXKEYS", 20, 620),
            ("LOG-PER-MXM3S",  25, 450),
            ("DEL-PER-WB3023",  8, 390),
        ]:
            pid = product_ids.get(sku)
            if pid:
                db.execute(
                    "INSERT INTO purchase_order_items (order_id, product_id, quantity_ordered, quantity_received, unit_price)"
                    " VALUES (?,?,?,?,?)",
                    (po3, pid, qty, 0, price),
                )

        db.commit()
        print("Purchase orders: PO-2026-0001 (received), PO-2026-0002 (partial), PO-2026-0003 (ordered)")

    # ── Customers ───────────────────────────────────────────────────────────
    cust_ids = {}
    for name, contact, email, phone, address, notes in CUSTOMERS:
        try:
            cur = db.execute(
                "INSERT INTO customers (name, contact_name, email, phone, address, notes, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (name, contact, email, phone, address, notes, ts(90)),
            )
            cust_ids[name] = cur.lastrowid
        except Exception:
            row = db.execute("SELECT id FROM customers WHERE name=?", (name,)).fetchone()
            if row: cust_ids[name] = row["id"]
    db.commit()
    print(f"Customers: {len(cust_ids)}")

    # ── Work Instructions ────────────────────────────────────────────────────
    wi_ids = {}
    for code, title, description, mins in WORK_INSTRUCTIONS:
        try:
            cur = db.execute(
                "INSERT INTO work_instructions (code, title, description, estimated_minutes, active)"
                " VALUES (?,?,?,?,1)",
                (code, title, description, mins),
            )
            wi_ids[code] = cur.lastrowid
        except Exception:
            row = db.execute("SELECT id FROM work_instructions WHERE code=?", (code,)).fetchone()
            if row: wi_ids[code] = row["id"]
    db.commit()
    print(f"Work instructions: {len(wi_ids)}")

    # ── Outbound Orders ──────────────────────────────────────────────────────
    if db.execute("SELECT COUNT(*) FROM outbound_orders").fetchone()[0] == 0:
        google_id    = cust_ids.get("Google Romania SRL")
        ms_id        = cust_ids.get("Microsoft Romania SRL")
        voda_id      = cust_ids.get("Vodafone Romania SA")

        # OB-2026-0001 — Google — Processing (in progress)
        cur = db.execute(
            "INSERT INTO outbound_orders"
            " (reference, customer_id, status, delivery_address, notes, required_date, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            ("OB-2026-0001", google_id, "processing",
             "Str. Fabrica de Glucoză 5, București 022965 — Loading dock B, contact security",
             "Apply WI-001 + WI-002 + WI-008 on all units. Deliver between 08:00–14:00.",
             "2026-06-25", ts(5)),
        )
        ob1 = cur.lastrowid
        for sku, qty, wi_codes in [
            ("DEL-LAP-VOS3520",  15, ["WI-001","WI-002","WI-008"]),
            ("DEL-PER-KM636",    15, ["WI-006"]),
            ("DEL-PER-KB216",    30, ["WI-006"]),
        ]:
            pid = product_ids.get(sku)
            if pid:
                item_cur = db.execute(
                    "INSERT INTO outbound_order_items (order_id, product_id, quantity_ordered)"
                    " VALUES (?,?,?)",
                    (ob1, pid, qty),
                )
                iid = item_cur.lastrowid
                for code in wi_codes:
                    wid = wi_ids.get(code)
                    if wid:
                        # Mark WI-006 as completed for demo
                        done = 1 if code == "WI-006" else 0
                        done_at = ts(3) if done else ""
                        db.execute(
                            "INSERT INTO outbound_item_instructions"
                            " (order_item_id, work_instruction_id, completed, completed_at)"
                            " VALUES (?,?,?,?)",
                            (iid, wid, done, done_at),
                        )

        # OB-2026-0002 — Microsoft — Pending
        cur = db.execute(
            "INSERT INTO outbound_orders"
            " (reference, customer_id, status, delivery_address, notes, required_date, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            ("OB-2026-0002", ms_id, "pending",
             "Calea Plevnei 139, București 060012 — Main entrance, attention IT dept",
             "Units must be individually boxed. Include WI-004 packaging. SLA: next-day delivery.",
             "2026-06-30", ts(2)),
        )
        ob2 = cur.lastrowid
        for sku, qty, wi_codes in [
            ("DEL-LAP-LAT5540",  5, ["WI-001","WI-004","WI-008","WI-009"]),
            ("DEL-DOC-WD19S",    5, ["WI-005"]),
        ]:
            pid = product_ids.get(sku)
            if pid:
                item_cur = db.execute(
                    "INSERT INTO outbound_order_items (order_id, product_id, quantity_ordered)"
                    " VALUES (?,?,?)",
                    (ob2, pid, qty),
                )
                iid = item_cur.lastrowid
                for code in wi_codes:
                    wid = wi_ids.get(code)
                    if wid:
                        db.execute(
                            "INSERT INTO outbound_item_instructions"
                            " (order_item_id, work_instruction_id, completed, completed_at)"
                            " VALUES (?,?,?,?)",
                            (iid, wid, 0, ""),
                        )

        # OB-2026-0003 — Vodafone — Shipped (completed 3 days ago)
        cur = db.execute(
            "INSERT INTO outbound_orders"
            " (reference, customer_id, status, delivery_address, notes, required_date, created_at, shipped_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            ("OB-2026-0003", voda_id, "shipped",
             "Str. Logofăt Tăutu 13, București 030167",
             "Monthly IT refresh — Q2 batch. Pallet delivery.",
             "2026-06-15", ts(10), ts(3)),
        )
        ob3 = cur.lastrowid
        for sku, qty, wi_codes in [
            ("DEL-MON-P2422H",  10, ["WI-008"]),
            ("DEL-PER-KB216",   10, ["WI-006"]),
            ("DEL-PER-MS3320W",  5, ["WI-006"]),
        ]:
            pid = product_ids.get(sku)
            if pid:
                item_cur = db.execute(
                    "INSERT INTO outbound_order_items"
                    " (order_id, product_id, quantity_ordered, quantity_shipped)"
                    " VALUES (?,?,?,?)",
                    (ob3, pid, qty, qty),
                )
                iid = item_cur.lastrowid
                for code in wi_codes:
                    wid = wi_ids.get(code)
                    if wid:
                        db.execute(
                            "INSERT INTO outbound_item_instructions"
                            " (order_item_id, work_instruction_id, completed, completed_at)"
                            " VALUES (?,?,?,?)",
                            (iid, wid, 1, ts(3)),
                        )
                # Add shipping movement
                pname = product_names.get(sku, sku)
                db.execute(
                    "INSERT INTO movements (product_id, product_name, delta, type, reference, reason, created_at)"
                    " VALUES (?,?,?,'sale',?,?,?)",
                    (pid, pname, -qty, "OB-2026-0003", "shipped to customer", ts(3, 14)),
                )

        db.commit()
        print("Outbound orders: OB-2026-0001 (processing), OB-2026-0002 (pending), OB-2026-0003 (shipped)")

    db.close()
    print("Done.")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
