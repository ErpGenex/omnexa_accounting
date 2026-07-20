import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Sales Invoice"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 170},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 110},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 90},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Base Grand Total"), "fieldname": "base_grand_total", "fieldtype": "Currency", "width": 140},
	]

	conditions = ["si.docstatus = 1"]
	params = {}

	if filters.get("company"):
		conditions.append("si.company = %(company)s")
		params["company"] = filters.company

	if filters.get("branch"):
		conditions.append("si.branch = %(branch)s")
		params["branch"] = filters.branch

	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		params["customer"] = filters.customer

	if filters.get("from_date"):
		conditions.append("si.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("si.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	data = frappe.db.sql(
		f"""
		SELECT
			si.posting_date,
			si.name,
			si.company,
			si.branch,
			si.customer,
			si.due_date,
			si.currency,
			si.grand_total,
			si.outstanding_amount,
			si.base_grand_total
		FROM `tabSales Invoice` si
		WHERE {" AND ".join(conditions)}
		ORDER BY si.posting_date DESC, si.modified DESC
		""",
		params,
		as_dict=True,
	)
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart