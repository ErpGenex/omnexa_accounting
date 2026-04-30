from __future__ import annotations

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": "Stock Entry", "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 170},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
		{"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
		{"label": "From Warehouse", "fieldname": "from_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 170},
		{"label": "To Warehouse", "fieldname": "to_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 170},
		{"label": "Item", "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 120},
		{"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 100},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": "Transfer Request", "fieldname": "transfer_request", "fieldtype": "Link", "options": "Stock Transfer Request", "width": 170},
	]

	conditions = ["se.docstatus = 1", "se.purpose = 'Material Transfer'"]
	params = {}
	for f in ("company", "branch", "from_warehouse", "to_warehouse"):
		if filters.get(f):
			conditions.append(f"se.{f} = %({f})s")
			params[f] = filters.get(f)
	if filters.get("item"):
		conditions.append("sei.item = %(item)s")
		params["item"] = filters.item
	if filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	data = frappe.db.sql(
		f"""
		SELECT
			se.posting_date,
			se.name AS stock_entry,
			se.company,
			se.branch,
			COALESCE(sei.s_warehouse, se.from_warehouse) AS from_warehouse,
			COALESCE(sei.t_warehouse, se.to_warehouse) AS to_warehouse,
			sei.item,
			sei.item_code,
			sei.qty,
			sei.rate,
			sei.amount,
			COALESCE(se.transfer_request, '') AS transfer_request
		FROM `tabStock Entry` se
		INNER JOIN `tabStock Entry Item` sei
			ON sei.parent = se.name AND sei.parenttype='Stock Entry'
		WHERE {" AND ".join(conditions)}
		ORDER BY se.posting_date DESC, se.modified DESC
		""",
		params,
		as_dict=True,
	)
	return columns, data

