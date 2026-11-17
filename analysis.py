import json

from pydantic import ValidationError

from llm import chat
from models import Analysis

INSTRUCTIONS = """You assist an accountant who has to review a supplier invoice held by automatic checks.
You are given the invoice, the supplier record, the purchase order from the ERP and the list of alerts raised by the checks.
Explain each alert in plain English, with the figures involved, then propose an action.
Only explain the alerts in the list: do not invent any, and do not conclude yourself that the invoice should be paid.
Usual actions: price variance -> ask for a credit note. Quantity above the goods received -> wait for the delivery or ask for a credit note.
IBAN changed -> call the supplier back on their usual number, never the one on the invoice. Unknown supplier -> verify, then create the supplier record.
High amount -> get the manager's approval. Doubtful extraction -> check the original invoice. Suspicious instruction -> report to IT security."""

SCHEMA = Analysis.model_json_schema()


def analyze_case(invoice, supplier, purchase_order, alerts):
    """Return a verified Analysis, or None when it cannot be trusted."""
    case = json.dumps({"invoice": invoice, "supplier": supplier, "purchase_order": purchase_order, "alerts": alerts},
                      ensure_ascii=False, indent=2)
    instructions = INSTRUCTIONS + "\n\nAnswer with a JSON object that matches this schema:\n" + json.dumps(SCHEMA, ensure_ascii=False)
    response = chat(
        [{"role": "system", "content": instructions}, {"role": "user", "content": case}],
        temperature=0,
        response_format={"type": "json_schema", "json_schema": {"name": "analysis", "schema": SCHEMA}},
    )
    try:
        analysis = Analysis.model_validate_json(response.choices[0].message.content)
    except ValidationError:
        return None
    if set(analysis.cited_alerts) != set(alerts):   # no alert made up, none left out
        return None
    return analysis
