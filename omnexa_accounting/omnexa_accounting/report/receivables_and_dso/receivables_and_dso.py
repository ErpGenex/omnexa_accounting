# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Open receivables, classic DSO vs rolling credit sales, and weighted aging by customer."""

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import add_days, flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))

	as_of = getdate(filters.get("as_of_date") or frappe.utils.today())
	period_days = max(int(filters.get("period_days") or 90), 1)
	period_start = add_days(as_of, -(period_days - 1))

	params = {"company": filters.company, "as_of": as_of, "period_start": period_start}

	open_ar_row = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(si.outstanding_amount), 0) AS open_ar
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.company = %(company)s
		  AND si.posting_date <= %(as_of)s
		""",
		params,
		as_dict=True,
	)
	open_ar = flt(open_ar_row[0].open_ar if open_ar_row else 0)

	credit_sales_row = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(si.base_grand_total), 0) AS credit_sales
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND IFNULL(si.is_return, 0) = 0
		  AND si.company = %(company)s
		  AND si.posting_date BETWEEN %(period_start)s AND %(as_of)s
		""",
		params,
		as_dict=True,
	)
	credit_sales = flt(credit_sales_row[0].credit_sales if credit_sales_row else 0)

	dso_days = None
	if credit_sales > 0 and open_ar >= 0:
		dso_days = flt((open_ar / credit_sales) * period_days, 1)

	weighted_row = frappe.db.sql(
		"""
		SELECT
			COALESCE(
				SUM(si.outstanding_amount * GREATEST(0, DATEDIFF(%(as_of)s, si.posting_date)))
				/ NULLIF(SUM(si.outstanding_amount), 0),
				0
			) AS wtd_days
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.company = %(company)s
		  AND si.posting_date <= %(as_of)s
		  AND si.outstanding_amount > 0
		  AND IFNULL(si.is_return, 0) = 0
		""",
		params,
		as_dict=True,
	)
	wtd_days = flt(weighted_row[0].wtd_days if weighted_row else 0, 1)

	report_summary = [
		{"value": open_ar, "label": _("Open AR (as of date)"), "datatype": "Currency", "currency": None},
		{
			"value": credit_sales,
			"label": _("Credit sales ({0} d)").format(period_days),
			"datatype": "Currency",
			"currency": None,
		},
		{
			"value": dso_days if dso_days is not None else 0.0,
			"label": _("DSO (days; 0 if no sales in period)"),
			"datatype": "Float",
		},
		{
			"value": wtd_days,
			"label": _("Weighted avg days (open invoices)"),
			"datatype": "Float",
		},
	]

	columns = [
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 220},
		{"label": _("Open AR"), "fieldname": "open_ar", "fieldtype": "Currency", "width": 140},
		{"label": _("Invoices"), "fieldname": "invoice_count", "fieldtype": "Int", "width": 90},
		{
			"label": _("Weighted days (posting → as of)"),
			"fieldname": "weighted_days",
			"fieldtype": "Float",
			"width": 160,
		},
	]

	data = frappe.db.sql(
		"""
		SELECT
			si.customer,
			SUM(si.outstanding_amount) AS open_ar,
			COUNT(*) AS invoice_count,
			SUM(si.outstanding_amount * GREATEST(0, DATEDIFF(%(as_of)s, si.posting_date)))
				/ NULLIF(SUM(si.outstanding_amount), 0) AS weighted_days
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.company = %(company)s
		  AND si.posting_date <= %(as_of)s
		GROUP BY si.customer
		HAVING ABS(SUM(si.outstanding_amount)) > 0.0001
		ORDER BY SUM(si.outstanding_amount) DESC
		""",
		params,
		as_dict=True,
	)

	message = _(
		"DSO = (Open AR ÷ credit sales in the rolling period) × period days. "
		"Credit sales exclude credit notes (is_return). Weighted days use only positive outstanding standard invoices."
	)

	return columns, data, message, None, report_summary, True
