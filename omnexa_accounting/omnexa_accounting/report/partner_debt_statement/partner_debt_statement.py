# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

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
	secondary_pct = d(filters.get("secondary_pct") or 0.20)
	accounts = resolve_partner_accounts(filters.company, filters, branch=filters.get("branch"))
	labels = resolve_partner_labels(filters)
	compare_year = filters.get("compare_year")
	rows = partner_debt_rows(
		company=filters.company,
		branch=filters.get("branch"),
		years=years,
		primary_current_account=accounts["primary_current"],
		secondary_due_account=accounts["secondary_due"],
		secondary_pct=secondary_pct,
	)
	for r in rows:
		r["elham_share"] = r.pop("secondary_share")
		r["elham_paid"] = r.pop("secondary_paid")
		r["elham_debt"] = r.pop("debt_year")

	columns = [
		{"label": _("Year"), "fieldname": "year", "fieldtype": "Int", "width": 90
	},
		{"label": _("Total Expenses"), "fieldname": "total_expenses", "fieldtype": "Currency", "width": 140
	},
		{
			"label": _("{0} Share").format(labels["secondary_partner_name"]),
			"fieldname": "elham_share",
			"fieldtype": "Currency",
			"width": 170
	},
		{"label": _("{0} Paid").format(labels["secondary_partner_name"]), "fieldname": "elham_paid", "fieldtype": "Currency", "width": 140
	},
		{"label": _("{0} Debt (year)").format(labels["secondary_partner_name"]), "fieldname": "elham_debt", "fieldtype": "Currency", "width": 170
	},
		{"label": _("Cumulative Debt"), "fieldname": "cumulative_debt", "fieldtype": "Currency", "width": 140
	},
	]

	if compare_year:
		compare = {r["year"]: r for r in _build_rows(filters.company, filters.get("branch"), [int(compare_year)])}
		for r in rows:
			c = compare.get(int(compare_year))
			if not c:
				continue
			r["compare_year"] = int(compare_year)
			r["compare_debt"] = flt(c.get("cumulative_debt") or 0)
			r["diff"] = flt(r["cumulative_debt"]) - flt(r["compare_debt"])
			base = flt(r["compare_debt"]) or 0
			r["pct_change"] = (flt(r["diff"]) / base * 100.0) if base else None
		columns.extend(
			[
				{"label": _("Compare Year"), "fieldname": "compare_year", "fieldtype": "Int", "width": 110
	},
				{"label": _("Compare Cumulative"), "fieldname": "compare_debt", "fieldtype": "Currency", "width": 150
	},
				{"label": _("Difference"), "fieldname": "diff", "fieldtype": "Currency", "width": 130
	},
				{"label": _("Change %"), "fieldname": "pct_change", "fieldtype": "Percent", "width": 110
	},
			]
		)

	chart = {
		"data": {"labels": [str(r["year"]) for r in rows], "datasets": [{"name": _("Cumulative Debt"), "values": [r["cumulative_debt"] for r in rows]}]
	},
		"type": "line",
		"title": _("Partner Debt — Cumulative"),
		"height": 260
	}
	return columns, rows, None, chart

