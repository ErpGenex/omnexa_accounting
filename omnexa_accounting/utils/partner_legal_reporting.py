# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from decimal import Decimal
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate


def d(v: Any) -> Decimal:
	return Decimal(str(v or 0))


def get_account_by_number(company: str, account_number: str, branch: str | None = None) -> str | None:
	filters = {"company": company, "account_number": account_number}
	if branch:
		filters["branch"] = branch
	name = frappe.db.get_value("GL Account", filters, "name")
	if name:
		return name
	return frappe.db.get_value("GL Account", {"company": company, "account_number": account_number}, "name")


def resolve_partner_accounts(company: str, filters: dict, branch: str | None = None) -> dict[str, str]:
	primary_current = filters.get("primary_current_account") or get_account_by_number(company, "3111", branch=branch)
	secondary_current = filters.get("secondary_current_account") or get_account_by_number(company, "3112", branch=branch)
	secondary_due = filters.get("secondary_due_account") or get_account_by_number(company, "1332", branch=branch)
	retained_primary = filters.get("retained_primary_account") or get_account_by_number(company, "3191", branch=branch)
	retained_secondary = filters.get("retained_secondary_account") or get_account_by_number(company, "3192", branch=branch)
	current_year_result = filters.get("current_year_result_account") or get_account_by_number(company, "3103", branch=branch)
	return {
		"primary_current": primary_current or "",
		"secondary_current": secondary_current or "",
		"secondary_due": secondary_due or "",
		"retained_primary": retained_primary or "",
		"retained_secondary": retained_secondary or "",
		"current_year_result": current_year_result or "",
	}


def resolve_partner_labels(filters: dict) -> dict[str, str]:
	return {
		"primary_partner_name": (filters.get("primary_partner_name") or _("Primary Partner")).strip(),
		"secondary_partner_name": (filters.get("secondary_partner_name") or _("Secondary Partner")).strip(),
	}


def resolve_years(filters: dict) -> list[int]:
	if filters.get("fiscal_year"):
		return [int(filters.get("fiscal_year"))]
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	start = int(filters.get("from_year") or from_date.year)
	end = int(filters.get("to_year") or to_date.year)
	start = max(start, from_date.year)
	end = min(end, to_date.year)
	return list(range(start, end + 1))


def yearly_expenses_funded_by_primary(
	*,
	company: str,
	branch: str | None,
	years: list[int],
	primary_current_account: str,
) -> dict[int, Decimal]:
	if not primary_current_account:
		return {y: Decimal("0") for y in years}
	out: dict[int, Decimal] = {}
	for y in years:
		params = {
			"company": company,
			"from_date": f"{y}-01-01",
			"to_date": f"{y}-12-31",
			"primary_current": primary_current_account,
		}
		conds = ["je.company=%(company)s", "je.docstatus=1", "je.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
		if branch and frappe.get_meta("Journal Entry").has_field("branch"):
			conds.append("je.branch=%(branch)s")
			params["branch"] = branch
		row = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(jea.debit),0) AS total_expense
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			INNER JOIN `tabGL Account` ga ON ga.name = jea.account
			WHERE {' AND '.join(conds)}
			  AND ga.account_type='Expense'
			  AND EXISTS (
			    SELECT 1 FROM `tabJournal Entry Account` jea2
			    WHERE jea2.parent = je.name
			      AND jea2.account = %(primary_current)s
			      AND jea2.credit > 0
			  )
			""",
			params,
			as_dict=True,
		)[0]
		out[y] = d(row.get("total_expense"))
	return out


def yearly_secondary_settlements(
	*,
	company: str,
	branch: str | None,
	years: list[int],
	secondary_due_account: str,
) -> dict[int, Decimal]:
	"""Settlements are credits on Due From Secondary Partner account (1332)."""
	if not secondary_due_account:
		return {y: Decimal("0") for y in years}
	out: dict[int, Decimal] = {}
	for y in years:
		params = {"company": company, "from_date": f"{y}-01-01", "to_date": f"{y}-12-31", "acc": secondary_due_account}
		conds = ["je.company=%(company)s", "je.docstatus=1", "je.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
		if branch and frappe.get_meta("Journal Entry").has_field("branch"):
			conds.append("je.branch=%(branch)s")
			params["branch"] = branch
		row = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(jea.credit),0) AS paid
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			WHERE {' AND '.join(conds)} AND jea.account=%(acc)s
			""",
			params,
			as_dict=True,
		)[0]
		out[y] = d(row.get("paid"))
	return out


