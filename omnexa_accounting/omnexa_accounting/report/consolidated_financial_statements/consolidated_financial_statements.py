# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""IFRS 10 / IAS 1 — multi-company financial statement pack with intercompany elimination."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt

from omnexa_accounting.omnexa_accounting.report.balance_sheet.balance_sheet import execute as balance_sheet_execute
from omnexa_accounting.omnexa_accounting.report.income_statement.income_statement import execute as income_statement_execute
from omnexa_accounting.utils.consolidation_elimination import build_consolidated_statement_rows
from omnexa_accounting.utils.report_bilingual import insert_account_name_ar_column


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

	apply_eliminations = cint(filters.get("apply_eliminations", 1))
	show_consolidated = cint(filters.get("show_consolidated_total", 1))
	show_elimination_detail = cint(filters.get("show_elimination_detail", 0))

	columns = insert_account_name_ar_column(
		[
			{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 130
	},
			{"label": _("Statement"), "fieldname": "statement", "fieldtype": "Data", "width": 120
	},
			{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 120
	},
			{"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 150
	},
			{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 200
	},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140
	},
		]
	)

	data = []
	for co in companies:
		bs_filters = frappe._dict(company=co, to_date=filters.to_date)
		_bs_cols, bs_rows = balance_sheet_execute(bs_filters)
		for row in bs_rows or []:
			data.append(
				{
					"company": co,
					"statement": _("Balance Sheet"),
					"section": row.get("section"),
					"account": row.get("account"),
					"account_name": row.get("account_name"),
					"account_name_ar": row.get("account_name_ar"),
					"amount": flt(row.get("balance"))
	}
			)

		is_filters = frappe._dict(company=co, from_date=filters.from_date, to_date=filters.to_date)
		_is_cols, is_rows = income_statement_execute(is_filters)
		for row in is_rows or []:
			data.append(
				{
					"company": co,
					"statement": _("Income Statement"),
					"section": row.get("section"),
					"account": row.get("account"),
					"account_name": row.get("account_name"),
					"account_name_ar": row.get("account_name_ar"),
					"amount": flt(row.get("amount"))
	}
			)

	msg_parts = []
	if len(companies) > 1 and apply_eliminations and show_consolidated:
		data.extend(
			build_consolidated_statement_rows(
				companies,
				from_date=filters.from_date,
				to_date=filters.to_date,
				statement="balance_sheet",
				per_company_rows=data,
				show_elimination_detail=show_elimination_detail,
			)
		)
		data.extend(
			build_consolidated_statement_rows(
				companies,
				from_date=filters.from_date,
				to_date=filters.to_date,
				statement="income_statement",
				per_company_rows=data,
				show_elimination_detail=show_elimination_detail,
			)
		)
		msg_parts.append(
			_("Consolidated and elimination rows use intercompany GL accounts and consolidation codes.")
		)
	elif len(companies) > 1:
		msg_parts.append(_("Per-company detail only — enable Apply Eliminations for group totals."))
	else:
		msg_parts.append(_("Single company — consolidated elimination not required."))

	return columns, data, " ".join(msg_parts), None, None, False
