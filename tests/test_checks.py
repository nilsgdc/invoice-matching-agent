from datetime import date

from checks import run_checks
from models import Invoice, InvoiceLine

TEXT = "FACTURE N° F-001 Date : 14/09/2026 IBAN : FR76 3000 4000 0312 3456 7890 143"


def make_invoice(**changes):
    """Build a correct invoice, then override the given fields."""
    values = dict(
        supplier="Bureau Plus SAS",
        invoice_number="F-001",
        invoice_date=date(2026, 9, 14),
        po_number="PO-2026-101",
        iban="FR7630004000031234567890143",
        lines=[InvoiceLine(description="Ramette", quantity=50, unit_price_excl_vat=4.20)],
        total_excl_vat=210.00,
        vat_amount=42.00,
        total_incl_vat=252.00,
    )
    values.update(changes)
    return Invoice(**values)


def test_correct_invoice_raises_nothing():
    assert run_checks(make_invoice(), TEXT) == []


def test_vat_error():
    assert "vat_error" in run_checks(make_invoice(vat_amount=46.00), TEXT)


def test_impossible_date():
    assert "doubtful_extraction" in run_checks(make_invoice(invoice_date=date(1409, 9, 14)), TEXT)


def test_iban_with_one_digit_too_many():
    assert "doubtful_extraction" in run_checks(make_invoice(iban="FR76300040000312034567890143"), TEXT)


def test_invoice_number_not_in_the_document():
    assert "doubtful_extraction" in run_checks(make_invoice(invoice_number="F-999"), TEXT)
