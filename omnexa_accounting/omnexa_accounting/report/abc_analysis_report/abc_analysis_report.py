from __future__ import annotations

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))

	rows = frappe.db.sql(
		"""
		SELECT
			name AS item,
			item_code,
			item_name,
			current_stock_qty,
			IFNULL(current_stock_qty,0) * IFNULL(0,0) AS base_value
		FROM `tabItem`
		WHERE company=%(company)s
		  AND IFNULL(is_stock_item,0)=1
		  AND IFNULL(disabled,0)=0
		""",
		{"company": filters.company
	},
		as_dict=True,
	)
	# Derive proxy value from latest known item rate in stock entries.
	for r in rows:
		rate = frappe.db.sql(
			"""
			SELECT IFNULL(sei.rate,0)
			FROM `tabStock Entry Item` sei
			INNER JOIN `tabStock Entry` se ON se.name=sei.parent AND se.docstatus=1
			WHERE sei.item=%s
			ORDER BY se.posting_date DESC, se.modified DESC
			LIMIT 1
			""",
			(r["item"],),
		)
		last_rate = flt(rate[0][0]) if rate else 0
		r["last_rate"] = last_rate
		r["stock_value"] = flt(r.get("current_stock_qty")) * last_rate

	rows.sort(key=lambda x: flt(x.get("stock_value")), reverse=True)
	total_value = sum(flt(r.get("stock_value")) for r in rows) or 1.0
	running = 0.0
	for r in rows:
		running += flt(r.get("stock_value"))
		pct = (running / total_value) * 100.0
		r["cumulative_pct"] = pct
		if pct <= 70:
			r["abc_class"] = "A"
		elif pct <= 90:
			r["abc_class"] = "B"
		else:
			r["abc_class"] = "C"

	columns = [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 150
	},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 130
	},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220
	},
		{"label": _("Current Qty"), "fieldname": "current_stock_qty", "fieldtype": "Float", "width": 110
	},
		{"label": _("Last Rate"), "fieldname": "last_rate", "fieldtype": "Currency", "width": 100
	},
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 120
	},
		{"label": _("Cumulative %"), "fieldname": "cumulative_pct", "fieldtype": "Percent", "width": 110
	},
		{"label": _("ABC Class"), "fieldname": "abc_class", "fieldtype": "Data", "width": 80
	},
	]
	chart = auto_chart_for_columns(rows, columns)
	return columns, rows, None, chart