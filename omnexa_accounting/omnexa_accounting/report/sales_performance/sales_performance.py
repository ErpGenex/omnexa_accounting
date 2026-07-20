# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
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
		"si.company = %(company)s",
		"si.docstatus = 1",
		"IFNULL(si.is_return, 0) = 0",
		"si.posting_date BETWEEN %(from_date)s AND %(to_date)s",
	]
	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _cols(), []
		params["allowed_branches"] = tuple(allowed)
		conditions.append("si.branch in %(allowed_branches)s")
	if filters.get("branch"):
		conditions.append("si.branch = %(branch)s")
		params["branch"] = filters.branch

	rows = frappe.db.sql(
		f"""
		SELECT
			DATE_FORMAT(si.posting_date, '%%Y-%%m') AS period,
			COUNT(*) AS invoice_count,
			SUM(si.base_grand_total) AS net_sales,
			SUM(si.base_net_total) AS net_before_tax
		FROM `tabSales Invoice` si
		WHERE {' AND '.join(conditions)}
		GROUP BY DATE_FORMAT(si.posting_date, '%%Y-%%m')
		ORDER BY period
		""",
		params,
		as_dict=True,
	)
	for r in rows:
		r["net_sales"] = flt(r.get("net_sales"), 2)
		r["net_before_tax"] = flt(r.get("net_before_tax"), 2)
		cnt = int(r.get("invoice_count") or 0)
		r["invoice_count"] = cnt
		r["avg_invoice_value"] = flt((r["net_sales"] or 0) / cnt, 2) if cnt else 0.0
	columns = _cols()
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart
def _cols():
	return [
		{"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 100},
		{"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 90},
		{"label": _("Net sales (base)"), "fieldname": "net_sales", "fieldtype": "Currency", "width": 140},
		{"label": _("Net before tax (base)"), "fieldname": "net_before_tax", "fieldtype": "Currency", "width": 150},
		{"label": _("Avg invoice (base)"), "fieldname": "avg_invoice_value", "fieldtype": "Currency", "width": 140},
	]