def yearly_net_results(company: str, branch: str | None, years: list[int]) -> dict[int, Decimal]:
	out: dict[int, Decimal] = {}
	for y in years:
		params = {"company": company, "from_date": f"{y}-01-01", "to_date": f"{y}-12-31"}
		conds = ["je.company=%(company)s", "je.docstatus=1", "je.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
		if branch and frappe.get_meta("Journal Entry").has_field("branch"):
			conds.append("je.branch=%(branch)s")
			params["branch"] = branch
		rows = frappe.db.sql(
			f"""
			SELECT ga.account_type, COALESCE(SUM(jea.debit),0) AS dr, COALESCE(SUM(jea.credit),0) AS cr
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			INNER JOIN `tabGL Account` ga ON ga.name = jea.account
			WHERE {' AND '.join(conds)}
			GROUP BY ga.account_type
			""",
			params,
			as_dict=True,
		)
		revenue = Decimal("0")
		expense = Decimal("0")
		for r in rows:
			at = (r.account_type or "").strip()
			dr = d(r.dr)
			cr = d(r.cr)
			if at in ("Revenue", "Income"):
				revenue += cr - dr
			elif at == "Expense":
				expense += dr - cr
		out[y] = revenue - expense
	return out


def partner_debt_rows(
	*,
	company: str,
	branch: str | None,
	years: list[int],
	primary_current_account: str,
	secondary_due_account: str,
	secondary_pct: Decimal,
) -> list[dict]:
	expenses = yearly_expenses_funded_by_primary(
		company=company,
		branch=branch,
		years=years,
		primary_current_account=primary_current_account,
	)
	paid = yearly_secondary_settlements(
		company=company,
		branch=branch,
		years=years,
		secondary_due_account=secondary_due_account,
	)
	rows: list[dict] = []
	cum = Decimal("0")
	for y in years:
		total = expenses.get(y, Decimal("0"))
		share = total * secondary_pct
		paid_y = paid.get(y, Decimal("0"))
		debt = share - paid_y
		cum += debt
		rows.append(
			{
				"year": y,
				"total_expenses": float(total),
				"secondary_share": float(share),
				"secondary_paid": float(paid_y),
				"debt_year": float(debt),
				"cumulative_debt": float(cum),
			}
		)
	return rows


@frappe.whitelist()
def generate_court_evidence_package(**filters) -> dict:
	"""Return court-ready package payload/links for partner dispute evidence."""
	filters = frappe._dict(filters or {})
	company = filters.get("company")
	if not company:
		frappe.throw(_("Company is required"), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required"), title=_("Filters"))
	years = resolve_years(filters)
	secondary_pct = Decimal(str(filters.get("secondary_pct") or 0.20))
	accounts = resolve_partner_accounts(company, filters, branch=filters.get("branch"))
	labels = resolve_partner_labels(filters)
	debt_rows = partner_debt_rows(
		company=company,
		branch=filters.get("branch"),
		years=years,
		primary_current_account=accounts["primary_current"],
		secondary_due_account=accounts["secondary_due"],
		secondary_pct=secondary_pct,
	)
	net_results = yearly_net_results(company, filters.get("branch"), years)
	loss_cum = Decimal("0")
	loss_rows = []
	for y in years:
		net = net_results.get(y, Decimal("0"))
		secondary_share = net * secondary_pct
		if net < 0:
			loss_cum += -secondary_share
		loss_rows.append(
			{
				"year": y,
				"net_result": float(net),
				"secondary_share": float(secondary_share),
				"cumulative_loss_share": float(loss_cum),
			}
		)
	final_debt = debt_rows[-1]["cumulative_debt"] if debt_rows else 0.0
	return {
		"ok": True,
		"company": company,
		"from_date": str(filters.get("from_date")),
		"to_date": str(filters.get("to_date")),
		"years": years,
		"accounts": accounts,
		"partners": labels,
		"partner_debt_statement": debt_rows,
		"partner_loss_allocation": loss_rows,
		"certificate": {
			"title_ar": "شهادة مديونية شريك",
			"title_en": "Partner Debt Certificate",
			"debtor_partner": labels["secondary_partner_name"],
			"funding_partner": labels["primary_partner_name"],
			"final_amount_due": float(final_debt),
		},
		"report_routes": {
			"partner_debt_statement": "/app/query-report/Partner Debt Statement",
			"partner_loss_allocation_report": "/app/query-report/Partner Loss Allocation Report",
			"partner_recovery_report": "/app/query-report/Partner Recovery Report",
			"legal_claim_statement": "/app/query-report/Legal Claim Statement",
			"liquidation_historical_report": "/app/query-report/Liquidation Historical Report",
		},
	}

