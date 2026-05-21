# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""IFRS 10 / IAS 1 — multi-company financial statement pack (Balance Sheet + Income Statement)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_accounting.omnexa_accounting.report.balance_sheet.balance_sheet import execute as balance_sheet_execute
from omnexa_accounting.omnexa_accounting.report.income_statement.income_statement import execute as income_statement_execute


def execute(filters=None):
	filters = frappe._dict(filters or {})
	raw = (filters.get("companies") or "").strip()
	companies = [c.strip() for c in raw.split(",") if c.strip()]
	if not companies:
		frappe.throw(_("Enter at least one company code."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	for co in companies:
		if not frappe.db.exists("Company", co):
			frappe.throw(_("Unknown company: {0}").format(co))

	columns = [
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 130},
		{"label": _("Statement"), "fieldname": "statement", "fieldtype": "Data", "width": 120},
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 120},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 150},
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 200},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
	]

	data = []
	for co in companies:
		bs_filters = frappe._dict(company=co, to_date=filters.to_date)
		_, bs_rows = balance_sheet_execute(bs_filters)
		for row in bs_rows or []:
			data.append(
				{
					"company": co,
					"statement": _("Balance Sheet"),
					"section": row.get("section"),
					"account": row.get("account"),
					"account_name": row.get("account_name"),
					"amount": flt(row.get("balance")),
				}
			)

		is_filters = frappe._dict(company=co, from_date=filters.from_date, to_date=filters.to_date)
		_, is_rows = income_statement_execute(is_filters)
		for row in is_rows or []:
			data.append(
				{
					"company": co,
					"statement": _("Income Statement"),
					"section": row.get("section"),
					"account": row.get("account"),
					"account_name": row.get("account_name"),
					"amount": flt(row.get("amount")),
				}
			)

	msg = _("Consolidated pack lists each company separately — elimination entries are not auto-generated.")
	return columns, data, msg, None, None, False
