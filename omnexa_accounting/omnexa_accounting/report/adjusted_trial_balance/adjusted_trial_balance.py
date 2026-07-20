# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Adjusted Trial Balance — book balances plus audit adjustment entries (entry_type = Adjustment)."""

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_accounting.utils.report_bilingual import (
	gl_account_name_ar_select,
	has_gl_account_name_ar,
	insert_account_name_ar_column,
)

ADJUSTMENT_ENTRY_TYPE = "Adjustment"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company = filters.get("company")
	if not company:
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	columns = insert_account_name_ar_column(
		[
			{"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "GL Account", "width": 180
	},
			{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 180
	},
			{"label": _("Account Type"), "fieldname": "account_type", "fieldtype": "Data", "width": 100
	},
		]
	)
	columns += [
		{"label": _("Opening Dr"), "fieldname": "opening_debit", "fieldtype": "Currency", "width": 110
	},
		{"label": _("Opening Cr"), "fieldname": "opening_credit", "fieldtype": "Currency", "width": 110
	},
		{"label": _("Book Period Dr"), "fieldname": "book_period_debit", "fieldtype": "Currency", "width": 110
	},
		{"label": _("Book Period Cr"), "fieldname": "book_period_credit", "fieldtype": "Currency", "width": 110
	},
		{"label": _("Adjustment Dr"), "fieldname": "adjustment_debit", "fieldtype": "Currency", "width": 110
	},
		{"label": _("Adjustment Cr"), "fieldname": "adjustment_credit", "fieldtype": "Currency", "width": 110
	},
		{"label": _("Adjusted Closing Dr"), "fieldname": "closing_debit", "fieldtype": "Currency", "width": 120
	},
		{"label": _("Adjusted Closing Cr"), "fieldname": "closing_credit", "fieldtype": "Currency", "width": 120
	},
	]

	data = _build_rows(filters)
	return columns, data, None, None


def _build_rows(filters):
	conditions = ["je.company = %(company)s", "je.docstatus = 1"]
	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return []
		filters.allowed_branches = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	if filters.get("branch"):
		conditions.append("je.branch = %(branch)s")

	opening_condition = "je.posting_date < %(from_date)s"
	period_condition = "je.posting_date between %(from_date)s and %(to_date)s"
	book_period_condition = f"{period_condition} AND COALESCE(je.entry_type, 'Standard') != %(adjustment_entry_type)s"
	adjustment_condition = f"{period_condition} AND je.entry_type = %(adjustment_entry_type)s"
	filters.adjustment_entry_type = ADJUSTMENT_ENTRY_TYPE

	rows = frappe.db.sql(
		f"""
		SELECT
			jea.account,
			ga.account_name,
			{gl_account_name_ar_select()} AS account_name_ar,
			COALESCE(NULLIF(ga.account_type, ''), 'Unclassified') AS account_type,
			SUM(CASE WHEN {opening_condition} THEN jea.debit ELSE 0 END) AS opening_debit,
			SUM(CASE WHEN {opening_condition} THEN jea.credit ELSE 0 END) AS opening_credit,
			SUM(CASE WHEN {book_period_condition} THEN jea.debit ELSE 0 END) AS book_period_debit,
			SUM(CASE WHEN {book_period_condition} THEN jea.credit ELSE 0 END) AS book_period_credit,
			SUM(CASE WHEN {adjustment_condition} THEN jea.debit ELSE 0 END) AS adjustment_debit,
			SUM(CASE WHEN {adjustment_condition} THEN jea.credit ELSE 0 END) AS adjustment_credit
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {' AND '.join(conditions)}
		GROUP BY jea.account, ga.account_name{", ga.account_name_ar" if has_gl_account_name_ar() else ""}, ga.account_type
		HAVING opening_debit <> 0 OR opening_credit <> 0
			OR book_period_debit <> 0 OR book_period_credit <> 0
			OR adjustment_debit <> 0 OR adjustment_credit <> 0
		ORDER BY ga.account_type, ga.account_number, ga.account_name
		""",
		filters,
		as_dict=True,
	)

	data = []
	for row in rows:
		opening_balance = flt(row.opening_debit) - flt(row.opening_credit)
		period_balance = (
			(flt(row.book_period_debit) - flt(row.book_period_credit))
			+ (flt(row.adjustment_debit) - flt(row.adjustment_credit))
		)
		closing_balance = opening_balance + period_balance
		data.append(
			{
				**row,
				"closing_debit": closing_balance if closing_balance > 0 else 0,
				"closing_credit": abs(closing_balance) if closing_balance < 0 else 0
	}
		)
	return data
