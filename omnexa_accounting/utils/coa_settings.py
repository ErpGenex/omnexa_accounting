# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe


DEFAULT_MASKS = {
	"Asset": "1xxx",
	"Liability": "2xxx",
	"Equity": "3xxx",
	"Revenue": "4xxx",
	"Expense": "5xxx",
}


def get_coa_settings(company: str | None) -> frappe._dict:
	if not company:
		return frappe._dict()
	row = frappe.db.get_value(
		"CoA Settings",
		{"company": company},
		[
			"name",
			"company",
			"enable_numbering_engine",
			"default_consolidation_view",
			"manual_number_override_roles",
			"asset_mask",
			"liability_mask",
			"equity_mask",
			"revenue_mask",
			"expense_mask",
			"require_group_reporting_tag_for_intercompany",
			"enforce_account_currency_match",
			"allow_direct_posting_default",
		],
		as_dict=True,
	)
	return frappe._dict(row or {})


def get_company_masks(company: str | None) -> dict:
	settings = get_coa_settings(company)
	out = dict(DEFAULT_MASKS)
	if settings:
		out.update(
			{
				"Asset": (settings.asset_mask or out["Asset"]).strip(),
				"Liability": (settings.liability_mask or out["Liability"]).strip(),
				"Equity": (settings.equity_mask or out["Equity"]).strip(),
				"Revenue": (settings.revenue_mask or out["Revenue"]).strip(),
				"Expense": (settings.expense_mask or out["Expense"]).strip(),
			}
		)
	return out


def get_manual_override_roles(company: str | None) -> set[str]:
	settings = get_coa_settings(company)
	lines = (settings.manual_number_override_roles or "").splitlines()
	roles = {line.strip() for line in lines if line.strip()}
	return roles or {"System Manager", "Accounts Manager"}


def should_use_consolidation_view(filters, company: str | None) -> bool:
	filters = frappe._dict(filters or {})
	if "consolidation_view" in filters:
		return int(filters.get("consolidation_view") or 0) == 1
	settings = get_coa_settings(company)
	return int(settings.get("default_consolidation_view") or 0) == 1
