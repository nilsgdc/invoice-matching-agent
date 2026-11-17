import sqlite3
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from analysis import analyze_case
from baseline import find_supplier, pair_by_label
from checks import check_document
from erp import get_purchase_order, get_supplier, post_invoice
from extraction import extract_invoice, read_document
from matching import decide, verify_invoice
from matching_agent import find_purchase_order
from models import Invoice


class State(TypedDict, total=False):
    path: str                  # the invoice file
    text: str                  # its raw text
    invoice: dict              # the extracted invoice, as plain JSON so it can be checkpointed
    supplier: dict | None      # the supplier record found in the ERP
    purchase_order: dict | None
    po_lines: list[int]        # for each invoice line, the paired purchase order line, 0 if none
    source: str                # who found the purchase order: "rules" or "agent"
    alerts: list[str]
    decision: str              # post, human_review or reject
    human_decision: str        # the accountant's answer: "approve" or "reject"
    status: str                # final outcome: posted, rejected or blocked
    explanation: str           # brief prepared for the accountant
    proposed_action: str


def extract(state):
    text = read_document(state["path"])
    try:
        invoice = extract_invoice(text)
    except ValidationError:   # unreadable extraction: record the alert, the routing stops the graph
        alerts = sorted(["doubtful_extraction"] + check_document(state["path"], text))
        return {"text": text, "alerts": alerts, "decision": "human_review"}
    return {"text": text, "invoice": invoice.model_dump(mode="json")}


def match_by_rules(state):
    invoice = Invoice.model_validate(state["invoice"])
    supplier = find_supplier(invoice.supplier)
    purchase_order = get_purchase_order(invoice.po_number) if invoice.po_number else None
    pairing = pair_by_label(invoice, purchase_order) if purchase_order else {}
    po_lines = [pairing.get(position, 0) for position in range(len(invoice.lines))]
    return {"supplier": supplier, "purchase_order": purchase_order, "po_lines": po_lines, "source": "rules"}


def rules_are_enough(state):
    """The agent only steps in when the fixed rules could not match everything."""
    all_found = state["supplier"] and state["purchase_order"] and 0 not in state["po_lines"]
    return "verify" if all_found else "match_by_agent"


def match_by_agent(state):
    invoice = Invoice.model_validate(state["invoice"])
    result = find_purchase_order(invoice)
    if result is None or result.po_number is None:   # the agent found nothing: keep what the rules found
        return {}
    # Read the purchase order again from the ERP instead of taking the agent's word for it.
    purchase_order = get_purchase_order(result.po_number)
    if purchase_order is None:   # the agent quoted an order that does not exist
        return {}
    valid_lines = {line["line"] for line in purchase_order["lines"]}
    po_lines = [number if number in valid_lines else 0 for number in result.po_lines]   # drop made-up line numbers
    supplier = get_supplier(result.supplier_id) if result.supplier_id else state["supplier"]
    return {"supplier": supplier, "purchase_order": purchase_order, "po_lines": po_lines, "source": "agent"}


def verify(state):
    """The checks and the decision are plain code: the model never decides."""
    invoice = Invoice.model_validate(state["invoice"])
    pairing = {position: line for position, line in enumerate(state["po_lines"]) if line}
    alerts = verify_invoice(invoice, state["path"], state["text"], state["supplier"], state["purchase_order"], pairing)
    return {"alerts": alerts, "decision": decide(alerts)}


def analyze(state):
    """Prepare the brief for the accountant."""
    analysis = analyze_case(state["invoice"], state["supplier"], state["purchase_order"], state["alerts"])
    if analysis is None:   # invalid or unfaithful explanation: fall back to the raw list of alerts
        return {"explanation": "Alerts raised: " + ", ".join(state["alerts"]),
                "proposed_action": "Review the invoice manually."}
    return {"explanation": analysis.explanation, "proposed_action": analysis.proposed_action}


def ask_for_review(state):
    """Pause the graph until the accountant answers."""
    answer = interrupt({
        "invoice": state["invoice"]["invoice_number"],
        "supplier": state["invoice"]["supplier"],
        "total_incl_vat": state["invoice"]["total_incl_vat"],
        "explanation": state["explanation"],
        "proposed_action": state["proposed_action"],
        "alerts": state["alerts"],
    })
    return {"human_decision": answer}   # on resume, interrupt returns the value passed to Command(resume=...)


def post(state):
    """The only node that writes to the ERP."""
    if state["supplier"] is None:
        return {"status": "blocked: the supplier must be created in the ERP first"}
    invoice = state["invoice"]
    po_number = state["purchase_order"]["number"] if state["purchase_order"] else None
    post_invoice(state["supplier"]["id"], invoice["invoice_number"], po_number, invoice["total_incl_vat"])
    return {"status": "posted"}


def reject(state):
    """The invoice goes back to the supplier. Nothing is written to the ERP."""
    return {"status": "rejected"}


def after_extraction(state):
    return "match_by_rules" if state.get("invoice") else END


def after_verification(state):
    if state["decision"] == "human_review":
        return "analyze"   # the brief is prepared before the accountant is asked
    return state["decision"]


def after_review(state):
    return "post" if state["human_decision"] == "approve" else "reject"


builder = StateGraph(State)
builder.add_node("extract", extract)
builder.add_node("match_by_rules", match_by_rules)
builder.add_node("match_by_agent", match_by_agent)
builder.add_node("verify", verify)
builder.add_node("analyze", analyze)
builder.add_node("human_review", ask_for_review)
builder.add_node("post", post)
builder.add_node("reject", reject)

builder.add_edge(START, "extract")
builder.add_conditional_edges("extract", after_extraction)
builder.add_conditional_edges("match_by_rules", rules_are_enough)
builder.add_edge("match_by_agent", "verify")
builder.add_conditional_edges("verify", after_verification)
builder.add_edge("analyze", "human_review")
builder.add_conditional_edges("human_review", after_review)
builder.add_edge("post", END)
builder.add_edge("reject", END)

# Every step is saved to disk, so a case waiting for a human survives a restart.
CHECKPOINTS_PATH = Path(__file__).parent / "data" / "checkpoints.db"
checkpointer = SqliteSaver(sqlite3.connect(CHECKPOINTS_PATH, check_same_thread=False))
graph = builder.compile(checkpointer=checkpointer)
