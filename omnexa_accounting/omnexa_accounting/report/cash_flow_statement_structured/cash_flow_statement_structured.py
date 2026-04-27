# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Operating / Investing / Financing using Payment Entry + bank-side Journal Entry lines classified via GL Account → Cash Flow Section."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_accounting.utils.coa_settings import should_use_consolidation_view

_SECTIONS = ("Operating Activities", "Investing Activities", "Financing Activities")


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
	consolidation_view = should_use_consolidation_view(filters, filters.company)

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

	bank_gl = set(
		frappe.db.sql(
			"""SELECT DISTINCT gl_account FROM `tabBank Account` WHERE company = %(company)s AND IFNULL(gl_account,'') != ''""",
			{"company": filters.company},
			pluck=True,
		)
	)
	section_by_account = {
		r.name: (r.cash_flow_section or "").strip() or "Exclude"
		for r in frappe.db.get_all(
			"GL Account",
			filters={"company": filters.company},
			fields=["name", "cash_flow_section"],
		)
	}
	intercompany_accounts = set()
	if consolidation_view:
		intercompany_accounts = set(
			frappe.db.get_all(
				"GL Account",
				filters={"company": filters.company, "intercompany_account": 1},
				pluck="name",
			)
		)

	je_totals = defaultdict(float)
	intercompany_adjustment = 0.0
	if bank_gl:
		je_names = frappe.db.sql(
			f"""SELECT je.name FROM `tabJournal Entry` je WHERE {je_where}""",
			params,
			pluck=True,
		)
		for je_name in je_names:
			lines = frappe.db.sql(
				"""
				SELECT account, debit, credit
				FROM `tabJournal Entry Account`
				WHERE parent = %s
				""",
				je_name,
				as_dict=True,
			)
			bank_net = 0.0
			non_bank = []
			for L in lines:
				net = flt(L.debit) - flt(L.credit)
				if L.account in bank_gl:
					bank_net += net
				else:
					non_bank.append((L.account, abs(net)))
					if consolidation_view and L.account in intercompany_accounts:
						intercompany_adjustment += net
			if abs(bank_net) < 1e-9:
				continue
			section = "Operating Activities"
			if non_bank:
				dominant = max(non_bank, key=lambda x: x[1])[0]
				s = section_by_account.get(dominant, "Exclude")
				if s in _SECTIONS:
					section = s
			je_totals[section] += bank_net

	operating_pe = flt(receipts - payments)
	operating_je = flt(je_totals["Operating Activities"])
	investing = flt(je_totals["Investing Activities"])
	financing = flt(je_totals["Financing Activities"])
	net_change = flt(operating_pe + operating_je + investing + financing)
	if consolidation_view:
		net_change -= flt(intercompany_adjustment)

	columns = [
		{"label": _("Section / Line"), "fieldname": "label", "fieldtype": "Data", "width": 360},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
	]

	data = [
		{"label": _("Operating — receipts from customers (Payment Entry)"), "amount": receipts},
		{"label": _("Operating — payments to suppliers (Payment Entry, shown positive)"), "amount": payments},
		{"label": _("Operating — net Payment Entry (receipts − payments)"), "amount": operating_pe},
		{"label": _("Operating — Journal Entry via bank GL (classified)"), "amount": operating_je},
		{"label": _("Investing — Journal Entry via bank GL (classified)"), "amount": investing},
		{"label": _("Financing — Journal Entry via bank GL (classified)"), "amount": financing},
		{
			"label": _("Consolidation elimination — intercompany movement"),
			"amount": flt(intercompany_adjustment) if consolidation_view else 0,
		},
		{"label": _("Net change in cash (indicative)"), "amount": net_change},
	]

	report_summary = [
		{"value": operating_pe + operating_je, "label": _("Operating total"), "datatype": "Currency"},
		{"value": investing, "label": _("Investing"), "datatype": "Currency"},
		{"value": financing, "label": _("Financing"), "datatype": "Currency"},
		{"value": net_change, "label": _("Net"), "datatype": "Currency"},
	]

	msg = _(
		"Structured cash movements: Payment Entry customer/supplier flows default to Operating. "
		"Journal Entry lines on Bank Account GLs are allocated to Operating / Investing / Financing "
		"from the dominant non-bank line's GL Account → Cash Flow Section. Not a full IFRS 7 indirect statement."
	)

	return columns, data, msg, None, report_summary, True


def _empty():
	return (
		[
			{"label": _("Section / Line"), "fieldname": "label", "fieldtype": "Data", "width": 360},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
		],
		[],
		None,
		None,
		[],
		True,
	)
