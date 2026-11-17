"""End-to-end evaluation on the test invoices: the rule-only baseline against the full graph.

    python evaluate.py                      # both pipelines
    python evaluate.py --pipeline graph     # only one of them
"""
import argparse
import time
from pathlib import Path

import yaml

from baseline import process_without_agent
from create_erp import create_erp
from evaluate_extraction import document_path

ROOT = Path(__file__).parent


def run_baseline(case):
    decision, alerts = process_without_agent(document_path(case))
    return {"decision": decision, "alerts": alerts, "source": "rules"}


def run_graph(case):
    from graph import graph   # imported late: it opens the checkpoint database

    config = {"configurable": {"thread_id": f"eval-{case['id']}-{time.time():.0f}"}}
    # A case that needs a human stops on the interrupt: the decision and the alerts are already in the state.
    state = graph.invoke({"path": str(document_path(case))}, config)
    return {"decision": state["decision"], "alerts": state["alerts"], "source": state.get("source", "-")}


def evaluate(name, run, cases):
    create_erp()   # posting changes the ERP, so every evaluation starts from the reference data
    print(f"\n== {name} ==")
    decisions = alerts = 0
    for case in cases:
        start = time.time()
        result = run(case)
        elapsed = time.time() - start
        decision_ok = result["decision"] == case["expected_decision"]
        alerts_ok = sorted(result["alerts"]) == sorted(case["expected_alerts"])
        decisions += decision_ok
        alerts += alerts_ok
        verdict = "OK  " if decision_ok and alerts_ok else ("~   " if decision_ok else "FAIL")
        print(f"{verdict} invoice_{case['id']:02d} | {result['decision']} (expected {case['expected_decision']}) "
              f"| {result['alerts']} | by {result['source']} | {elapsed:.0f} s | {case['scenario']}")
    print(f"{name}: correct decisions {decisions}/{len(cases)}, exact alerts {alerts}/{len(cases)}")
    print("OK = decision and alerts as expected, ~ = right decision but different alerts, FAIL = wrong decision")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pipeline", choices=["baseline", "graph", "both"], default="both")
    args = parser.parse_args()

    cases = yaml.safe_load((ROOT / "data" / "invoices.yaml").read_text(encoding="utf-8"))
    if args.pipeline in ("baseline", "both"):
        evaluate("Rule-only baseline", run_baseline, cases)
    if args.pipeline in ("graph", "both"):
        evaluate("Full graph", run_graph, cases)
