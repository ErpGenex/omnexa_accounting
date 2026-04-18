# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Stock qty from Item × latest Purchase Invoice rate for the company (MVP valuation proxy)."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	params = {"company": filters.company}
	conditions = ["i.is_stock_item = 1", "(i.company = %(company)s OR IFNULL(i.company, '') = '')"]
	if filters.get("item"):
		conditions.append("i.name = %(item)s")
		params["item"] = filters.item

	where_sql = " AND ".join(conditions)

	data = frappe.db.sql(
		f"""
		SELECT
			i.name AS item,
			i.item_code,
			i.item_name,
			i.stock_uom,
			COALESCE(i.current_stock_qty, 0) AS qty,
			COALESCE(
				(
					SELECT pii.rate
					FROM `tabPurchase Invoice Item` pii
					INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
					WHERE pi.docstatus = 1
						AND pi.company = %(company)s
						AND pii.item_code = i.item_code
					ORDER BY pi.posting_date DESC, pi.modified DESC
					LIMIT 1
				),
				0
			) AS unit_cost,
			COALESCE(i.current_stock_qty, 0) * COALESCE(
				(
					SELECT pii.rate
					FROM `tabPurchase Invoice Item` pii
					INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
					WHERE pi.docstatus = 1
						AND pi.company = %(company)s
						AND pii.item_code = i.item_code
					ORDER BY pi.posting_date DESC, pi.modified DESC
					LIMIT 1
				),
				0
			) AS inventory_value
		FROM `tabItem` i
		WHERE {where_sql}
		ORDER BY i.item_code
		""",
		params,
		as_dict=True,
	)

	for row in data:
		row["qty"] = flt(row.get("qty"), 4)
		row["unit_cost"] = flt(row.get("unit_cost"), 4)
		row["inventory_value"] = flt(row.get("inventory_value"), 2)

	columns = [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 160},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Unit cost (last PI rate)"), "fieldname": "unit_cost", "fieldtype": "Currency", "width": 140},
		{"label": _("Inventory value"), "fieldname": "inventory_value", "fieldtype": "Currency", "width": 140},
	]

	msg = _("Valuation uses latest submitted Purchase Invoice line rate for the item in this company — not a full cost-layer / GL stock valuation.")
	return columns, data, msg, None, None, False
