import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Purchase Invoice"), "fieldname": "name", "fieldtype": "Link", "options": "Purchase Invoice", "width": 170},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 140},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 200},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 110},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 90},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Base Grand Total"), "fieldname": "base_grand_total", "fieldtype": "Currency", "width": 140},
	]

	conditions = ["pi.docstatus = 1"]
	params = {}

	if filters.get("company"):
		conditions.append("pi.company = %(company)s")
		params["company"] = filters.company

	if filters.get("branch"):
		conditions.append("pi.branch = %(branch)s")
		params["branch"] = filters.branch

	if filters.get("supplier"):
		conditions.append("pi.supplier = %(supplier)s")
		params["supplier"] = filters.supplier

	if filters.get("from_date"):
		conditions.append("pi.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("pi.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	data = frappe.db.sql(
		f"""
		SELECT
			pi.posting_date,
			pi.name,
			pi.company,
			pi.branch,
			pi.supplier,
			pi.due_date,
			pi.currency,
			pi.grand_total,
			pi.outstanding_amount,
			pi.base_grand_total
		FROM `tabPurchase Invoice` pi
		WHERE {" AND ".join(conditions)}
		ORDER BY pi.posting_date DESC, pi.modified DESC
		""",
		params,
		as_dict=True,
	)
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart