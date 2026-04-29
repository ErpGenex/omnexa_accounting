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
DEMO_SUPPLIER_NAME = "Omnexa Demo Supplier"
DEMO_ITEM_CODE = "OMNEXA-DEMO-ITEM"
DEMO_GL_ACCOUNT_NO = "OMN-DEMO-REV"
DEMO_WH_CODE = "OMN-DEMO-WH"
DEMO_TAX_RULE_TITLE = "Omnexa Demo VAT 15%"
DEMO_TAX_GL_NO = "OMN-DEMO-TAX"
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


def _get_branch(company: str) -> str | None:
	try:
		b = frappe.defaults.get_user_default("branch")
	except Exception:
		b = None
	if b and frappe.db.exists("Branch", b):
		if frappe.db.get_value("Branch", b, "company") == company:
			return b
	return frappe.db.get_value("Branch", {"company": company}, "name", order_by="creation asc")


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


def _get_or_create_demo_supplier(company: str) -> str:
	row = frappe.db.get_value("Supplier", {"supplier_name": DEMO_SUPPLIER_NAME, "company": company}, "name")
	if row:
		return row
	sup = frappe.new_doc("Supplier")
	sup.company = company
	sup.supplier_name = DEMO_SUPPLIER_NAME
	sup.insert(ignore_permissions=True)
	return sup.name


def _find_leaf_gl(company: str, account_type: str | None = None) -> str | None:
	filters = {"company": company, "is_group": 0}
	if account_type:
		filters["account_type"] = account_type
	return frappe.db.get_value("GL Account", filters, "name")


def _get_tax_gl(company: str) -> str | None:
	return (
		_find_leaf_gl(company, account_type="Tax")
		or frappe.db.get_value(
			"GL Account",
			{"company": company, "is_group": 0, "account_name": ("like", "%Tax%")},
			"name",
		)
		or frappe.db.get_value(
			"GL Account",
			{"company": company, "is_group": 0, "account_name": ("like", "%VAT%")},
			"name",
		)
	)


def _get_or_create_demo_tax_gl(company: str) -> str | None:
	existing = _get_tax_gl(company)
	if existing:
		return existing

	# Create a dedicated tax GL account for demo seeding (best-effort).
	try:
		doc = frappe.new_doc("GL Account")
		doc.company = company
		doc.account_number = DEMO_TAX_GL_NO
		doc.account_name = "Omnexa Demo VAT Payable"
		doc.is_group = 0
		if doc.meta.has_field("account_type"):
			doc.account_type = "Tax"
		if doc.meta.has_field("is_tax_account"):
			doc.is_tax_account = 1
		doc.insert(ignore_permissions=True)
		return doc.name
	except Exception:
		return _get_tax_gl(company)


def _get_or_create_demo_tax_rule(company: str, tax_gl: str | None) -> str | None:
	if not tax_gl:
		return None
	existing = frappe.db.get_value("Tax Rule", {"title": DEMO_TAX_RULE_TITLE, "company": company}, "name")
	if existing:
		return existing
	doc = frappe.new_doc("Tax Rule")
	doc.title = DEMO_TAX_RULE_TITLE
	doc.company = company
	doc.valid_from = add_to_date(today(), days=-400)
	doc.valid_to = add_to_date(today(), days=400)
	doc.tax_type = "standard"
	doc.rate = 15
	doc.account_head = tax_gl
	doc.insert(ignore_permissions=True)
	return doc.name


def _get_cash_gl(company: str) -> str | None:
	return (
		_find_leaf_gl(company, account_type="Cash")
		or frappe.db.get_value(
			"GL Account",
			{"company": company, "is_group": 0, "account_name": ("like", "%Cash%")},
			"name",
		)
		or frappe.db.get_value(
			"GL Account",
			{"company": company, "is_group": 0, "account_name": ("like", "%Bank%")},
			"name",
		)
	)


def _get_expense_gl(company: str) -> str | None:
	return (
		_find_leaf_gl(company, account_type="Expense")
		or frappe.db.get_value(
			"GL Account",
			{"company": company, "is_group": 0, "account_name": ("like", "%Expense%")},
			"name",
		)
		or frappe.db.get_value(
			"GL Account",
			{"company": company, "is_group": 0, "account_name": ("like", "%Cost%")},
			"name",
		)
	)


def _is_full_demo_present(company: str) -> bool:
	"""Allow re-seeding when old seed is too small."""
	try:
		return (
			(frappe.db.count("Sales Invoice", {"company": company, "docstatus": 1}) or 0) >= 6
			and (frappe.db.count("Purchase Invoice", {"company": company, "docstatus": 1}) or 0) >= 6
			and (frappe.db.count("Stock Entry", {"company": company, "docstatus": 1}) or 0) >= 6
			and (frappe.db.count("Journal Entry", {"company": company, "docstatus": 1}) or 0) >= 6
		)
	except Exception:
		return False


def ensure_demo_workspace_seed() -> None:
	"""Create a complete demo dataset (12/6 months, tax-inclusive accounting, stock movements)."""
	if frappe.flags.in_install or frappe.flags.in_uninstall:
		return
	if not is_feature_enabled("demo_workspace_seed"):
		return

	company = _get_company()
	if not company:
		return
	branch = _get_branch(company)
	if not branch:
		return
	force = is_feature_enabled("demo_workspace_seed_force")
	if not force and frappe.db.get_default(DEFAULT_KEY_SEEDED) == "1" and _is_full_demo_present(company):
		return

	currency = frappe.db.get_value("Company", company, "default_currency") or "EGP"
	item = _get_or_create_demo_item(company)
	rev = _get_or_create_demo_revenue_gl(company)
	wh = _get_or_create_demo_warehouse(company)
	tax_gl = _get_or_create_demo_tax_gl(company)
	tax_rule = _get_or_create_demo_tax_rule(company, tax_gl)
	cash_gl = _get_cash_gl(company)
	expense_gl = _get_expense_gl(company)
	supplier_name = _get_or_create_demo_supplier(company)

	try:
		cust = frappe.db.get_value("Customer", {"customer_name": DEMO_CUSTOMER_NAME, "company": company}, "name")
		if cust:
			cust = frappe.get_doc("Customer", cust)
		else:
			cust = frappe.new_doc("Customer")
			cust.company = company
			cust.customer_name = DEMO_CUSTOMER_NAME
			cust.insert(ignore_permissions=True)

		# 12 months of stock activity + journal entries.
		for month_idx in range(12):
			days_ago = 30 * (month_idx + 1)
			receipt_qty = 20 + month_idx
			issue_qty = 10 + (month_idx % 5)

			se_in = frappe.new_doc("Stock Entry")
			se_in.company = company
			se_in.branch = branch
			se_in.purpose = "Material Receipt"
			se_in.posting_date = add_to_date(today(), days=-days_ago)
			se_in.to_warehouse = wh
			se_in.append(
				"items",
				{
					"item": item,
					"qty": receipt_qty,
					"t_warehouse": wh,
					"uom": "Nos",
					"rate": 35 + month_idx,
				},
			)
			se_in.insert(ignore_permissions=True)
			se_in.submit()
			_backdate_creation("Stock Entry", se_in.name, days_ago)

			se_out = frappe.new_doc("Stock Entry")
			se_out.company = company
			se_out.branch = branch
			se_out.purpose = "Material Issue"
			se_out.posting_date = add_to_date(today(), days=-(days_ago - 5))
			se_out.from_warehouse = wh
			se_out.append(
				"items",
				{
					"item": item,
					"qty": issue_qty,
					"s_warehouse": wh,
					"uom": "Nos",
					"rate": 35 + month_idx,
				},
			)
			se_out.insert(ignore_permissions=True)
			se_out.submit()
			_backdate_creation("Stock Entry", se_out.name, days_ago - 5)

			if cash_gl and expense_gl:
				je = frappe.new_doc("Journal Entry")
				je.company = company
				je.voucher_type = "Journal Entry"
				je.posting_date = add_to_date(today(), days=-(days_ago - 2))
				je.user_remark = f"Omnexa Demo Journal Month {month_idx + 1}"
				amount = 300 + (month_idx * 20)
				je.append("accounts", {"account": expense_gl, "debit_in_account_currency": amount})
				je.append("accounts", {"account": cash_gl, "credit_in_account_currency": amount})
				je.insert(ignore_permissions=True)
				je.submit()
				_backdate_creation("Journal Entry", je.name, days_ago - 2)

		# 6 months of sales/purchase cycle including taxes.
		for month_idx in range(6):
			days_ago = 30 * (month_idx + 1)
			qty = 2 + month_idx
			rate = 120 + (month_idx * 10)
			purchase_rate = 70 + (month_idx * 7)

			si = frappe.new_doc("Sales Invoice")
			si.company = company
			si.branch = branch
			si.customer = cust.name
			si.posting_date = add_to_date(today(), days=-days_ago)
			si.posting_date = add_to_date(today(), days=-days_ago)
			si.currency = currency
			if tax_rule:
				si.default_tax_rule = tax_rule
			si.append("items", {"item": item, "qty": qty, "rate": rate, "income_account": rev, "warehouse": wh})
			# Credit invoice with installment schedule (2 payments).
			if si.meta.has_field("payment_mode"):
				si.payment_mode = "Installment"
			grand_est = float(qty * rate) * 1.15 if tax_rule else float(qty * rate)
			si.append("payment_schedule", {"due_date": add_to_date(si.posting_date, days=30), "payment_amount": grand_est / 2})
			si.append("payment_schedule", {"due_date": add_to_date(si.posting_date, days=60), "payment_amount": grand_est / 2})
			si.insert(ignore_permissions=True)
			si.submit()
			_backdate_creation("Sales Invoice", si.name, days_ago)

			pi = frappe.new_doc("Purchase Invoice")
			pi.company = company
			pi.branch = branch
			pi.supplier = supplier_name
			pi.posting_date = add_to_date(today(), days=-(days_ago - 3))
			pi.currency = currency
			if tax_rule:
				pi.default_tax_rule = tax_rule
			pi.append("items", {"item": item, "qty": qty, "rate": purchase_rate, "warehouse": wh})
			if pi.meta.has_field("payment_mode"):
				pi.payment_mode = "Installment"
			grand_est_pi = float(qty * purchase_rate) * 1.15 if tax_rule else float(qty * purchase_rate)
			pi.append(
				"payment_schedule",
				{"due_date": add_to_date(pi.posting_date, days=30), "payment_amount": grand_est_pi / 2},
			)
			pi.append(
				"payment_schedule",
				{"due_date": add_to_date(pi.posting_date, days=60), "payment_amount": grand_est_pi / 2},
			)
			pi.insert(ignore_permissions=True)
			pi.submit()
			_backdate_creation("Purchase Invoice", pi.name, days_ago - 3)

		if frappe.db.exists("DocType", "Pipeline Opportunity"):
			for days_ago, stage, title in (
				(60, "Qualified", "Omnexa demo opportunity A"),
				(35, "Proposal", "Omnexa demo opportunity B"),
				(12, "Negotiation", "Omnexa demo opportunity C"),
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
		frappe.log_error(frappe.get_traceback(), "Omnexa demo workspace seed")
