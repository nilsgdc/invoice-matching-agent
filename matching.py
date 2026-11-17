from checks import RULES, compact, run_checks
from erp import invoice_already_posted

PRICE_TOLERANCE = RULES["tolerances"]["unit_price_variance_pct"]
QUANTITY_TOLERANCE = RULES["tolerances"]["quantity_variance"]
AMOUNT_THRESHOLD = RULES["thresholds"]["human_review_amount_excl_vat_eur"]
SEVERITY = {"post": 0, "human_review": 1, "reject": 2}


def compare_to_purchase_order(invoice, purchase_order, pairing):
    """Match the invoice line by line against the purchase order and the goods received.

    `pairing` maps the position of an invoice line to a purchase order line number, for example {0: 1, 1: 2}.
    """
    alerts = []
    po_lines = {line["line"]: line for line in purchase_order["lines"]}
    for position, invoice_line in enumerate(invoice.lines):
        if position not in pairing:
            alerts.append("item_not_ordered")
            continue
        po_line = po_lines[pairing[position]]
        ordered_price = po_line["unit_price_excl_vat"]
        price_variance = (invoice_line.unit_price_excl_vat - ordered_price) / ordered_price * 100
        if price_variance > PRICE_TOLERANCE:   # only a price above the order is a problem
            alerts.append("price_variance")
        received = po_line["quantity_received"] or 0
        if invoice_line.quantity - received > QUANTITY_TOLERANCE:
            alerts.append("quantity_variance")
    return alerts


def verify_invoice(invoice, text, supplier, purchase_order, pairing):
    """Run every verification and return the alerts, deduplicated and in a stable order."""
    if purchase_order is not None and supplier is not None and purchase_order["supplier_id"] != supplier["id"]:
        purchase_order = None   # an order placed with another supplier does not count
    alerts = run_checks(invoice, text)
    if invoice.total_excl_vat > AMOUNT_THRESHOLD:
        alerts.append("high_amount")
    if supplier is None:
        alerts.append("unknown_supplier")
    else:
        if compact(invoice.iban or "") != supplier["iban"]:
            alerts.append("iban_changed")
        if invoice_already_posted(supplier["id"], invoice.invoice_number):
            alerts.append("duplicate")
    if purchase_order is None:
        alerts.append("po_not_found")
    else:
        alerts += compare_to_purchase_order(invoice, purchase_order, pairing)
    return sorted(set(alerts))


def decide(alerts):
    """The strictest decision imposed by the alerts, or post when there is none."""
    decision = "post"
    for alert in alerts:
        imposed = RULES["alerts"][alert]
        if SEVERITY[imposed] > SEVERITY[decision]:
            decision = imposed
    return decision
