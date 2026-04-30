from __future__ import annotations

import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = [
		{"label": "Quotation Date", "fieldname": "quotation_date", "fieldtype": "Date", "width": 110},
		{
			"label": "Purchase Quotation",
			"fieldname": "quotation",
			"fieldtype": "Link",
			"options": "Purchase Quotation",
			"width": 170,
		},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
		{"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
		{"label": "Purchase Request", "fieldname": "purchase_request", "fieldtype": "Link", "options": "Purchase Request", "width": 160},
		{"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 190},
		{"label": "Currency", "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 90},
		{"label": "Item", "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 160},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 120},
		{"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 80},
		{"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 110},
		{"label": "Discount %", "fieldname": "discount_percentage", "fieldtype": "Float", "width": 100},
		{"label": "Effective Rate", "fieldname": "effective_rate", "fieldtype": "Currency", "width": 120},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": "Is Best", "fieldname": "is_best", "fieldtype": "Check", "width": 70},
	]

	conditions = ["pq.docstatus = 1"]
	params = {}

	for f in ("company", "branch", "supplier", "purchase_request", "currency"):
		if filters.get(f):
			conditions.append(f"pq.{f} = %({f})s")
			params[f] = filters.get(f)

	if filters.get("from_date"):
		conditions.append("pq.quotation_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("pq.quotation_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("item"):
		conditions.append("pqi.item = %(item)s")
		params["item"] = filters.item

	if filters.get("item_code"):
		conditions.append("pqi.item_code = %(item_code)s")
		params["item_code"] = filters.item_code

	rows = frappe.db.sql(
		f"""
		SELECT
			pq.quotation_date,
			pq.name AS quotation,
			pq.company,
			pq.branch,
			pq.purchase_request,
			pq.supplier,
			pq.currency,
			pqi.item,
			pqi.item_code,
			pqi.qty,
			pqi.rate,
			pqi.discount_percentage,
			pqi.amount
		FROM `tabPurchase Quotation` pq
		INNER JOIN `tabPurchase Quotation Item` pqi
			ON pqi.parent = pq.name AND pqi.parenttype='Purchase Quotation'
		WHERE {" AND ".join(conditions)}
		ORDER BY pq.quotation_date DESC, pq.modified DESC
		""",
		params,
		as_dict=True,
	)

	# Compute effective rate and mark best offer per (purchase_request, item_code/item).
	best_key_to_rate = {}
	for r in rows:
		disc = flt(r.get("discount_percentage"))
		eff_rate = flt(r.get("rate")) * (1.0 - max(0.0, min(100.0, disc)) / 100.0)
		r["effective_rate"] = eff_rate
		key = (
			r.get("purchase_request") or "",
			r.get("company") or "",
			r.get("currency") or "",
			r.get("item") or "",
			r.get("item_code") or "",
			flt(r.get("qty") or 0),
		)
		prev = best_key_to_rate.get(key)
		if prev is None or eff_rate < prev:
			best_key_to_rate[key] = eff_rate

	for r in rows:
		key = (
			r.get("purchase_request") or "",
			r.get("company") or "",
			r.get("currency") or "",
			r.get("item") or "",
			r.get("item_code") or "",
			flt(r.get("qty") or 0),
		)
		r["is_best"] = 1 if flt(r.get("effective_rate")) == flt(best_key_to_rate.get(key) or 0) else 0

	chart = None
	if rows:
		# Chart top 8 suppliers by count of best offers in current result.
		best_counts = {}
		for r in rows:
			if r.get("is_best"):
				best_counts[r.get("supplier") or "Unknown"] = best_counts.get(r.get("supplier") or "Unknown", 0) + 1
		top = sorted(best_counts.items(), key=lambda x: x[1], reverse=True)[:8]
		if top:
			chart = {
				"data": {"labels": [t[0] for t in top], "datasets": [{"name": "Best Offers", "values": [t[1] for t in top]}]},
				"type": "bar",
			}

	report_summary = []
	if rows:
		report_summary = [
			{"label": "Quotations", "value": len({r.get("quotation") for r in rows}), "indicator": "Blue"},
			{"label": "Lines", "value": len(rows), "indicator": "Blue"},
			{"label": "Best Offers", "value": sum(1 for r in rows if r.get("is_best")), "indicator": "Green"},
		]

	return columns, rows, None, chart, report_summary

