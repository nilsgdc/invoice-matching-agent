import os

import pytest

from create_erp import create_erp

# The tests never call a model, but importing the extraction module builds the client.
os.environ.setdefault("LLM_API_KEY", "not-used-in-tests")


@pytest.fixture(scope="session", autouse=True)
def reference_erp():
    """Processing invoices changes the ERP: the tests always start from the reference data."""
    create_erp()
