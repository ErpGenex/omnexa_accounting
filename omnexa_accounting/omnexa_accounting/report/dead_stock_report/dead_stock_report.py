from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	days = max(30, cint(filters.get("days") or 120))

	data = frappe.db.sql(
		"""
		SELECT
			i.name AS item,
			i.item_code,
			i.item_name,
			i.current_stock_qty,
			MAX(se.posting_date) AS last_movement_date
		FROM `tabItem` i
		LEFT JOIN `tabStock Entry Item` sei
			ON sei.item = i.name
		LEFT JOIN `tabStock Entry` se
			ON se.name = sei.parent AND se.docstatus=1
		WHERE i.company=%(company)s
		  AND IFNULL(i.is_stock_item,0)=1
		  AND IFNULL(i.disabled,0)=0
		GROUP BY i.name, i.item_code, i.item_name, i.current_stock_qty
		HAVING IFNULL(i.current_stock_qty,0) > 0
		   AND (last_movement_date IS NULL OR last_movement_date < DATE_SUB(CURDATE(), INTERVAL %(days)s DAY))
		ORDER BY i.current_stock_qty DESC, i.item_code
		""",
		{"company": filters.company, "days": days},
		as_dict=True,
	)

	columns = [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": _("Current Qty"), "fieldname": "current_stock_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Last Movement Date"), "fieldname": "last_movement_date", "fieldtype": "Date", "width": 130},
	]
	return columns, data

