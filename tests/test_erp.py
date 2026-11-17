import sqlite3

import pytest

from erp import (get_purchase_order, get_supplier, invoice_already_posted,
                 list_open_purchase_orders, read, search_suppliers)


def test_supplier_found_from_part_of_its_name():
    suppliers = search_suppliers("bureau plus")   # LIKE is case-insensitive
    assert [s["id"] for s in suppliers] == ["F001"]


def test_unknown_supplier():
    assert search_suppliers("Globex") == []


def test_get_supplier():
    assert get_supplier("F003")["name"] == "Café & Co"
    assert get_supplier("F999") is None


def test_missing_purchase_order():
    assert get_purchase_order("PO-0000-000") is None


def test_partial_receipt():
    purchase_order = get_purchase_order("PO-2026-104")
    assert purchase_order["lines"][1]["quantity_received"] == 6   # 6 boxes received out of 10


def test_open_purchase_orders_sorted_by_date():
    numbers = [p["number"] for p in list_open_purchase_orders("F001")]
    assert numbers == ["PO-2026-101", "PO-2026-105", "PO-2026-112", "PO-2026-108"]


def test_duplicate_detected():
    assert invoice_already_posted("F002", "FAC-IT-0457")
    assert not invoice_already_posted("F002", "FAC-IT-0461")


def test_read_connection_cannot_write():
    with pytest.raises(sqlite3.OperationalError):
        read("DELETE FROM suppliers")
