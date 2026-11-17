# Invoice matching agent

[![tests](https://github.com/nilsgdc/invoice-matching-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/nilsgdc/invoice-matching-agent/actions/workflows/tests.yml)

Matches supplier invoices (PDF or plain-text email) against the purchase orders and goods receipts in a mock ERP. Each invoice ends up posted (recorded for payment), rejected or waiting for an accountant.

A personal learning project from October 2026, about 1000 lines of Python on LangGraph. It runs locally, the ERP is a SQLite file and the model is served by Ollama. All data is fictional and the invoices are in French. The 11 scenarios they cover are in [docs/business-case.md](docs/business-case.md).

## Install

You need Python 3.13. The defaults in `.env.example` point at a local Ollama server, any other OpenAI-compatible endpoint works (set it in `.env`).

```bash
ollama pull gpt-oss:20b
python -m venv .venv
.venv\Scripts\activate            # source .venv/bin/activate on Linux and macOS
pip install -r requirements.txt
cp .env.example .env
python create_erp.py
```

The last line builds the ERP, run it again to reset it.

## Usage

To process one invoice:

```bash
python process_invoice.py data/invoices/invoice_08.pdf
```

Invoice 8 has a different IBAN from the supplier record, so the graph pauses:

```
WAITING FOR REVIEW: {'invoice': 'CC-2026-0802', 'supplier': 'Café & Co', 'total_incl_vat': 242.4,
 'explanation': 'The invoice lists the IBAN FR7612548029989876543210917, but the supplier record shows a different IBAN FR7618206000105678901234567, indicating the bank account details have changed. This mismatch could lead to payment being sent to the wrong account.',
 'proposed_action': 'Call the supplier back on their usual number and confirm the correct IBAN before processing the payment.',
 'alerts': ['iban_changed']}
To resume: python process_invoice.py --resume invoice_08-180708 approve   (or reject)
```

The case is saved in SQLite, you can stop the program and answer later. Use the case id from the last line (yours will have a different time) with `approve` or `reject`:

```bash
python process_invoice.py --resume invoice_08-180708 reject
```

## How it works

The nodes of the graph in `graph.py`:

```
extract          LLM, structured output into a Pydantic model
match_by_rules   exact purchase order number and item labels
match_by_agent   only if the rules could not pair everything
                 LLM agent, read-only ERP tools over MCP
                 (search_suppliers, list_open_purchase_orders, get_purchase_order)
verify           all the checks and the decision, plain Python driven by rules.yaml
                 (2% unit price tolerance, human review above 10,000 EUR excluding VAT)
post             if the decision is post: the only write to the ERP
reject           if the decision is reject
analyze          if the decision is human_review: LLM summary for the accountant,
                 dropped if it doesn't cite exactly the alerts raised
human_review     LangGraph interrupt, waits for approve or reject, then post or reject
```

Invoice 10 hides an instruction in white 4-point text asking the AI to skip the checks and post it. In my first version it got posted like any other invoice. Now `checks.py` flags PDF text that's white or smaller than 5 pt, plus a few suspicious phrases listed in `rules.yaml`, and the invoice goes to human review with the `suspicious_instruction` alert.

During development the model swapped day and month on French dates until I stated the format in the field description. The agent also crashed when called from the graph because it inherited the parent graph's synchronous SQLite checkpointer, hence `checkpointer=False` in `matching_agent.py`.

## Evaluation

`evaluate.py` runs the full graph and a rule-only baseline, which is the same extraction and checks without the agent step (`baseline.py`). There are 33 tests, they also run in CI.

```bash
python evaluate.py               # both pipelines on the 12 invoices, the ERP is reset first
python evaluate_extraction.py    # field-by-field extraction score
pytest                           # deterministic parts only, no model needed
```

Numbers with `gpt-oss:20b`. The full graph gave the same ones over three runs. "Exact alerts" means the alerts raised are exactly the ones expected in `data/invoices.yaml`.

| Pipeline | Correct decisions | Exact alerts |
| --- | --- | --- |
| Rule-only baseline | 10/12 | 9/12 |
| Full graph (rules, then agent) | 12/12 | 11/12 |

Extraction alone gets 107 of 108 fields right.

The agent is what gets invoices 5 and 12 right: 5 quotes no purchase order number, 12 is a free-form email with items worded differently. The miss is invoice 3, where the model reads the quantity as 1 instead of 20 because of the "1 kg" in the item label. The totals check notices and the invoice goes to human review, so the decision is right but there's one alert too many.

I wrote the test set myself and tuned the prompts on it, with a single model, so I can't tell how it would do on real invoices. The hidden-text check doesn't read images, and the ERP has no authentication.
