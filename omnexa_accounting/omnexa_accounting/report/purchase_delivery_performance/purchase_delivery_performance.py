# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Submitted POs with Expected Delivery Date vs first submitted Purchase Receipt on that PO."""

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	params = {"company": filters.company}
	conditions = [
		"po.docstatus = 1",
		"po.company = %(company)s",
		"po.expected_delivery_date IS NOT NULL",
	]
	if filters.get("from_date"):
		conditions.append("po.posting_date >= %(from_date)s")
		params["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("po.posting_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	where_sql = " AND ".join(conditions)

	data = frappe.db.sql(
		f"""
		SELECT
			po.name AS purchase_order,
			po.supplier,
			po.posting_date AS po_date,
			po.expected_delivery_date,
			fr.first_receipt_date AS first_receipt_date,
			CASE
				WHEN fr.first_receipt_date IS NOT NULL THEN
					DATEDIFF(fr.first_receipt_date, po.expected_delivery_date)
			END AS delay_days_vs_expected
		FROM `tabPurchase Order` po
		LEFT JOIN (
			SELECT purchase_order, MIN(posting_date) AS first_receipt_date
			FROM `tabPurchase Receipt`
			WHERE docstatus = 1 AND IFNULL(purchase_order, '') != ''
			GROUP BY purchase_order
		) fr ON fr.purchase_order = po.name
		WHERE {where_sql}
		ORDER BY po.posting_date DESC, po.name
		""",
		params,
		as_dict=True,
	)

	for row in data:
		if row.get("delay_days_vs_expected") is not None:
			row["delay_days_vs_expected"] = int(row["delay_days_vs_expected"])
		if row.get("first_receipt_date") and row.get("expected_delivery_date"):
			fd, ed = getdate(row["first_receipt_date"]), getdate(row["expected_delivery_date"])
			row["on_time"] = _("Yes") if fd <= ed else _("No")
		else:
			row["on_time"] = _("No receipt")

	columns = [
		{"label": _("Purchase Order"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
		{"label": _("PO Date"), "fieldname": "po_date", "fieldtype": "Date", "width": 110},
		{"label": _("Expected Delivery"), "fieldname": "expected_delivery_date", "fieldtype": "Date", "width": 130},
		{"label": _("First Receipt Date"), "fieldname": "first_receipt_date", "fieldtype": "Date", "width": 130},
		{"label": _("Delay (days vs expected)"), "fieldname": "delay_days_vs_expected", "fieldtype": "Int", "width": 130},
		{"label": _("On time"), "fieldname": "on_time", "fieldtype": "Data", "width": 100},
	]

	msg = _("Only Purchase Orders with Expected Delivery Date set are included.")
	return columns, data, msg, None, None, False
