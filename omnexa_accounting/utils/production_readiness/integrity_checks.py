# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Production readiness integrity checks (extracted from production_readiness.py)."""

from __future__ import annotations

import frappe
from frappe import _

from omnexa_accounting.utils.company_financial_defaults import COMPANY_GL_CODE_BY_FIELD, get_company_gl_by_account_number
from omnexa_accounting.utils.vat_accounts import resolve_vat_accounts


@frappe.whitelist()
def run_production_integrity_checks(company: str | None = None) -> dict:
	frappe.only_for("System Manager")
	companies = [company] if company else frappe.get_all("Company", pluck="name")
	checks = []
	for comp in companies:
		checks.extend(_checks_for_company(comp))
	return {"ok": all(c["ok"] for c in checks), "checks": checks}


def _checks_for_company(company: str) -> list[dict]:
	out = []
	missing_defaults = []
	for field, code in COMPANY_GL_CODE_BY_FIELD.items():
		if not frappe.get_meta("Company").has_field(field):
			continue
		val = frappe.db.get_value("Company", company, field)
		if val:
			continue
		if not get_company_gl_by_account_number(company, code):
			missing_defaults.append(field)
	out.append(
		{
			"company": company,
			"name": "company_gl_defaults",
			"ok": not missing_defaults,
			"details": missing_defaults or "all mapped",
		}
	)

	vat = resolve_vat_accounts(company)
	out.append(
		{
			"company": company,
			"name": "vat_accounts_resolved",
			"ok": bool(vat.get("input_vat_gl") and vat.get("output_vat_gl")),
			"details": vat,
		}
	)

	je_open = frappe.db.count("Journal Entry", {"company": company, "docstatus": 0})
	out.append(
		{
			"company": company,
			"name": "no_draft_journal_entries",
			"ok": je_open == 0,
			"details": f"draft_journal_entries={je_open}",
		}
	)
	return out
