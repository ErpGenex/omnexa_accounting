# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {"from_date": filters.from_date, "to_date": filters.to_date}
	user_filter = ""
	if filters.get("user"):
		user_filter = " AND al.user = %(user)s"
		params["user"] = filters.user

	rows = frappe.db.sql(
		f"""
		SELECT al.user, COUNT(*) AS activity_count
		FROM `tabActivity Log` al
		WHERE DATE(al.creation) BETWEEN %(from_date)s AND %(to_date)s
		{user_filter}
		GROUP BY al.user
		ORDER BY activity_count DESC
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 200},
		{"label": _("Activity count"), "fieldname": "activity_count", "fieldtype": "Int", "width": 140},
	]
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart