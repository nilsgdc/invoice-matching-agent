import re
from datetime import date
from pathlib import Path

import yaml
from pypdf import PdfReader

RULES = yaml.safe_load((Path(__file__).parent / "rules.yaml").read_text(encoding="utf-8"))
TOLERANCE = RULES["tolerances"]["vat_rounding_eur"]
MIN_READABLE_FONT_SIZE = RULES["hidden_text"]["min_font_size_pt"]
SUSPICIOUS_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in RULES["suspicious_patterns"]]


def compact(text):
    """Remove all whitespace, so that 'FR76 3000' and 'FR763000' compare equal."""
    return "".join(text.split())


def check_totals(invoice):
    """The amounts of the invoice must be consistent with each other."""
    alerts = []
    lines_total = sum(line.quantity * line.unit_price_excl_vat for line in invoice.lines)
    if abs(lines_total - invoice.total_excl_vat) > TOLERANCE:   # a misread line breaks the sum
        alerts.append("doubtful_extraction")
    if abs(invoice.total_excl_vat + invoice.vat_amount - invoice.total_incl_vat) > TOLERANCE:
        alerts.append("vat_error")
    return alerts


def check_plausibility(invoice):
    """Impossible values point to an extraction error."""
    alerts = []
    if not date(2020, 1, 1) <= invoice.invoice_date <= date.today():
        alerts.append("doubtful_extraction")
    iban = compact(invoice.iban or "")
    if iban.startswith("FR") and len(iban) != 27:   # a French IBAN is always 27 characters long
        alerts.append("doubtful_extraction")
    return alerts


def check_anchoring(invoice, text):
    """The identifiers extracted must appear in the document, otherwise the model made them up or miscopied them."""
    alerts = []
    document = compact(text)
    for value in [invoice.invoice_number, invoice.iban]:
        if value and compact(value) not in document:
            alerts.append("doubtful_extraction")
    return alerts


def run_checks(invoice, text):
    """Run every check on the extracted invoice and return the alerts, deduplicated and in a stable order."""
    alerts = check_totals(invoice) + check_plausibility(invoice) + check_anchoring(invoice, text)
    return sorted(set(alerts))


def find_hidden_text(path):
    """Fragments of a PDF that a human reader cannot see: white text, or text too small to read."""
    fragments = []
    for page in PdfReader(path).pages:
        fill = {"white": False}

        def before(operator, operands, cm, tm):
            if operator in (b"rg", b"g"):   # fill colour, RGB or grey: white when every component is at 1
                fill["white"] = all(float(value) >= 0.99 for value in operands)

        def visit(text, cm, tm, font_dict, font_size):
            if text.strip() and (fill["white"] or font_size < MIN_READABLE_FONT_SIZE):
                fragments.append(text.strip())

        page.extract_text(visitor_operand_before=before, visitor_text=visit)
    return fragments


def check_document(path, text):
    """Look for an instruction aimed at the software, whatever the invoice says otherwise.

    Two signals: text hidden from a human reader, and wording that addresses an AI or asks to skip the checks.
    """
    path = Path(path)
    hidden = find_hidden_text(path) if path.suffix == ".pdf" else []
    flat_text = " ".join(text.split())   # a pattern must not be broken by a line wrap
    if hidden or any(pattern.search(flat_text) for pattern in SUSPICIOUS_PATTERNS):
        return ["suspicious_instruction"]
    return []
