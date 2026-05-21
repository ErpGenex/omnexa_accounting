# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Intercompany elimination helpers for multi-company consolidated reports (IFRS 10)."""

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt


def _group_key(consolidation_code: str | None, group_tag: str | None, account: str) -> str:
	return (consolidation_code or "").strip() or (group_tag or "").strip() or account


def intercompany_net_by_group(
	companies: list[str],
	*,
	from_date: str | None = None,
	to_date: str | None = None,
	balance_sheet: bool = False,
) -> dict[str, float]:
	"""Period or cumulative net on intercompany GL accounts, keyed by consolidation group."""
	if not companies:
		return {}

	params = frappe._dict(companies=tuple(companies), from_date=from_date, to_date=to_date)
	date_parts = []
	if balance_sheet:
		if to_date:
			date_parts.append("je.posting_date <= %(to_date)s")
	else:
		if from_date and to_date:
			date_parts.append("je.posting_date BETWEEN %(from_date)s AND %(to_date)s")
		elif to_date:
			date_parts.append("je.posting_date <= %(to_date)s")

	date_sql = f" AND {' AND '.join(date_parts)}" if date_parts else ""

	rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(ga.consolidation_account_code, ''), NULLIF(ga.group_reporting_tag, ''), ga.name) AS grp,
			ga.account_type,
			SUM(jea.debit - jea.credit) AS net
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE je.company IN %(companies)s
			AND je.docstatus = 1
			AND IFNULL(ga.intercompany_account, 0) = 1
			{date_sql}
		GROUP BY grp, ga.account_type
		""",
		params,
		as_dict=True,
	)

	totals: dict[str, float] = defaultdict(float)
	for row in rows:
		net = flt(row.net)
		if (row.account_type or "") in ("Liability", "Equity", "Revenue", "Income"):
			net = -net
		totals[row.grp] += net
	return dict(totals)


def build_consolidated_statement_rows(
	companies: list[str],
	*,
	from_date: str,
	to_date: str,
	statement: str,
	per_company_rows: list[dict],
) -> list[dict]:
	"""Aggregate per-company statement rows and apply intercompany elimination."""
	balance_sheet = statement == "balance_sheet"
	elim_by_group = intercompany_net_by_group(
		companies,
		from_date=from_date,
		to_date=to_date,
		balance_sheet=balance_sheet,
	)

	agg: dict[tuple[str, str, str], dict] = {}
	amount_field = "balance" if balance_sheet else "amount"
	stmt_label = _("Balance Sheet") if balance_sheet else _("Income Statement")

	for row in per_company_rows:
		if row.get("statement") != stmt_label:
			continue
		section = row.get("section") or ""
		account = row.get("account") or ""
		key = (section, account, row.get("account_name") or "")
		entry = agg.setdefault(
			key,
			{
				"company": _("(Consolidated)"),
				"statement": stmt_label,
				"section": section,
				"account": account,
				"account_name": row.get("account_name"),
				"account_name_ar": row.get("account_name_ar"),
				amount_field: 0.0,
			},
		)
		entry[amount_field] = flt(entry[amount_field]) + flt(row.get(amount_field))

	# Subtract intercompany nets matched by account/group code
	for key, entry in list(agg.items()):
		grp = key[1]
		ic_net = flt(elim_by_group.get(grp))
		if ic_net:
			entry[amount_field] = flt(entry[amount_field]) - ic_net

	out = list(agg.values())

	for grp, net in sorted(elim_by_group.items()):
		if abs(net) < 1e-6:
			continue
		out.append(
			{
				"company": _("(Elimination)"),
				"statement": stmt_label,
				"section": _("Intercompany Elimination"),
				"account": grp,
				"account_name": _("Intercompany offset"),
				amount_field: -flt(net),
			}
		)

	return out
