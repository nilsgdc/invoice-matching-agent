"""Command line entry point.

    python process_invoice.py data/invoices/invoice_03.pdf
    python process_invoice.py --resume <case> approve|reject
"""
import sys
from datetime import datetime
from pathlib import Path

from langgraph.types import Command

from graph import graph

resuming = len(sys.argv) > 1 and sys.argv[1] == "--resume"
if len(sys.argv) < 2 or (resuming and (len(sys.argv) != 4 or sys.argv[3] not in ("approve", "reject"))):
    sys.exit(__doc__)

if resuming:
    case, answer = sys.argv[2], sys.argv[3]
    config = {"configurable": {"thread_id": case}}
    state = graph.invoke(Command(resume=answer), config)   # restart the paused case with the accountant's answer
else:
    path = sys.argv[1]
    case = f"{Path(path).stem}-{datetime.now():%H%M%S}"   # unique case id: file name plus time of day
    config = {"configurable": {"thread_id": case}}
    state = graph.invoke({"path": path}, config)

if "__interrupt__" in state:   # the graph stopped on a human review
    print("WAITING FOR REVIEW:", state["__interrupt__"][0].value)
    print(f"To resume: python process_invoice.py --resume {case} approve   (or reject)")
else:
    print("Decision:", state["decision"], "| alerts:", state["alerts"], "| status:", state.get("status"))
