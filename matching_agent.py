import asyncio
import sys
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.errors import GraphRecursionError

from extraction import extract_invoice, read_document
from llm import langchain_model
from models import SearchResult

INSTRUCTIONS = """You are an accounts payable matching agent. You are given a supplier invoice that has already been extracted.
Your task: find in the ERP the supplier and the purchase order that correspond to this invoice, then pair each invoice line with the purchase order line for the same item, even when the labels are worded differently.
Method: search for the supplier by name. If the invoice quotes a purchase order number, read that purchase order. Otherwise list the open purchase orders of the supplier, then read those whose amount or items correspond.
You only search and pair: you do not decide whether the invoice should be paid.
If no purchase order matches, answer with po_number set to null.
Always give your final answer by calling the SearchResult tool, never as plain text."""

REMINDER = "Give your final answer now by calling the SearchResult tool."
MAX_ATTEMPTS = 3

MCP_CLIENT = MultiServerMCPClient({
    "erp": {"transport": "stdio", "command": sys.executable,
            "args": [str(Path(__file__).parent / "mcp_server.py")]},
})


async def find_purchase_order_async(invoice):
    """Run the agent against the MCP server. Returns a SearchResult, or None if it gave up."""
    async with MCP_CLIENT.session("erp") as session:
        tools = await load_mcp_tools(session)
        # checkpointer=False: called from a graph node, the agent would otherwise inherit the parent's
        # synchronous SQLite checkpointer and fail on its first async call.
        agent = create_agent(langchain_model(), tools, system_prompt=INSTRUCTIONS,
                             response_format=ToolStrategy(SearchResult), checkpointer=False)
        messages = [{"role": "user", "content": "Here is the invoice:\n" + invoice.model_dump_json(indent=2)}]
        try:
            for attempt in range(MAX_ATTEMPTS):
                result = await agent.ainvoke(
                    {"messages": messages},
                    config={"recursion_limit": 20},   # hard stop: at most 20 steps in the agent loop
                )
                if result.get("structured_response") is not None:
                    break
                # The model sometimes ends on a sentence instead of the answer tool: ask again, keeping the history.
                messages = result["messages"] + [{"role": "user", "content": REMINDER}]
        except GraphRecursionError:
            return None
    for message in result["messages"]:   # trace of every tool call, with its arguments
        for call in getattr(message, "tool_calls", None) or []:
            print(f"    agent -> {call['name']}({call['args']})")
    return result.get("structured_response")


# One event loop for the whole program: asyncio.run() would create and close a new one on every call.
LOOP = asyncio.new_event_loop()


def find_purchase_order(invoice):
    """Synchronous version, callable from a graph node."""
    return LOOP.run_until_complete(find_purchase_order_async(invoice))


if __name__ == "__main__":
    for path in ["data/invoices/invoice_05.txt", "data/invoices/invoice_12.txt"]:
        print(path, "->", find_purchase_order(extract_invoice(read_document(path))))
