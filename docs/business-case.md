# Business case: matching supplier invoices

## The problem
Before paying a supplier invoice, the accounting team checks that it corresponds to what was ordered and to what was delivered. This check is manual and repetitive, it produces errors, and it is the door IBAN-change fraud comes through.

## The current process (assumptions to validate)
1. The accountant receives the invoice, as a PDF or in an email.
2. They look up the purchase order in the ERP.
3. They compare each line: item, quantity, price.
4. They check on the goods receipt that the goods were delivered.
5. They post the invoice, or hold it and contact the supplier.

Estimated time: about 10 minutes per invoice (assumption).

## The possible decisions
- **Post**: everything matches, the invoice is recorded automatically.
- **Human review**: an accountant has to decide.
- **Reject**: the invoice is sent back to the supplier.

## The scenarios
| # | Scenario | Expected decision | Proposed action |
| --- | --- | --- | --- |
| 1 | Compliant invoice | Post | None |
| 2 | Price variance of 2 % or less | Post | None |
| 3 | Price variance above 2 % | Human review | Ask for a credit note |
| 4 | Quantity invoiced above quantity received | Human review | Wait for the delivery, or ask for a credit note |
| 5 | No purchase order reference, reworded labels | Post, once the purchase order is found | None |
| 6 | Duplicate of an invoice already posted | Reject | Report the duplicate to the supplier |
| 7 | Unknown supplier | Human review | Create the supplier record after verification |
| 8 | IBAN different from the supplier record | Human review, with a fraud alert | Call the supplier back on their usual number, never the one on the invoice |
| 9 | VAT error | Reject | Ask for a corrected invoice |
| 10 | Instruction hidden in the invoice | Human review, with a security alert | Report to IT security |
| 11 | Amount above 10,000 EUR excluding VAT | Human review | Get the manager's approval |

The thresholds are set in `rules.yaml`.
