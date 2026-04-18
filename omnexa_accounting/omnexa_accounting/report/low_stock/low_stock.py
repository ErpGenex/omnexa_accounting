# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	below = flt(filters.get("below_qty"), 3)
	if below < 0:
		below = 0.0

	conditions = ["i.company = %(company)s", "IFNULL(i.is_stock_item, 0) = 1", "IFNULL(i.disabled, 0) = 0"]
	params = {"company": filters.company, "below_qty": below}

	if filters.get("item"):
		conditions.append("i.name = %(item)s")
		params["item"] = filters.item

	conditions.append("IFNULL(i.current_stock_qty, 0) <= %(below_qty)s")

	where_sql = " AND ".join(conditions)

	data = frappe.db.sql(
		f"""
		SELECT
			i.name AS item,
			i.item_code,
			i.item_name,
			i.stock_uom,
			IFNULL(i.current_stock_qty, 0) AS current_stock_qty
		FROM `tabItem` i
		WHERE {where_sql}
		ORDER BY current_stock_qty ASC, i.item_code
		""",
		params,
		as_dict=True,
	)

	columns = [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 160},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 100},
		{
			"label": _("Current Stock Qty"),
			"fieldname": "current_stock_qty",
			"fieldtype": "Float",
			"width": 130,
		},
	]

	return columns, data
