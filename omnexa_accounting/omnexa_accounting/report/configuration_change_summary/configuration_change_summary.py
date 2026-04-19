# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

_CONFIG_DOCTYPES = (
	"System Settings",
	"Workflow",
	"Tax Category",
	"Tax Rule",
	"Company",
	"Currency Exchange Rate",
	"Workspace",
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	in_clause = ", ".join(["%s"] * len(_CONFIG_DOCTYPES))
	rows = frappe.db.sql(
		f"""
		SELECT v.ref_doctype, COUNT(*) AS version_events
		FROM `tabVersion` v
		WHERE DATE(v.creation) BETWEEN %s AND %s
			AND v.ref_doctype IN ({in_clause})
		GROUP BY v.ref_doctype
		ORDER BY version_events DESC
		""",
		tuple([filters.from_date, filters.to_date, *_CONFIG_DOCTYPES]),
		as_dict=True,
	)
	columns = [
		{"label": _("DocType"), "fieldname": "ref_doctype", "fieldtype": "Data", "width": 220},
		{"label": _("Version events"), "fieldname": "version_events", "fieldtype": "Int", "width": 140},
	]
	return columns, rows
