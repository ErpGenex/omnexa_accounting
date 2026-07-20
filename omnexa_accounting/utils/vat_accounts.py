# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Resolve input/output VAT GL accounts per company with explicit source tracing."""

from __future__ import annotations

import frappe
from frappe import _

from omnexa_accounting.utils.company_financial_defaults import (
	COMPANY_GL_CODE_BY_FIELD,
	get_company_gl_by_account_number,
)

INPUT_VAT_FIELD = "default_input_vat_gl"
OUTPUT_VAT_FIELD = "default_output_vat_gl"

INPUT_VAT_NUMBERS = ("1106", "1170", "1171")
OUTPUT_VAT_NUMBERS = ("2103", "2170", "2171")

_NAME_HINTS_INPUT = ("input vat", "vat recoverable", "vat input", "ضريبة مدخلات", "ضريبة قيمة مضافة مدخلات")
_NAME_HINTS_OUTPUT = ("output vat", "vat payable", "vat output", "ضريبة مخرجات", "ضريبة قيمة مضافة مخرجات")


def resolve_vat_accounts(company: str, branch: str | None = None) -> dict:
	"""Return input/output VAT GL with resolution metadata."""
	if not company:
		frappe.throw(_("Company is required."))

	input_acc, input_src = _resolve_side(company, branch, INPUT_VAT_FIELD, INPUT_VAT_NUMBERS, _NAME_HINTS_INPUT)
	output_acc, output_src = _resolve_side(company, branch, OUTPUT_VAT_FIELD, OUTPUT_VAT_NUMBERS, _NAME_HINTS_OUTPUT)

	return {
		"company": company,
		"branch": branch,
		"input_vat_gl": input_acc,
		"output_vat_gl": output_acc,
		"input_source": input_src,
		"output_source": output_src,
	}


def _resolve_side(
	company: str,
	branch: str | None,
	company_field: str,
	account_numbers: tuple[str, ...],
	name_hints: tuple[str, ...],
) -> tuple[str | None, str]:
	if frappe.db.exists("Company", company):
		doc = frappe.get_doc("Company", company)
		if doc.meta.has_field(company_field):
			val = (doc.get(company_field) or "").strip()
			if val and frappe.db.exists("GL Account", val):
				return val, f"company.{company_field}"

	code = COMPANY_GL_CODE_BY_FIELD.get(company_field)
	if code:
		match = get_company_gl_by_account_number(company, code, branch=branch)
		if match:
			return match, f"coa.account_number.{code}"

	for num in account_numbers:
		match = get_company_gl_by_account_number(company, num, branch=branch)
		if match:
			return match, f"fallback.account_number.{num}"

	by_name = _find_by_name_hints(company, branch, name_hints)
	if by_name:
		return by_name, "name_pattern"

	return None, "unresolved"


def _find_by_name_hints(company: str, branch: str | None, hints: tuple[str, ...]) -> str | None:
	filters = {"company": company, "is_group": 0}
	if branch:
		filters["branch"] = branch
	rows = frappe.get_all(
		"GL Account",
		filters=filters,
		fields=["name", "account_name", "account_number"],
		limit=200,
	)
	for row in rows:
		label = f"{row.account_name or ''} {row.account_number or ''}".lower()
		if any(h in label for h in hints):
			return row.name
	return None
