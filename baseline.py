"""Rule-only pipeline, kept as the baseline the agent is measured against.

The purchase order must be quoted on the invoice and the item labels must match exactly.
"""
from pydantic import ValidationError

from checks import check_document
from erp import get_purchase_order, search_suppliers
from extraction import extract_invoice, read_document
from matching import decide, verify_invoice


def find_supplier(name):
    """The supplier must carry exactly this name in the ERP."""
    for supplier in search_suppliers(name):
        if supplier["name"].lower() == name.lower():
            return supplier
    return None


def pair_by_label(invoice, purchase_order):
    """An invoice line matches the purchase order line that has the same label."""
    pairing = {}
    for position, line in enumerate(invoice.lines):
        for po_line in purchase_order["lines"]:
            if line.description.lower() == po_line["description"].lower():
                pairing[position] = po_line["line"]
    return pairing


def process_without_agent(path):
    """Process one invoice end to end with fixed rules only. Returns (decision, alerts)."""
    text = read_document(path)
    try:
        invoice = extract_invoice(text)
    except ValidationError:   # unreadable extraction: when in doubt a human decides
        return "human_review", sorted(["doubtful_extraction"] + check_document(path, text))
    supplier = find_supplier(invoice.supplier)
    purchase_order = get_purchase_order(invoice.po_number) if invoice.po_number else None
    pairing = pair_by_label(invoice, purchase_order) if purchase_order else {}
    alerts = verify_invoice(invoice, path, text, supplier, purchase_order, pairing)
    return decide(alerts), alerts

