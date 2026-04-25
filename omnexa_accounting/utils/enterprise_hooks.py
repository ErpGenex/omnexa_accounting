# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from omnexa_accounting.utils.enterprise_codes import ensure_entity_code


def ensure_item_code(doc, method=None):
	ensure_entity_code(doc, fieldname="item_code", prefix="ITM-", digits=5)


def ensure_customer_code(doc, method=None):
	ensure_entity_code(doc, fieldname="customer_code", prefix="CUST-", digits=5)


def ensure_supplier_code(doc, method=None):
	ensure_entity_code(doc, fieldname="supplier_code", prefix="SUP-", digits=5)


def ensure_employee_code(doc, method=None):
	ensure_entity_code(doc, fieldname="employee_code", prefix="EMP-", digits=5)

