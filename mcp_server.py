"""MCP server exposing the ERP to the agent. Read-only: it has no tool that writes."""
import json

from mcp.server.fastmcp import FastMCP

import erp

server = FastMCP("erp-invoices")


@server.tool()
def search_suppliers(name: str) -> str:
    """Search the ERP for suppliers whose name contains the given text. Returns their identifier, name and IBAN."""
    return json.dumps(erp.search_suppliers(name), ensure_ascii=False)


@server.tool()
def list_open_purchase_orders(supplier_id: str) -> str:
    """List the open purchase orders of a supplier (ERP identifier, for example F001), with their date and total excluding VAT."""
    return json.dumps(erp.list_open_purchase_orders(supplier_id), ensure_ascii=False)


@server.tool()
def get_purchase_order(number: str) -> str:
    """Read a purchase order (for example PO-2026-105): its numbered lines (description, quantity, unit price excluding VAT) and the quantities received."""
    return json.dumps(erp.get_purchase_order(number), ensure_ascii=False)


if __name__ == "__main__":
    server.run()   # stdio transport by default
