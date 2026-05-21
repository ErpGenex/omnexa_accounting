import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = ["docstatus < 2", "ifnull(is_pos,0)=1"]
	params = {}
	if filters.get("company"):
		conditions.append("company = %(company)s")
		params["company"] = filters.company
	if filters.get("branch"):
		conditions.append("branch = %(branch)s")
		params["branch"] = filters.branch
	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date
	rows = frappe.db.sql(
		f"""
		SELECT
			name, company, branch, posting_date, customer, pos_profile, grand_total, outstanding_amount, docstatus
		FROM `tabSales Invoice`
		WHERE {' AND '.join(conditions)}
		ORDER BY posting_date DESC, modified DESC
		""",
		params,
		as_dict=True,
	)
	for row in rows:
		row["status"] = "Submitted" if int(row.docstatus or 0) == 1 else ("Cancelled" if int(row.docstatus or 0) == 2 else "Draft")
	columns = [
		{"label": _("Invoice"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 140},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": _("POS Profile"), "fieldname": "pos_profile", "fieldtype": "Link", "options": "POS Profile", "width": 130},
		{"label": _("Amount"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 130},
	]
	return columns, rows
