# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt
from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_accounting.utils.report_bilingual import gl_account_name_ar_select, insert_account_name_ar_column


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company = filters.get("company")
	if not company:
		frappe.throw(_("Company filter is required."), title=_("Filters"))

	conditions = ["je.company = %(company)s", "je.docstatus = 1"]
	if filters.get("from_date"):
		conditions.append("je.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("je.posting_date <= %(to_date)s")
	if filters.get("account"):
		conditions.append("jea.account = %(account)s")
	if filters.get("branch"):
		conditions.append("je.branch = %(branch)s")
	allowed = get_allowed_branches(company=company)
	if allowed is not None:
		if not allowed:
			return columns, []
		filters.allowed_branches = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	columns = insert_account_name_ar_column(
		[
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "GL Account", "width": 170},
		],
		after="account",
	)
	columns += [
		{"label": _("Voucher"), "fieldname": "voucher", "fieldtype": "Link", "options": "Journal Entry", "width": 130},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 120},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 120},
		{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 120},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
		{"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 130},
	]

	rows = frappe.db.sql(
		f"""
		SELECT
			je.posting_date,
			jea.account,
			{gl_account_name_ar_select("ga")} AS account_name_ar,
			je.name AS voucher,
			jea.debit,
			jea.credit,
			je.branch,
			je.reference
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		LEFT JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {' AND '.join(conditions)}
		ORDER BY jea.account, je.posting_date, je.name, jea.idx
		""",
		filters,
		as_dict=True,
	)

	balances = {}
	data = []
	for row in rows:
		account = row.account
		balances[account] = flt(balances.get(account)) + flt(row.debit) - flt(row.credit)
		row.balance = balances[account]
		data.append(row)
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart