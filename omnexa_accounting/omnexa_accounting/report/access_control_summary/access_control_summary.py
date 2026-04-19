# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	rows = frappe.db.sql(
		"""
		SELECT
			up.`user` AS `user`,
			COUNT(*) AS permission_rows
		FROM `tabUser Permission` up
		GROUP BY up.`user`
		ORDER BY permission_rows DESC
		LIMIT 500
		""",
		as_dict=True,
	)
	columns = [
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 200},
		{"label": _("Permission rows"), "fieldname": "permission_rows", "fieldtype": "Int", "width": 140},
	]
	return columns, rows
