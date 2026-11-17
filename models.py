from datetime import date

from pydantic import BaseModel, Field

# The field descriptions travel to the model inside the JSON schema,
# so they double as extraction instructions.


class InvoiceLine(BaseModel):
    description: str = Field(description="Item label, as written on the invoice")
    quantity: float = Field(description="Quantity invoiced, read from the quantity column. Do not confuse it with a number inside the label, such as '1 kg'.")
    unit_price_excl_vat: float = Field(description="Unit price excluding VAT (prix unitaire HT), in euros")


class Invoice(BaseModel):
    supplier: str = Field(description="Name of the company issuing the invoice")
    invoice_number: str = Field(description="Invoice number")
    invoice_date: date = Field(description="Issue date in YYYY-MM-DD format, year first. French invoices write day/month/year: 14/09/2026 is 2026-09-14.")
    po_number: str | None = Field(description="Purchase order number quoted on the invoice, or null if absent")
    iban: str | None = Field(description="Supplier IBAN for payment, without spaces, or null if absent")
    lines: list[InvoiceLine] = Field(description="The invoiced items")
    total_excl_vat: float = Field(description="Total amount excluding VAT (total HT)")
    vat_amount: float = Field(description="VAT amount (TVA)")
    total_incl_vat: float = Field(description="Total amount including VAT (total TTC)")


# Final answer of the matching agent.
class SearchResult(BaseModel):
    supplier_id: str | None = Field(description="ERP identifier of the supplier, for example F001, or null if not found")
    po_number: str | None = Field(description="Number of the purchase order that matches the invoice, or null if none matches")
    po_lines: list[int] = Field(description="For each invoice line, in order, the number of the purchase order line for the same item, or 0 if none matches")
    rationale: str = Field(description="One or two sentences: why this purchase order and these line matches")


# Brief prepared for the accountant when a human has to decide.
class Analysis(BaseModel):
    explanation: str = Field(description="For the accountant, in 2 to 4 plain sentences: what is wrong, with the figures involved")
    proposed_action: str = Field(description="The recommended action, in one sentence, for example: ask the supplier for a credit note")
    cited_alerts: list[str] = Field(description="The exact names of the alerts explained, copied from the list provided")
