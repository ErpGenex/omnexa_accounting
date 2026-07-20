# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	params: dict = {}
	where = "1=1"
	if filters.get("from_date"):
		where += " AND DATE(wa.modified) >= %(from_date)s"
		params["from_date"] = filters.from_date
	if filters.get("to_date"):
		where += " AND DATE(wa.modified) <= %(to_date)s"
		params["to_date"] = filters.to_date

	rows = frappe.db.sql(
		f"""
		SELECT
			IFNULL(wa.reference_doctype, '') AS reference_doctype,
			IFNULL(wa.status, '') AS status,
			COUNT(*) AS action_count
		FROM `tabWorkflow Action` wa
		WHERE {where}
		GROUP BY wa.reference_doctype, wa.status
		ORDER BY action_count DESC
		LIMIT 300
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Reference DocType"), "fieldname": "reference_doctype", "fieldtype": "Data", "width": 200
	},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100
	},
		{"label": _("Actions"), "fieldname": "action_count", "fieldtype": "Int", "width": 120
	},
	]
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart