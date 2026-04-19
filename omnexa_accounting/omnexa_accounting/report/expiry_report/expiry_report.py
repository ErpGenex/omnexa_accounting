# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	params = {"company": filters.company}
	date_filter_se = ""
	date_filter_pr = ""
	if filters.get("from_date"):
		params["from_date"] = filters.from_date
		date_filter_se = " AND se.posting_date >= %(from_date)s"
		date_filter_pr = " AND pr.posting_date >= %(from_date)s"
	if filters.get("to_date"):
		params["to_date"] = filters.to_date
		date_filter_se += " AND se.posting_date <= %(to_date)s"
		date_filter_pr += " AND pr.posting_date <= %(to_date)s"

	rows = frappe.db.sql(
		f"""
		SELECT * FROM (
			SELECT
				sei.batch_no AS batch_no,
				sei.item_code AS item_code,
				sei.item AS item,
				se.company AS company,
				se.posting_date AS posting_date,
				se.name AS voucher_no,
				'Stock Entry' AS source,
				NULL AS expiry_date
			FROM `tabStock Entry Item` sei
			INNER JOIN `tabStock Entry` se ON se.name = sei.parent
			WHERE se.docstatus = 1
				AND IFNULL(sei.batch_no, '') != ''
				AND se.company = %(company)s
				{date_filter_se}
			UNION ALL
			SELECT
				pri.batch_no AS batch_no,
				pri.item_code AS item_code,
				NULL AS item,
				pr.company AS company,
				pr.posting_date AS posting_date,
				pr.name AS voucher_no,
				'Purchase Receipt' AS source,
				NULL AS expiry_date
			FROM `tabPurchase Receipt Item` pri
			INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
			WHERE pr.docstatus = 1
				AND IFNULL(pri.batch_no, '') != ''
				AND pr.company = %(company)s
				{date_filter_pr}
		) t
		ORDER BY posting_date DESC, batch_no
		LIMIT 500
		""",
		params,
		as_dict=True,
	)

	columns = [
		{"label": _("Batch No."), "fieldname": "batch_no", "fieldtype": "Data", "width": 140},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 140},
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 160},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
		{"label": _("Voucher"), "fieldname": "voucher_no", "fieldtype": "Data", "width": 160},
		{"label": _("Source"), "fieldname": "source", "fieldtype": "Data", "width": 130},
		{
			"label": _("Expiry Date"),
			"fieldname": "expiry_date",
			"fieldtype": "Date",
			"width": 110,
		},
	]
	return columns, rows
