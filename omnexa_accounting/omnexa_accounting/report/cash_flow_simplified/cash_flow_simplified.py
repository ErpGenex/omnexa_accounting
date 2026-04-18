# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Payment Entry liquidity plus Journal Entry lines on bank GL accounts — not IAS 7."""

import frappe
from frappe import _
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

	pe_conditions = [
		"pe.company = %(company)s",
		"pe.docstatus = 1",
		"pe.posting_date BETWEEN %(from_date)s AND %(to_date)s",
	]

	je_conditions = [
		"je.company = %(company)s",
		"je.docstatus = 1",
		"je.posting_date BETWEEN %(from_date)s AND %(to_date)s",
	]

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _empty()
		params["allowed_branches"] = tuple(allowed)
		pe_conditions.append("pe.branch in %(allowed_branches)s")
		je_conditions.append("je.branch in %(allowed_branches)s")

	if filters.get("branch"):
		params["branch"] = filters.branch
		pe_conditions.append("pe.branch = %(branch)s")
		je_conditions.append("je.branch = %(branch)s")

	pe_where = " AND ".join(pe_conditions)
	je_where = " AND ".join(je_conditions)

	row = frappe.db.sql(
		f"""
		SELECT
			COALESCE(SUM(CASE WHEN pe.party_type = 'Customer' THEN pe.paid_amount ELSE 0 END), 0) AS receipts,
			COALESCE(SUM(CASE WHEN pe.party_type = 'Supplier' THEN pe.paid_amount ELSE 0 END), 0) AS payments
		FROM `tabPayment Entry` pe
		WHERE {pe_where}
		""",
		params,
		as_dict=True,
	)
	r = row[0] if row else {}
	receipts = flt(r.get("receipts"))
	payments = flt(r.get("payments"))

	je_row = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(jea.debit - jea.credit), 0) AS bank_net
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabBank Account` ba ON ba.gl_account = jea.account AND ba.company = je.company
		WHERE {je_where}
		""",
		params,
		as_dict=True,
	)
	bank_je_net = flt(je_row[0].get("bank_net") if je_row else 0)

	pe_net = flt(receipts - payments)
	indicative_total = flt(pe_net + bank_je_net)

	columns = [
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 320},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 160},
	]

	data = [
		{"section": _("Receipts from customers (Payment Entry)"), "amount": receipts},
		{"section": _("Payments to suppliers (Payment Entry)"), "amount": payments},
		{"section": _("Net from Payment Entry (receipts − payments)"), "amount": pe_net},
		{"section": _("Bank / cash GL — Journal Entry (net debit − credit)"), "amount": bank_je_net},
		{"section": _("Indicative total (PE net + bank JE net)"), "amount": indicative_total},
	]

	report_summary = [
		{"value": receipts, "label": _("Receipts"), "datatype": "Currency"},
		{"value": payments, "label": _("Payments"), "datatype": "Currency"},
		{"value": indicative_total, "label": _("Indicative total"), "datatype": "Currency"},
	]

	msg = _(
		"Simplified view: Payment Entry party flows plus Journal Entry lines posted to Bank Account GL accounts. "
		"Not a full cash flow statement (IAS 7); may overlap if the same cash movement is recorded both as PE and JE."
	)

	return columns, data, msg, None, report_summary, True


def _empty():
	columns = [
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 320},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 160},
	]
	return columns, [], None, None, [], True
