# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_accounting.omnexa_accounting.report.trial_balance.trial_balance import _build_rows
from omnexa_accounting.utils.report_bilingual import insert_account_name_ar_column


def execute(filters=None):
	filters = frappe._dict(filters or {})
	raw = (filters.get("companies") or "").strip()
	companies = [c.strip() for c in raw.split(",") if c.strip()]
	if not companies:
		frappe.throw(_("Enter at least one company code."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	for c in companies:
		if not frappe.db.exists("Company", c):
			frappe.throw(_("Unknown company: {0}").format(c), title=_("Filters"))

	msg_parts = []
	if filters.get("branch") and len(companies) > 1:
		msg_parts.append(_("Branch filter is ignored when multiple companies are selected."))

	branch = filters.get("branch") if len(companies) == 1 else None

	columns = insert_account_name_ar_column(
		[
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "GL Account", "width": 170},
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 180},
		{"label": _("Account Type"), "fieldname": "account_type", "fieldtype": "Data", "width": 100},
		]
	)
	columns += [
		{"label": _("Opening Dr"), "fieldname": "opening_debit", "fieldtype": "Currency", "width": 110},
		{"label": _("Opening Cr"), "fieldname": "opening_credit", "fieldtype": "Currency", "width": 110},
		{"label": _("Period Dr"), "fieldname": "period_debit", "fieldtype": "Currency", "width": 110},
		{"label": _("Period Cr"), "fieldname": "period_credit", "fieldtype": "Currency", "width": 110},
		{"label": _("Closing Dr"), "fieldname": "closing_debit", "fieldtype": "Currency", "width": 110},
		{"label": _("Closing Cr"), "fieldname": "closing_credit", "fieldtype": "Currency", "width": 110},
	]

	data = []
	for co in companies:
		sub = frappe._dict(
			company=co,
			from_date=filters.from_date,
			to_date=filters.to_date,
			branch=branch,
		)
		for row in _build_rows(sub):
			row = dict(row)
			row["company"] = co
			data.append(row)

	msg = _("Same chart per company is not validated — rows are listed per company.") + (
		" " + msg_parts[0] if msg_parts else ""
	)
	return columns, data, msg, None, None, False
