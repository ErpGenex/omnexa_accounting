# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_accounting.utils.partner_legal_reporting import resolve_partner_labels, resolve_years, yearly_net_results


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	years = resolve_years(filters)
	labels = resolve_partner_labels(filters)
	primary_pct = Decimal(str(filters.get("primary_pct") or 80)) / Decimal("100")
	secondary_pct = Decimal(str(filters.get("secondary_pct") or 20)) / Decimal("100")
	net_by_year = yearly_net_results(filters.company, filters.get("branch"), years)

	rows = []
	cum_loss = Decimal("0")
	for y in years:
		net = net_by_year.get(y, Decimal("0"))
		primary_share = net * primary_pct
		secondary_share = net * secondary_pct
		if net < 0:
			cum_loss += -secondary_share
		rows.append(
			{
				"year": y,
				"net_result": float(net),
				"primary_share": float(primary_share),
				"secondary_share": float(secondary_share),
				"cumulative_secondary_loss": float(cum_loss),
			}
		)

	compare_year = filters.get("compare_year")
	columns = [
		{"label": _("Year"), "fieldname": "year", "fieldtype": "Int", "width": 90},
		{"label": _("Net Profit / Loss"), "fieldname": "net_result", "fieldtype": "Currency", "width": 150},
		{"label": _("{0} Share").format(labels["primary_partner_name"]), "fieldname": "primary_share", "fieldtype": "Currency", "width": 160},
		{"label": _("{0} Share").format(labels["secondary_partner_name"]), "fieldname": "secondary_share", "fieldtype": "Currency", "width": 160},
		{
			"label": _("Cumulative {0} Loss").format(labels["secondary_partner_name"]),
			"fieldname": "cumulative_secondary_loss",
			"fieldtype": "Currency",
			"width": 170,
		},
	]
	if compare_year:
		comp = next((r for r in rows if r["year"] == int(compare_year)), None)
		if comp:
			for r in rows:
				r["compare_year"] = int(compare_year)
				r["compare_value"] = flt(comp["net_result"])
				r["diff"] = flt(r["net_result"]) - flt(r["compare_value"])
				base = flt(r["compare_value"]) or 0
				r["pct_change"] = (flt(r["diff"]) / base * 100.0) if base else None
			columns.extend(
				[
					{"label": _("Compare Year"), "fieldname": "compare_year", "fieldtype": "Int", "width": 110},
					{"label": _("Compare Value"), "fieldname": "compare_value", "fieldtype": "Currency", "width": 140},
					{"label": _("Difference"), "fieldname": "diff", "fieldtype": "Currency", "width": 130},
					{"label": _("Change %"), "fieldname": "pct_change", "fieldtype": "Percent", "width": 110},
				]
			)

	chart = {
		"data": {
			"labels": [str(r["year"]) for r in rows],
			"datasets": [
				{"name": _("Net Result"), "values": [r["net_result"] for r in rows]},
				{"name": _("Secondary Share"), "values": [r["secondary_share"] for r in rows]},
			],
		},
		"type": "bar",
		"title": _("Partner Profit/Loss Allocation"),
		"height": 260,
	}
	return columns, rows, None, chart

