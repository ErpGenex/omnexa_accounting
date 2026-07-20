# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_accounting.utils.partner_legal_reporting import (
	d,
	partner_debt_rows,
	resolve_partner_accounts,
	resolve_partner_labels,
	resolve_years,
	yearly_net_results,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	years = resolve_years(filters)
	secondary_pct = Decimal(str(filters.get("secondary_pct") or 20)) / Decimal("100")
	acc = resolve_partner_accounts(filters.company, filters, branch=filters.get("branch"))
	labels = resolve_partner_labels(filters)
	debt_rows = partner_debt_rows(
		company=filters.company,
		branch=filters.get("branch"),
		years=years,
		primary_current_account=acc["primary_current"],
		secondary_due_account=acc["secondary_due"],
		secondary_pct=secondary_pct,
	)
	net_by_year = yearly_net_results(filters.company, filters.get("branch"), years)
	loss_secondary = Decimal("0")
	for y in years:
		net = d(net_by_year.get(y))
		if net < 0:
			loss_secondary += -(net * secondary_pct)
	secondary_paid = d(sum(r["secondary_paid"] for r in debt_rows))
	closing_debt = d(debt_rows[-1]["cumulative_debt"] if debt_rows else 0)

	# Conservative legal certificate components:
	# Capital deficiency approximated through debt base (if partner did not settle share funding).
	capital_deficiency = d(sum(r["secondary_share"] for r in debt_rows))
	expense_deficiency = d(sum(r["debt_year"] for r in debt_rows))
	final_amount_due = closing_debt + loss_secondary

	rows = [
		{
			"line_no": 1,
			"component": _("Opening Balance"),
			"amount": 0.0,
			"notes": _("Opening balance for selected period."),
		},
		{
			"line_no": 2,
			"component": _("Capital Contribution Deficiency"),
			"amount": float(capital_deficiency),
			"notes": _("{0} unpaid ownership share of funding.").format(labels["secondary_partner_name"]),
		},
		{
			"line_no": 3,
			"component": _("Expense Contribution Deficiency"),
			"amount": float(expense_deficiency),
			"notes": _("{0} unpaid expense share across funded expenses.").format(labels["secondary_partner_name"]),
		},
		{
			"line_no": 4,
			"component": _("Loss Allocation"),
			"amount": float(loss_secondary),
			"notes": _("{0} share of cumulative losses.").format(labels["secondary_partner_name"]),
		},
		{
			"line_no": 5,
			"component": _("Settlements / Payments"),
			"amount": -float(secondary_paid),
			"notes": _("Credits posted as settlement (Due From Partner account) for {0}.").format(labels["secondary_partner_name"]),
		},
		{
			"line_no": 6,
			"component": _("Final Amount Due"),
			"amount": float(final_amount_due),
			"notes": _("Partner Debt Certificate amount."),
			"bold": 1,
			"is_total_row": 1,
		},
	]

	compare_year = filters.get("compare_year")
	if compare_year:
		# Single-year comparison against the chosen year
		c_rows = partner_debt_rows(
			company=filters.company,
			branch=filters.get("branch"),
			years=[int(compare_year)],
			primary_current_account=acc["primary_current"],
			secondary_due_account=acc["secondary_due"],
			secondary_pct=secondary_pct,
		)
		if c_rows:
			comp = d(c_rows[-1]["cumulative_debt"])
			for r in rows:
				r["compare_year"] = int(compare_year)
				r["compare_amount"] = float(comp)
				r["difference"] = flt(r["amount"]) - flt(r["compare_amount"])
				base = flt(r["compare_amount"]) or 0
				r["pct_change"] = (flt(r["difference"]) / base * 100.0) if base else None

	columns = [
		{"label": _("Line"), "fieldname": "line_no", "fieldtype": "Int", "width": 70},
		{"label": _("Component"), "fieldname": "component", "fieldtype": "Data", "width": 260},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 160},
		{"label": _("Notes"), "fieldname": "notes", "fieldtype": "Data", "width": 300},
	]
	if compare_year:
		columns.extend(
			[
				{"label": _("Compare Year"), "fieldname": "compare_year", "fieldtype": "Int", "width": 110},
				{"label": _("Compare Amount"), "fieldname": "compare_amount", "fieldtype": "Currency", "width": 150},
				{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Currency", "width": 130},
				{"label": _("Change %"), "fieldname": "pct_change", "fieldtype": "Percent", "width": 110},
			]
		)

	message = _(
		"Partner Debt Certificate / شهادة مديونية شريك — "
		"Prepared for legal, arbitration, audit, and liquidation purposes."
	)
	chart = {
		"data": {"labels": [r["component"] for r in rows], "datasets": [{"name": _("Amount"), "values": [flt(r["amount"]) for r in rows]}]},
		"type": "bar",
		"title": _("Legal Claim Statement"),
		"height": 260,
	}
	return columns, rows, message, chart

