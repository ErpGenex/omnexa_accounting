# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from omnexa_accounting.utils.report_charts import aging_bucket_chart


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	as_of = getdate(filters.get("as_of_date") or frappe.utils.today())

	params = {"company": filters.company, "as_of": as_of}

	data = frappe.db.sql(
		"""
		SELECT
			t.customer,
			t.aging_bucket,
			SUM(t.outstanding_amount) AS outstanding
		FROM (
			SELECT
				si.customer,
				si.outstanding_amount,
				CASE
					WHEN DATEDIFF(%(as_of)s, IFNULL(si.due_date, si.posting_date)) <= 0 THEN 'Current'
					WHEN DATEDIFF(%(as_of)s, IFNULL(si.due_date, si.posting_date)) BETWEEN 1 AND 30 THEN '1-30 days'
					WHEN DATEDIFF(%(as_of)s, IFNULL(si.due_date, si.posting_date)) BETWEEN 31 AND 60 THEN '31-60 days'
					WHEN DATEDIFF(%(as_of)s, IFNULL(si.due_date, si.posting_date)) BETWEEN 61 AND 90 THEN '61-90 days'
					ELSE '90+ days'
				END AS aging_bucket
			FROM `tabSales Invoice` si
			WHERE si.docstatus = 1
			  AND si.company = %(company)s
			  AND IFNULL(si.is_return, 0) = 0
			  AND si.posting_date <= %(as_of)s
			  AND si.outstanding_amount > 0.0001
		) t
		GROUP BY t.customer, t.aging_bucket
		ORDER BY t.customer, t.aging_bucket
		""",
		params,
		as_dict=True,
	)

	for row in data:
		row["outstanding"] = flt(row.get("outstanding"), 2)

	columns = [
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": _("Aging bucket"), "fieldname": "aging_bucket", "fieldtype": "Data", "width": 120},
		{"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 140},
	]

	message = _("Aging days from due date, or posting date if due date is empty. Open invoices only.")
	chart = aging_bucket_chart(data)

	return columns, data, message, chart, None, False
