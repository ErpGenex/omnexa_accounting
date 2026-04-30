from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	company = filters.company

	items = frappe.get_all(
		"Item",
		filters={"company": company, "is_stock_item": 1, "disabled": 0},
		fields=["name", "item_code", "item_name", "current_stock_qty", "reorder_level", "safety_stock"],
		limit_page_length=5000,
	)

	total_items = len(items)
	low_stock = 0
	dead_stock = 0
	total_qty = 0.0
	for it in items:
		qty = flt(it.get("current_stock_qty"))
		total_qty += qty
		threshold = max(flt(it.get("reorder_level")), flt(it.get("safety_stock")))
		if threshold > 0 and qty <= threshold:
			low_stock += 1
		last_move = frappe.db.sql(
			"""
			SELECT MAX(se.posting_date)
			FROM `tabStock Entry` se
			INNER JOIN `tabStock Entry Item` sei ON sei.parent = se.name
			WHERE se.docstatus=1 AND sei.item=%s
			""",
			(it["name"],),
		)
		last_dt = last_move[0][0] if last_move else None
		if qty > 0 and (not last_dt):
			dead_stock += 1

	columns = [
		{"label": _("KPI"), "fieldname": "kpi", "fieldtype": "Data", "width": 220},
		{"label": _("Value"), "fieldname": "value", "fieldtype": "Float", "width": 180},
	]
	data = [
		{"kpi": "Total Stock Items", "value": total_items},
		{"kpi": "Total On-hand Qty", "value": total_qty},
		{"kpi": "Low Stock Items", "value": low_stock},
		{"kpi": "Potential Dead Stock Items", "value": dead_stock},
	]

	chart = {
		"data": {
			"labels": [d["kpi"] for d in data],
			"datasets": [{"name": "Inventory KPIs", "values": [d["value"] for d in data]}],
		},
		"type": "bar",
	}
	report_summary = [
		{"label": "Total Items", "value": total_items, "indicator": "Blue"},
		{"label": "Low Stock", "value": low_stock, "indicator": "Orange" if low_stock else "Green"},
		{"label": "Dead Stock", "value": dead_stock, "indicator": "Red" if dead_stock else "Green"},
	]
	return columns, data, None, chart, report_summary

