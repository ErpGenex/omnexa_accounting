# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _

from omnexa_accounting.utils.partner_legal_reporting import (
	d,
	partner_debt_rows,
	resolve_partner_accounts,
	resolve_partner_labels,
	resolve_years,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	years = resolve_years(filters)
	primary_pct = Decimal(str(filters.get("primary_pct") or 80)) / Decimal("100")
	secondary_pct = Decimal(str(filters.get("secondary_pct") or 20)) / Decimal("100")
	acc = resolve_partner_accounts(filters.company, filters, branch=filters.get("branch"))
	labels = resolve_partner_labels(filters)
	rows = partner_debt_rows(
		company=filters.company,
		branch=filters.get("branch"),
		years=years,
		primary_current_account=acc["primary_current"],
		secondary_due_account=acc["secondary_due"],
		secondary_pct=secondary_pct,
	)
	total_funding = d(sum(r["total_expenses"] for r in rows))
	required_primary = total_funding * primary_pct
	required_secondary = total_funding * secondary_pct
	actual_primary = total_funding
	actual_secondary = d(sum(r["secondary_paid"] for r in rows))
	out = [
		{
			"partner": labels["primary_partner_name"],
			"ownership_pct": float(primary_pct * 100),
			"required_funding": float(required_primary),
			"actual_funding": float(actual_primary),
			"difference": float(actual_primary - required_primary),
		},
		{
			"partner": labels["secondary_partner_name"],
			"ownership_pct": float(secondary_pct * 100),
			"required_funding": float(required_secondary),
			"actual_funding": float(actual_secondary),
			"difference": float(actual_secondary - required_secondary),
		},
	]
	columns = [
		{"label": _("Partner"), "fieldname": "partner", "fieldtype": "Data", "width": 180},
		{"label": _("Ownership %"), "fieldname": "ownership_pct", "fieldtype": "Percent", "width": 120},
		{"label": _("Required Funding"), "fieldname": "required_funding", "fieldtype": "Currency", "width": 160},
		{"label": _("Actual Funding"), "fieldname": "actual_funding", "fieldtype": "Currency", "width": 160},
		{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Currency", "width": 140},
	]
	chart = {
		"data": {
			"labels": [r["partner"] for r in out],
			"datasets": [{"name": _("Difference"), "values": [r["difference"] for r in out]}],
		},
		"type": "bar",
		"title": _("Partner Contribution Gap"),
		"height": 240,
	}
	return columns, out, None, chart

