# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Optional demo documents so workspace dashboard charts (Last Month / creation-based) are not empty.

Enable in site_config.json:

	"omnexa_feature_flags": {
		"demo_workspace_seed": true
	}

Idempotent: sets global default ``omnexa_demo_workspace_seeded`` after a full successful run; also skips if
marker customer "Omnexa Demo Seed" already exists (heals missing default).
"""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, get_table_name, now_datetime, today

from omnexa_core.omnexa_core.feature_flags import is_feature_enabled

DEMO_CUSTOMER_NAME = "Omnexa Demo Seed"
DEMO_ITEM_CODE = "OMNEXA-DEMO-ITEM"
DEMO_GL_ACCOUNT_NO = "OMN-DEMO-REV"
DEMO_WH_CODE = "OMN-DEMO-WH"
DEFAULT_KEY_SEEDED = "omnexa_demo_workspace_seeded"


def _backdate_creation(doctype: str, name: str, days_ago: int) -> None:
	dt = add_to_date(now_datetime(), days=-abs(days_ago), as_datetime=True)
	tn = get_table_name(doctype)
	frappe.db.sql(
		f"UPDATE `{tn}` SET `creation`=%s, `modified`=%s WHERE `name`=%s",
		(dt, dt, name),
	)


def _ensure_uom() -> None:
	if not frappe.db.exists("UOM", "Nos"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert(ignore_permissions=True)


def _get_company() -> str | None:
	try:
		c = frappe.defaults.get_user_default("company")
	except Exception:
		c = None
	if c and frappe.db.exists("Company", c):
		return c
	return frappe.db.get_value("Company", {}, "name", order_by="creation asc")


def _get_or_create_demo_revenue_gl(company: str) -> str:
	row = frappe.db.get_value(
		"GL Account", {"company": company, "account_number": DEMO_GL_ACCOUNT_NO}, "name"
	)
	if row:
		return row
	doc = frappe.new_doc("GL Account")
	doc.company = company
	doc.account_number = DEMO_GL_ACCOUNT_NO
	doc.account_name = "Omnexa Demo Revenue"
	doc.is_group = 0
	doc.account_type = "Income"
	doc.pl_bucket = "Revenue"
	doc.insert(ignore_permissions=True)
	return doc.name


def _get_or_create_demo_warehouse(company: str) -> str:
	row = frappe.db.get_value("Warehouse", {"warehouse_code": DEMO_WH_CODE, "company": company}, "name")
	if row:
		return row
	w = frappe.new_doc("Warehouse")
	w.company = company
	w.warehouse_name = "Omnexa Demo Warehouse"
	w.warehouse_code = DEMO_WH_CODE
	w.insert(ignore_permissions=True)
	return w.name


def _get_or_create_demo_item(company: str) -> str:
	row = frappe.db.get_value("Item", {"item_code": DEMO_ITEM_CODE, "company": company}, "name")
	if row:
		return row
	_ensure_uom()
	it = frappe.new_doc("Item")
	it.item_code = DEMO_ITEM_CODE
	it.item_name = DEMO_ITEM_CODE
	it.company = company
	it.stock_uom = "Nos"
	it.insert(ignore_permissions=True)
	return it.name


def ensure_demo_workspace_seed() -> None:
	"""Create a small submitted sales chain + CRM rows with staggered `creation` in the last month."""
	if frappe.flags.in_install or frappe.flags.in_uninstall:
		return
	if not is_feature_enabled("demo_workspace_seed"):
		return

	if frappe.db.get_default(DEFAULT_KEY_SEEDED) == "1":
		return
	if frappe.db.exists("Customer", {"customer_name": DEMO_CUSTOMER_NAME}):
		frappe.db.set_default(DEFAULT_KEY_SEEDED, "1")
		return

	company = _get_company()
	if not company:
		return

	currency = frappe.db.get_value("Company", company, "default_currency") or "EGP"
	item = _get_or_create_demo_item(company)
	rev = _get_or_create_demo_revenue_gl(company)
	wh = _get_or_create_demo_warehouse(company)

	try:
		cust = frappe.new_doc("Customer")
		cust.company = company
		cust.customer_name = DEMO_CUSTOMER_NAME
		cust.insert(ignore_permissions=True)

		sq = frappe.new_doc("Sales Quotation")
		sq.company = company
		sq.customer = cust.name
		sq.transaction_date = today()
		sq.currency = currency
		sq.append("items", {"item": item, "qty": 1, "rate": 100, "income_account": rev})
		sq.insert(ignore_permissions=True)
		sq.submit()
		_backdate_creation("Sales Quotation", sq.name, 22)

		so = frappe.new_doc("Sales Order")
		so.company = company
		so.customer = cust.name
		so.sales_quotation = sq.name
		so.transaction_date = today()
		so.currency = currency
		so.append("items", {"item": item, "qty": 1, "rate": 100, "income_account": rev})
		so.insert(ignore_permissions=True)
		so.submit()
		_backdate_creation("Sales Order", so.name, 18)

		dn = frappe.new_doc("Delivery Note")
		dn.company = company
		dn.customer = cust.name
		dn.sales_order = so.name
		dn.warehouse = wh
		dn.transaction_date = today()
		dn.append("items", {"item": item, "qty": 1, "rate": 100})
		dn.insert(ignore_permissions=True)
		dn.submit()
		_backdate_creation("Delivery Note", dn.name, 12)

		si = frappe.new_doc("Sales Invoice")
		si.company = company
		si.customer = cust.name
		si.posting_date = today()
		si.currency = currency
		si.sales_quotation = sq.name
		si.sales_order = so.name
		si.delivery_note = dn.name
		si.append("items", {"item": item, "qty": 1, "rate": 100, "income_account": rev})
		si.insert(ignore_permissions=True)
		si.submit()
		_backdate_creation("Sales Invoice", si.name, 6)

		if frappe.db.exists("DocType", "Pipeline Opportunity"):
			for days_ago, stage, title in (
				(14, "Qualified", "Omnexa demo opportunity A"),
				(9, "Proposal", "Omnexa demo opportunity B"),
			):
				po = frappe.new_doc("Pipeline Opportunity")
				po.company = company
				po.customer = cust.name
				po.opportunity_name = title
				po.stage = stage
				po.amount = 500
				po.insert(ignore_permissions=True)
				_backdate_creation("Pipeline Opportunity", po.name, days_ago)

		frappe.db.set_default(DEFAULT_KEY_SEEDED, "1")
	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), title="Omnexa demo workspace seed")
