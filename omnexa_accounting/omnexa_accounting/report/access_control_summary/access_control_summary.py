# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = ["1=1"]
	params = {}
	if filters.get("company"):
		conditions.append("(up.allow = 'Company' AND up.for_value = %(company)s)")
		params["company"] = filters.company
	rows = frappe.db.sql(
		f"""
		SELECT
			up.`user` AS `user`,
			COUNT(*) AS permission_rows
		FROM `tabUser Permission` up
		WHERE {' AND '.join(conditions)}
		GROUP BY up.`user`
		ORDER BY permission_rows DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 200},
		{"label": _("Permission rows"), "fieldname": "permission_rows", "fieldtype": "Int", "width": 140},
	]
	return columns, rows
