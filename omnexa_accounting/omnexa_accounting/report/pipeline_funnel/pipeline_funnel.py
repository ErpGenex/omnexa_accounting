import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 160},
		{"label": _("Opportunities"), "fieldname": "opportunity_count", "fieldtype": "Int", "width": 120},
		{"label": _("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 140},
		{"label": _("Weighted Amount"), "fieldname": "weighted_amount", "fieldtype": "Currency", "width": 150},
	]

	conditions = ["po.docstatus < 2"]
	params = {}

	if filters.get("company"):
		conditions.append("po.company = %(company)s")
		params["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("po.closing_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("po.closing_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	data = frappe.db.sql(
		f"""
		SELECT
			po.stage,
			COUNT(po.name) AS opportunity_count,
			COALESCE(SUM(po.amount), 0) AS total_amount,
			COALESCE(SUM(po.amount * (po.probability / 100.0)), 0) AS weighted_amount
		FROM `tabPipeline Opportunity` po
		WHERE {" AND ".join(conditions)}
		GROUP BY po.stage
		ORDER BY opportunity_count DESC, total_amount DESC
		""",
		params,
		as_dict=True,
	)
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart