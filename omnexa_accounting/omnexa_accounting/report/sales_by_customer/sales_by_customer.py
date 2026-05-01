# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
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
			return (
				[
					{
						"label": _("Customer"),
						"fieldname": "customer",
						"fieldtype": "Link",
						"options": "Customer",
						"width": 220,
					},
					{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
					{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
				],
				[],
			)
		params["allowed_branches"] = tuple(allowed)
		conditions.append("si.branch in %(allowed_branches)s")

	if filters.get("branch"):
		conditions.append("si.branch = %(branch)s")
		params["branch"] = filters.branch

	if filters.get("customer"):
		conditions.append("si.customer = %(customer)s")
		params["customer"] = filters.customer

	where_sql = " AND ".join(conditions)

	data = frappe.db.sql(
		f"""
		SELECT
			si.customer AS customer,
			SUM(sii.qty) AS qty,
			SUM(sii.amount) AS amount
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE {where_sql}
		GROUP BY si.customer
		ORDER BY amount DESC
		""",
		params,
		as_dict=True,
	)

	for row in data:
		row["qty"] = flt(row.get("qty"), 4)
		row["amount"] = flt(row.get("amount"), 2)

	columns = [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 220,
		},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
	]

	return columns, data, None, None, None, False
