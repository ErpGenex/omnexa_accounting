# Copyright (c) 2026, Omnexa and contributors
# License: MIT

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	if frappe.db.table_exists("Event Audit Log"):
		return _from_event_audit_log(filters)
	return _from_version_table(filters)


def _from_event_audit_log(filters):
	params = {"from_date": filters.from_date, "to_date": filters.to_date
	}
	conditions = ["DATE(creation) BETWEEN %(from_date)s AND %(to_date)s"]
	if filters.get("company"):
		params["company"] = filters.company
		conditions.append("company = %(company)s")
	if filters.get("event_name"):
		params["event_name"] = filters.event_name
		conditions.append("event_name = %(event_name)s")

	rows = frappe.db.sql(
		f"""
		SELECT creation, event_name, source_doctype, source_docname, action, company, branch, owner AS user
		FROM `tabEvent Audit Log`
		WHERE {" AND ".join(conditions)}
		ORDER BY creation DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Date"), "fieldname": "creation", "fieldtype": "Datetime", "width": 160
	},
		{"label": _("Event"), "fieldname": "event_name", "fieldtype": "Data", "width": 180
	},
		{"label": _("DocType"), "fieldname": "source_doctype", "fieldtype": "Data", "width": 160
	},
		{"label": _("Document"), "fieldname": "source_docname", "fieldtype": "Data", "width": 160
	},
		{"label": _("Action"), "fieldname": "action", "fieldtype": "Data", "width": 120
	},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120
	},
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 120
	},
	]
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart


def _from_version_table(filters):
	params = {"from_date": filters.from_date, "to_date": filters.to_date
	}
	rows = frappe.db.sql(
		"""
		SELECT creation, ref_doctype AS source_doctype, docname AS source_docname,
			'Version' AS event_name, owner AS user
		FROM `tabVersion`
		WHERE DATE(creation) BETWEEN %(from_date)s AND %(to_date)s
		ORDER BY creation DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)
	columns = [
		{"label": _("Date"), "fieldname": "creation", "fieldtype": "Datetime", "width": 160
	},
		{"label": _("Event"), "fieldname": "event_name", "fieldtype": "Data", "width": 140
	},
		{"label": _("DocType"), "fieldname": "source_doctype", "fieldtype": "Data", "width": 160
	},
		{"label": _("Document"), "fieldname": "source_docname", "fieldtype": "Data", "width": 160
	},
		{"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 120
	},
	]
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, _("Fallback: Frappe Version table (Event Audit Log not available)."), chart
