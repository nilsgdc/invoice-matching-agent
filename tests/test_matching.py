from datetime import date

from matching import compare_to_purchase_order, decide
from models import Invoice, InvoiceLine

# 20 kg of coffee at 18.40 EUR, all received.
PURCHASE_ORDER = {"number": "PO-TEST", "supplier_id": "F003", "lines": [
    {"line": 1, "description": "Café en grains 1 kg", "quantity": 20, "unit_price_excl_vat": 18.40, "quantity_received": 20},
]}


def coffee_invoice(quantity, price):
    line = InvoiceLine(description="Café en grains 1 kg", quantity=quantity, unit_price_excl_vat=price)
    return Invoice(supplier="Café & Co", invoice_number="T-1", invoice_date=date(2026, 9, 18),
                   po_number="PO-TEST", iban=None, lines=[line],
                   total_excl_vat=quantity * price, vat_amount=0, total_incl_vat=quantity * price)


def test_small_price_variance_is_accepted():
    assert compare_to_purchase_order(coffee_invoice(20, 18.70), PURCHASE_ORDER, {0: 1}) == []   # +1.6 %


def test_large_price_variance():
    assert compare_to_purchase_order(coffee_invoice(20, 19.90), PURCHASE_ORDER, {0: 1}) == ["price_variance"]   # +8.2 %


def test_quantity_above_goods_received():
    assert compare_to_purchase_order(coffee_invoice(25, 18.40), PURCHASE_ORDER, {0: 1}) == ["quantity_variance"]


def test_line_without_a_match():
    assert compare_to_purchase_order(coffee_invoice(20, 18.40), PURCHASE_ORDER, {}) == ["item_not_ordered"]


def test_strictest_decision_wins():
    assert decide([]) == "post"
    assert decide(["price_variance"]) == "human_review"
    assert decide(["price_variance", "duplicate"]) == "reject"
