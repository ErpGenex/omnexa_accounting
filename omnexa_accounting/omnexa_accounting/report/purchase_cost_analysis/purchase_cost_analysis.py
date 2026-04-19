# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}
	conditions = [
		"pi.company = %(company)s",
		"pi.docstatus = 1",
		"IFNULL(pi.is_return, 0) = 0",
		"pi.posting_date BETWEEN %(from_date)s AND %(to_date)s",
	]
	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _cols(), []
		params["allowed_branches"] = tuple(allowed)
		conditions.append("pi.branch in %(allowed_branches)s")
	if filters.get("branch"):
		conditions.append("pi.branch = %(branch)s")
		params["branch"] = filters.branch

	rows = frappe.db.sql(
		f"""
		SELECT
			pi.supplier,
			SUM(pi.base_grand_total) AS spend,
			COUNT(*) AS invoice_count
		FROM `tabPurchase Invoice` pi
		WHERE {' AND '.join(conditions)}
		GROUP BY pi.supplier
		ORDER BY spend DESC
		""",
		params,
		as_dict=True,
	)
	for r in rows:
		r["spend"] = flt(r.get("spend"), 2)
		r["invoice_count"] = int(r.get("invoice_count") or 0)
	return _cols(), rows


def _cols():
	return [
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 200},
		{"label": _("Spend (base)"), "fieldname": "spend", "fieldtype": "Currency", "width": 140},
		{"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 100},
	]
