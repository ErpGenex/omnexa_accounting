# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Receipts vs payments from Payment Entry (MVP liquidity view — not full IAS 7 cash flow statement)."""

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}

	conditions = [
		"pe.company = %(company)s",
		"pe.docstatus = 1",
		"pe.posting_date BETWEEN %(from_date)s AND %(to_date)s",
	]

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _empty()
		params["allowed_branches"] = tuple(allowed)
		conditions.append("pe.branch in %(allowed_branches)s")

	if filters.get("branch"):
		conditions.append("pe.branch = %(branch)s")
		params["branch"] = filters.branch

	where_sql = " AND ".join(conditions)

	row = frappe.db.sql(
		f"""
		SELECT
			COALESCE(SUM(CASE WHEN pe.party_type = 'Customer' THEN pe.paid_amount ELSE 0 END), 0) AS receipts,
			COALESCE(SUM(CASE WHEN pe.party_type = 'Supplier' THEN pe.paid_amount ELSE 0 END), 0) AS payments
		FROM `tabPayment Entry` pe
		WHERE {where_sql}
		""",
		params,
		as_dict=True,
	)
	r = row[0] if row else {}
	receipts = flt(r.get("receipts"))
	payments = flt(r.get("payments"))
	net = flt(receipts - payments)

	columns = [
		{"label": _("Metric"), "fieldname": "metric", "fieldtype": "Data", "width": 280},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 160},
	]

	data = [
		{"metric": _("Receipts from customers (Payment Entry)"), "amount": receipts},
		{"metric": _("Payments to suppliers (Payment Entry)"), "amount": payments},
		{"metric": _("Net liquidity movement (receipts − payments)"), "amount": net},
	]

	report_summary = [
		{"value": receipts, "label": _("Receipts"), "datatype": "Currency"},
		{"value": payments, "label": _("Payments"), "datatype": "Currency"},
		{"value": net, "label": _("Net"), "datatype": "Currency"},
	]

	msg = _(
		"Simplified cash activity from Payment Entry only — not a full Cash Flow Statement (operating/investing/financing)."
	)

	return columns, data, msg, None, report_summary, True


def _empty():
	columns = [
		{"label": _("Metric"), "fieldname": "metric", "fieldtype": "Data", "width": 280},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 160},
	]
	return columns, [], None, None, [], True
