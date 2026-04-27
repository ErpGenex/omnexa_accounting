# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_accounting.utils.coa_settings import should_use_consolidation_view


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))

	columns = [
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 140},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 180},
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 220},
		{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 140},
	]

	consolidation_view = should_use_consolidation_view(filters, filters.company)
	assets = _rows_for_type(filters, "Asset", "Assets", consolidation_view=consolidation_view)
	liabilities = _rows_for_type(filters, "Liability", "Liabilities", consolidation_view=consolidation_view)
	equity = _rows_for_type(filters, "Equity", "Equity", consolidation_view=consolidation_view)

	data = assets + liabilities + equity
	return columns, data


def _rows_for_type(filters, account_type, section_label, consolidation_view=False):
	conditions = ["je.company = %(company)s", "je.docstatus = 1", "ga.account_type = %(account_type)s"]
	params = frappe._dict(filters.copy())
	params.account_type = account_type

	if filters.get("to_date"):
		conditions.append("je.posting_date <= %(to_date)s")

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return []
		params.allowed_branches = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	rows = frappe.db.sql(
		f"""
		SELECT
			jea.account,
			ga.account_name,
			ga.consolidation_account_code,
			SUM(jea.debit) AS total_debit,
			SUM(jea.credit) AS total_credit
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {' AND '.join(conditions)}
		GROUP BY jea.account, ga.account_name, ga.consolidation_account_code
		ORDER BY ga.account_number, ga.account_name
		""",
		params,
		as_dict=True,
	)

	data = []
	aggregate = {}
	for row in rows:
		if account_type == "Asset":
			balance = flt(row.total_debit) - flt(row.total_credit)
		else:
			balance = flt(row.total_credit) - flt(row.total_debit)
		account_display = row.account
		account_name = row.account_name
		if consolidation_view:
			account_display = (row.consolidation_account_code or row.account or "").strip()
			account_name = _("Consolidated Group")
			aggregate.setdefault(account_display, 0.0)
			aggregate[account_display] += balance
			continue
		data.append(
			{
				"section": _(section_label),
				"account": account_display,
				"account_name": account_name,
				"balance": balance,
			}
		)
	if consolidation_view:
		data = [
			{"section": _(section_label), "account": k, "account_name": _("Consolidated Group"), "balance": v}
			for k, v in sorted(aggregate.items())
		]
	return data
