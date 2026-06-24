# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {"from_date": filters.from_date, "to_date": filters.to_date}
	dt_filter = ""
	if filters.get("ref_doctype"):
		dt_filter = " AND v.ref_doctype = %(ref_doctype)s"
		params["ref_doctype"] = filters.ref_doctype

	rows = frappe.db.sql(
		f"""
		SELECT v.ref_doctype, COUNT(*) AS version_events
		FROM `tabVersion` v
		WHERE DATE(v.creation) BETWEEN %(from_date)s AND %(to_date)s
		{dt_filter}
		GROUP BY v.ref_doctype
		ORDER BY version_events DESC
		LIMIT 200
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("DocType"), "fieldname": "ref_doctype", "fieldtype": "Data", "width": 220},
		{"label": _("Version events"), "fieldname": "version_events", "fieldtype": "Int", "width": 140},
	]
	return columns, rows
