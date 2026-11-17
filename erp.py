import sqlite3
from datetime import date
from pathlib import Path

ERP_PATH = Path(__file__).parent / "data" / "erp.db"


def read(sql, parameters=()):
    """Run a read query and return the rows as dictionaries."""
    # Read-only connection: any write attempt fails, whatever the SQL.
    connection = sqlite3.connect(ERP_PATH.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(sql, parameters).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def search_suppliers(name):
    """Suppliers whose name contains the given text."""
    return read("SELECT id, name, iban FROM suppliers WHERE name LIKE ?", (f"%{name}%",))


def get_supplier(supplier_id):
    """A supplier by its identifier, or None."""
    result = read("SELECT id, name, iban FROM suppliers WHERE id = ?", (supplier_id,))
    return result[0] if result else None


def get_purchase_order(number):
    """A purchase order with its lines and the quantities received, or None."""
    headers = read("SELECT number, supplier_id, order_date, status FROM purchase_orders WHERE number = ?", (number,))
    if not headers:
        return None
    purchase_order = headers[0]
    purchase_order["lines"] = read(
        """SELECT l.line, l.description, l.quantity, l.unit_price_excl_vat, r.quantity_received
           FROM po_lines l
           LEFT JOIN receipts r ON r.po_number = l.po_number AND r.line = l.line
           WHERE l.po_number = ?
           ORDER BY l.line""",
        (number,),
    )
    return purchase_order


def list_open_purchase_orders(supplier_id):
    """Open purchase orders of a supplier, with their total excluding VAT."""
    return read(
        """SELECT p.number, p.order_date, ROUND(SUM(l.quantity * l.unit_price_excl_vat), 2) AS total_excl_vat
           FROM purchase_orders p
           JOIN po_lines l ON l.po_number = p.number
           WHERE p.supplier_id = ? AND p.status = 'open'
           GROUP BY p.number
           ORDER BY p.order_date""",
        (supplier_id,),
    )


def invoice_already_posted(supplier_id, invoice_number):
    result = read("SELECT 1 FROM posted_invoices WHERE supplier_id = ? AND invoice_number = ?",
                  (supplier_id, invoice_number))
    return len(result) > 0


def post_invoice(supplier_id, invoice_number, po_number, total_incl_vat):
    """The only write to the ERP: record the invoice as payable and close its purchase order."""
    connection = sqlite3.connect(ERP_PATH)
    connection.execute("INSERT INTO posted_invoices VALUES (?, ?, ?, ?, ?, ?)",
                       (supplier_id, invoice_number, po_number, total_incl_vat, date.today().isoformat(), "to_pay"))
    connection.execute("UPDATE purchase_orders SET status = 'invoiced' WHERE number = ?", (po_number,))
    connection.commit()
    connection.close()
