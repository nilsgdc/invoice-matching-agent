"""Build the mock ERP: a SQLite file with suppliers, purchase orders, goods receipts and posted invoices."""
import sqlite3

from erp import ERP_PATH

SCHEMA = """
CREATE TABLE suppliers (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    iban TEXT NOT NULL
);
CREATE TABLE purchase_orders (
    number      TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    order_date  TEXT NOT NULL,
    status      TEXT NOT NULL
);
CREATE TABLE po_lines (
    po_number           TEXT NOT NULL REFERENCES purchase_orders(number),
    line                INTEGER NOT NULL,
    description         TEXT NOT NULL,
    quantity            REAL NOT NULL,
    unit_price_excl_vat REAL NOT NULL,
    PRIMARY KEY (po_number, line)
);
CREATE TABLE receipts (
    po_number         TEXT NOT NULL,
    line              INTEGER NOT NULL,
    quantity_received REAL NOT NULL,
    FOREIGN KEY (po_number, line) REFERENCES po_lines(po_number, line)
);
CREATE TABLE posted_invoices (
    supplier_id    TEXT NOT NULL REFERENCES suppliers(id),
    invoice_number TEXT NOT NULL,
    po_number      TEXT,
    total_incl_vat REAL NOT NULL,
    posting_date   TEXT NOT NULL,
    status         TEXT NOT NULL,
    UNIQUE (supplier_id, invoice_number)
);
"""

# (id, name, reference IBAN)
SUPPLIERS = [
    ("F001", "Bureau Plus SAS", "FR7630004000031234567890143"),
    ("F002", "InfoTech Solutions", "FR7610107001011234567890129"),
    ("F003", "Café & Co", "FR7618206000105678901234567"),
    ("F004", "Imprimerie Duval", "FR7614505000017654321098765"),
]

# (number, supplier, order date, status)
PURCHASE_ORDERS = [
    ("PO-2026-099", "F002", "2026-08-28", "invoiced"),
    ("PO-2026-101", "F001", "2026-09-01", "open"),
    ("PO-2026-102", "F002", "2026-09-02", "open"),
    ("PO-2026-103", "F003", "2026-09-04", "open"),
    ("PO-2026-104", "F004", "2026-09-07", "open"),
    ("PO-2026-105", "F001", "2026-09-14", "open"),
    ("PO-2026-106", "F003", "2026-09-15", "open"),
    ("PO-2026-107", "F004", "2026-09-16", "open"),
    ("PO-2026-108", "F001", "2026-09-22", "open"),
    ("PO-2026-109", "F002", "2026-09-23", "open"),
    ("PO-2026-110", "F003", "2026-09-29", "open"),
    ("PO-2026-112", "F001", "2026-09-18", "open"),
]

# (purchase order, line number, description, quantity, unit price excl. VAT)
# The item labels are in French, like the invoices they are matched against.
PO_LINES = [
    ("PO-2026-099", 1, "Clavier sans fil", 10, 39.00),
    ("PO-2026-099", 2, "Souris sans fil", 10, 24.00),
    ("PO-2026-101", 1, "Ramette papier A4 80 g", 50, 4.20),
    ("PO-2026-101", 2, "Stylo bille bleu (boîte de 50)", 4, 12.50),
    ("PO-2026-102", 1, "Écran 27 pouces", 3, 248.00),
    ("PO-2026-102", 2, "Câble HDMI 2 m", 3, 9.90),
    ("PO-2026-103", 1, "Café en grains 1 kg", 20, 18.40),
    ("PO-2026-103", 2, "Gobelets carton (lot de 100)", 10, 6.50),
    ("PO-2026-104", 1, "Flyers A5", 2000, 0.09),
    ("PO-2026-104", 2, "Cartes de visite (boîte de 250)", 10, 22.00),
    ("PO-2026-105", 1, "Chaise ergonomique", 4, 189.00),
    ("PO-2026-105", 2, "Lampe de bureau LED", 4, 34.90),
    ("PO-2026-106", 1, "Thé vert bio (boîte de 100 sachets)", 12, 14.50),
    ("PO-2026-106", 2, "Sucre en morceaux 1 kg", 10, 2.80),
    ("PO-2026-107", 1, "Affiches A2", 50, 3.60),
    ("PO-2026-107", 2, "Kakémono 85x200", 2, 95.00),
    ("PO-2026-108", 1, "Classeur à levier A4", 30, 3.10),
    ("PO-2026-108", 2, "Post-it 76x76 (lot de 12)", 5, 9.80),
    ("PO-2026-109", 1, "Ordinateur portable 14 pouces", 12, 1050.00),
    ("PO-2026-109", 2, "Sacoche ordinateur", 12, 35.00),
    ("PO-2026-110", 1, "Café en grains 1 kg", 15, 18.40),
    ("PO-2026-110", 2, "Lait demi-écrémé (pack de 6 L)", 8, 7.20),
    ("PO-2026-112", 1, "Chaise visiteur", 4, 79.00),
]

# The only incomplete delivery: 6 boxes of business cards received out of 10.
PARTIAL_RECEIPTS = {("PO-2026-104", 2): 6}

# (purchase order, line number, quantity received)
RECEIPTS = [
    (po_number, line, PARTIAL_RECEIPTS.get((po_number, line), quantity))
    for po_number, line, description, quantity, price in PO_LINES
]

# (supplier, invoice number, purchase order, total incl. VAT, date, status)
# Already recorded: invoice 6 of the test set is its duplicate.
POSTED_INVOICES = [
    ("F002", "FAC-IT-0457", "PO-2026-099", 756.00, "2026-09-12", "to_pay"),
]


def create_erp():
    """Recreate the database from scratch, so every run starts from the same reference data."""
    ERP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ERP_PATH.unlink(missing_ok=True)
    connection = sqlite3.connect(ERP_PATH)
    connection.executescript(SCHEMA)
    connection.executemany("INSERT INTO suppliers VALUES (?, ?, ?)", SUPPLIERS)
    connection.executemany("INSERT INTO purchase_orders VALUES (?, ?, ?, ?)", PURCHASE_ORDERS)
    connection.executemany("INSERT INTO po_lines VALUES (?, ?, ?, ?, ?)", PO_LINES)
    connection.executemany("INSERT INTO receipts VALUES (?, ?, ?)", RECEIPTS)
    connection.executemany("INSERT INTO posted_invoices VALUES (?, ?, ?, ?, ?, ?)", POSTED_INVOICES)
    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_erp()
    print("ERP created:", ERP_PATH)
