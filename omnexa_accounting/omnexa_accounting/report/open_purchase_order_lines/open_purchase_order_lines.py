# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Ordered vs received qty per PO line (matched by item_code on linked receipts)."""

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("as_of_date"):
		frappe.throw(_("As Of Date is required."), title=_("Filters"))

	params = {"company": filters.company, "as_of": filters.as_of_date
	}

	data = frappe.db.sql(
		"""
		SELECT
			po.name AS purchase_order,
			po.supplier,
			po.posting_date AS po_date,
			poi.item_code,
			poi.qty AS ordered_qty,
			COALESCE(rec.received_qty, 0) AS received_qty,
			(poi.qty - COALESCE(rec.received_qty, 0)) AS pending_qty,
			poi.amount AS line_amount
		FROM `tabPurchase Order` po
		INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		LEFT JOIN (
			SELECT
				pr.purchase_order,
				pri.item_code,
				SUM(pri.qty) AS received_qty
			FROM `tabPurchase Receipt` pr
			INNER JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
			WHERE pr.docstatus = 1
				AND IFNULL(pr.purchase_order, '') != ''
				AND pr.posting_date <= %(as_of)s
			GROUP BY pr.purchase_order, pri.item_code
		) rec ON rec.purchase_order = po.name AND rec.item_code = poi.item_code
		WHERE po.docstatus = 1
			AND po.company = %(company)s
			AND po.posting_date <= %(as_of)s
			AND (poi.qty - COALESCE(rec.received_qty, 0)) > 0.0001
		ORDER BY po.posting_date DESC, po.name, poi.idx
		""",
		params,
		as_dict=True,
	)

	for row in data:
		row["ordered_qty"] = flt(row.get("ordered_qty"), 4)
		row["received_qty"] = flt(row.get("received_qty"), 4)
		row["pending_qty"] = flt(row.get("pending_qty"), 4)
		row["line_amount"] = flt(row.get("line_amount"), 2)

	columns = [
		{"label": _("Purchase Order"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 160
	},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160
	},
		{"label": _("PO Date"), "fieldname": "po_date", "fieldtype": "Date", "width": 110
	},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 140
	},
		{"label": _("Ordered Qty"), "fieldname": "ordered_qty", "fieldtype": "Float", "width": 110
	},
		{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 110
	},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 110
	},
		{"label": _("Line Amount"), "fieldname": "line_amount", "fieldtype": "Currency", "width": 120
	},
	]

	msg = _(
		"Receipt quantities are summed from submitted Purchase Receipts linked to the PO with matching item_code "
		"(multiple PO lines with the same item_code share one received total)."
	)

	return columns, data, msg, None, None, False
