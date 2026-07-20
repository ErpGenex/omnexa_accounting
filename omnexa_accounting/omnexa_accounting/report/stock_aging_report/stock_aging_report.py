from __future__ import annotations

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))

	data = frappe.db.sql(
		"""
		SELECT
			i.name AS item,
			i.item_code,
			i.item_name,
			i.current_stock_qty,
			MAX(se.posting_date) AS last_movement_date,
			DATEDIFF(CURDATE(), MAX(se.posting_date)) AS aging_days
		FROM `tabItem` i
		LEFT JOIN `tabStock Entry Item` sei
			ON sei.item = i.name
		LEFT JOIN `tabStock Entry` se
			ON se.name = sei.parent AND se.docstatus=1
		WHERE i.company=%(company)s
		  AND IFNULL(i.is_stock_item,0)=1
		  AND IFNULL(i.disabled,0)=0
		GROUP BY i.name, i.item_code, i.item_name, i.current_stock_qty
		ORDER BY aging_days DESC, i.item_code
		""",
		{"company": filters.company
	},
		as_dict=True,
	)
	for r in data:
		r["stock_value"] = 0
		aging = r.get("aging_days")
		if aging is None:
			r["aging_bucket"] = "No Movement"
		elif aging <= 30:
			r["aging_bucket"] = "0-30"
		elif aging <= 60:
			r["aging_bucket"] = "31-60"
		elif aging <= 90:
			r["aging_bucket"] = "61-90"
		else:
			r["aging_bucket"] = "90+"

	columns = [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 150
	},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 130
	},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220
	},
		{"label": _("Current Qty"), "fieldname": "current_stock_qty", "fieldtype": "Float", "width": 110
	},
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 110
	},
		{"label": _("Last Movement Date"), "fieldname": "last_movement_date", "fieldtype": "Date", "width": 130
	},
		{"label": _("Aging Days"), "fieldname": "aging_days", "fieldtype": "Int", "width": 100
	},
		{"label": _("Aging Bucket"), "fieldname": "aging_bucket", "fieldtype": "Data", "width": 100
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart