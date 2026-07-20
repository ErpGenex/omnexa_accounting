# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_accounting.utils.partner_legal_reporting import d, resolve_partner_accounts, resolve_partner_labels


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("as_of_date"):
		frappe.throw(_("As Of Date is required."), title=_("Filters"))

	primary_pct = Decimal(str(filters.get("primary_pct") or 80)) / Decimal("100")
	secondary_pct = Decimal(str(filters.get("secondary_pct") or 20)) / Decimal("100")
	liq_cost = d(filters.get("liquidation_cost") or 0)
	labels = resolve_partner_labels(filters)

	assets = d(_sum_account_type(filters.company, filters.get("branch"), filters.as_of_date, "Asset"))
	liabs = d(_sum_account_type(filters.company, filters.get("branch"), filters.as_of_date, "Liability"))
	equity = d(_sum_account_type(filters.company, filters.get("branch"), filters.as_of_date, "Equity"))

	acc = resolve_partner_accounts(filters.company, filters, branch=filters.get("branch"))
	partner_debt = d(_account_balance(filters.company, filters.get("branch"), filters.as_of_date, acc.get("secondary_due")))

	net_liq_value = assets - liabs - liq_cost
	primary_share = net_liq_value * primary_pct
	secondary_share = net_liq_value * secondary_pct
	secondary_after_debt = secondary_share - partner_debt
	primary_after_debt = primary_share + partner_debt

	rows = [
		{"line": _("Assets"), "amount": float(assets)},
		{"line": _("Liabilities"), "amount": -float(liabs)},
		{"line": _("Liquidation Costs"), "amount": -float(liq_cost)},
		{"line": _("Net Liquidation Value"), "amount": float(net_liq_value), "bold": 1},
		{"line": _("{0} Share Before Debt").format(labels["primary_partner_name"]), "amount": float(primary_share)},
		{"line": _("{0} Share Before Debt").format(labels["secondary_partner_name"]), "amount": float(secondary_share)},
		{"line": _("{0} Debt").format(labels["secondary_partner_name"]), "amount": -float(partner_debt)},
		{"line": _("{0} Share After Debt").format(labels["primary_partner_name"]), "amount": float(primary_after_debt), "bold": 1},
		{"line": _("{0} Share After Debt").format(labels["secondary_partner_name"]), "amount": float(secondary_after_debt), "bold": 1},
		{"line": _("Equity Snapshot (book)"), "amount": float(equity)},
	]

	columns = [
		{"label": _("Line Item"), "fieldname": "line", "fieldtype": "Data", "width": 260},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 170},
	]
	chart = {
		"data": {
			"labels": [_("Assets"), _("Liabilities"), _("Net")],
			"datasets": [{"name": _("Liquidation"), "values": [flt(assets), flt(liabs), flt(net_liq_value)]}],
		},
		"type": "bar",
		"title": _("Historical Liquidation Snapshot"),
		"height": 250,
	}
	return columns, rows, None, chart


def _sum_account_type(company: str, branch: str | None, as_of_date: str, account_type: str) -> float:
	params = {"company": company, "as_of": as_of_date, "atype": account_type}
	conds = ["je.company=%(company)s", "je.docstatus=1", "je.posting_date <= %(as_of)s", "ga.account_type=%(atype)s"]
	if branch and frappe.get_meta("Journal Entry").has_field("branch"):
		conds.append("je.branch=%(branch)s")
		params["branch"] = branch
	row = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(jea.debit),0) AS dr, COALESCE(SUM(jea.credit),0) AS cr
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {' AND '.join(conds)}
		""",
		params,
		as_dict=True,
	)[0]
	dr = flt(row.get("dr"))
	cr = flt(row.get("cr"))
	if account_type == "Asset":
		return dr - cr
	return cr - dr


def _account_balance(company: str, branch: str | None, as_of_date: str, account: str | None) -> float:
	if not account:
		return 0.0
	params = {"company": company, "as_of": as_of_date, "acc": account}
	conds = ["je.company=%(company)s", "je.docstatus=1", "je.posting_date <= %(as_of)s", "jea.account=%(acc)s"]
	if branch and frappe.get_meta("Journal Entry").has_field("branch"):
		conds.append("je.branch=%(branch)s")
		params["branch"] = branch
	row = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(jea.debit),0) AS dr, COALESCE(SUM(jea.credit),0) AS cr
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		WHERE {' AND '.join(conds)}
		""",
		params,
		as_dict=True,
	)[0]
	return flt(row.get("dr")) - flt(row.get("cr"))

