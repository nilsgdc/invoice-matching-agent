"""Generate the test invoices (PDF or plain-text email) from data/invoices.yaml.

The documents are written in French on purpose: they imitate what a French accounts payable team receives.
"""
from pathlib import Path

import yaml
from fpdf import FPDF

ROOT = Path(__file__).parent
FOLDER = ROOT / "data" / "invoices"
CUSTOMER = "Atelier Démo SAS, 12 rue de l'Exemple, 75011 Paris"   # the fictional company receiving the invoices


def amount(value):
    """French number format: 1074.72 becomes '1 074,72 EUR'."""
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return text + " EUR"   # "EUR" because the core fonts of fpdf2 cannot write the euro sign


def text_line(pdf, text, bold=False):
    pdf.set_font("Helvetica", "B" if bold else "", 10)
    pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")


def create_pdf(case, path):
    invoice = case["invoice"]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, invoice["supplier"], new_x="LMARGIN", new_y="NEXT")
    text_line(pdf, f"FACTURE N° {invoice['invoice_number']}", bold=True)
    text_line(pdf, f"Date : {invoice['invoice_date'].strftime('%d/%m/%Y')}")
    if invoice["po_number"]:
        text_line(pdf, f"Votre commande : {invoice['po_number']}")
    text_line(pdf, f"Client : {CUSTOMER}")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 8, "Désignation", border=1)
    pdf.cell(25, 8, "Quantité", border=1)
    pdf.cell(35, 8, "Prix unit. HT", border=1)
    pdf.cell(40, 8, "Montant HT", border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    for line in invoice["lines"]:
        pdf.cell(90, 8, line["description"], border=1)
        pdf.cell(25, 8, f"{line['quantity']:g}", border=1)
        pdf.cell(35, 8, amount(line["unit_price_excl_vat"]), border=1)
        pdf.cell(40, 8, amount(line["quantity"] * line["unit_price_excl_vat"]), border=1)
        pdf.ln()
    pdf.ln(5)

    text_line(pdf, f"Total HT : {amount(invoice['total_excl_vat'])}")
    text_line(pdf, f"TVA 20 % : {amount(invoice['vat_amount'])}")
    text_line(pdf, f"Total TTC : {amount(invoice['total_incl_vat'])}", bold=True)
    pdf.ln(5)
    if "notice" in case:   # "our bank details have changed" (invoice 8)
        text_line(pdf, case["notice"], bold=True)
    text_line(pdf, f"Règlement par virement à 30 jours. IBAN : {invoice['iban']}")
    if "hidden_text" in case:   # the planted instruction (invoice 10): white on white, tiny, invisible to a human
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 4)
        pdf.multi_cell(0, 3, case["hidden_text"])
    pdf.output(str(path))


if __name__ == "__main__":
    FOLDER.mkdir(parents=True, exist_ok=True)
    cases = yaml.safe_load((ROOT / "data" / "invoices.yaml").read_text(encoding="utf-8"))
    for case in cases:
        name = f"invoice_{case['id']:02d}"
        if case["format"] == "pdf":
            create_pdf(case, FOLDER / f"{name}.pdf")
        else:
            (FOLDER / f"{name}.txt").write_text(case["email_text"], encoding="utf-8")
        print("Created:", name)
