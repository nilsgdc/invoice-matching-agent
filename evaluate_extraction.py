"""Score the extraction field by field against the expected answers of data/invoices.yaml."""
from pathlib import Path

import yaml
from pydantic import ValidationError

from extraction import extract_invoice, read_document
from models import Invoice

ROOT = Path(__file__).parent
FOLDER = ROOT / "data" / "invoices"
FIELDS = ["supplier", "invoice_number", "invoice_date", "po_number",
          "iban", "total_excl_vat", "vat_amount", "total_incl_vat"]


def normalize(value):
    """Put a value in a comparable form."""
    if isinstance(value, str):
        return value.replace(" ", "").lower()
    if isinstance(value, float | int):
        return round(value, 2)   # amounts are compared to the cent
    return value


def quantities_and_prices(invoice):
    return [(normalize(line["quantity"]), normalize(line["unit_price_excl_vat"])) for line in invoice["lines"]]


def compare(expected, obtained):
    """List the wrong fields, with the expected and the obtained value."""
    errors = []
    for field in FIELDS:
        if normalize(expected[field]) != normalize(obtained[field]):
            errors.append(f"{field} (expected {expected[field]}, got {obtained[field]})")
    # Labels are not compared: the model may reword them.
    if quantities_and_prices(expected) != quantities_and_prices(obtained):
        errors.append(f"lines (expected {quantities_and_prices(expected)}, got {quantities_and_prices(obtained)})")
    return errors


def document_path(case):
    extension = ".pdf" if case["format"] == "pdf" else ".txt"
    return FOLDER / f"invoice_{case['id']:02d}{extension}"


if __name__ == "__main__":
    cases = yaml.safe_load((ROOT / "data" / "invoices.yaml").read_text(encoding="utf-8"))
    fields_per_invoice = len(FIELDS) + 1   # the 8 fields, plus the lines counted as one
    correct = 0
    for case in cases:
        path = document_path(case)
        expected = Invoice.model_validate(case["invoice"]).model_dump()
        try:
            obtained = extract_invoice(read_document(path)).model_dump()
        except ValidationError:   # the JSON returned does not fit the schema: no field counted as correct
            print(path.stem, "invalid extraction")
            continue
        errors = compare(expected, obtained)
        correct += fields_per_invoice - len(errors)
        print(path.stem, "OK" if not errors else "wrong: " + ", ".join(errors))

    total = fields_per_invoice * len(cases)
    print(f"Correct fields: {correct}/{total} ({100 * correct / total:.0f} %)")
