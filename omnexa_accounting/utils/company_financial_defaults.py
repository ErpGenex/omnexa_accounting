# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt
"""Company / branch default GL resolution aligned with professional CoA account_number codes.

See `omnexa_accounting.utils.coa_seed_templates.BASE_COA_TEMPLATE` (IFRS-oriented structure).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

# field on Company -> account_number in seeded CoA (company-level GL, branch usually unset)
COMPANY_GL_CODE_BY_FIELD: dict[str, str] = {
	"default_petty_cash_gl": "1101",
	"default_bank_operating_gl": "1102",
	"default_receivable_gl": "1103",
	"default_inventory_gl": "1104",
	"default_advance_to_supplier_gl": "1105",
	"default_input_vat_gl": "1106",
	"default_other_receivable_gl": "1107",
	"default_trade_payable_gl": "2101",
	"default_output_vat_gl": "2103",
	"default_customer_advances_gl": "2105",
	"default_share_capital_gl": "3101",
	"default_retained_earnings_gl": "3102",
	"default_sales_revenue_gl": "4101",
	"default_service_revenue_gl": "4102",
	"default_cogs_gl": "5101",
	"default_opex_gl": "5102",
	"default_finance_cost_gl": "5109",
}


def _gl_exists() -> bool:
	return bool(frappe.db.exists("DocType", "GL Account"))


def get_company_gl_by_account_number(company: str, account_number: str, branch: str | None = None) -> str | None:
	if not _gl_exists() or not company or not account_number:
		return None
	if branch:
		match = frappe.db.get_value(
			"GL Account",
			{"company": company, "account_number": account_number, "branch": branch},
			"name",
		)
		if match:
			return match
	rows = frappe.get_all(
		"GL Account",
		filters={"company": company, "account_number": account_number, "branch": branch},
		pluck="name",
		limit=1,
	)
	if rows:
		return rows[0]
	rows = frappe.get_all(
		"GL Account",
		filters={"company": company, "account_number": account_number},
		fields=["name", "branch"],
	)
	for r in rows:
		if not r.branch:
			return r.name
	return rows[0].name if rows else None


def apply_company_default_gl_from_coa(company: str, branch: str | None = None, overwrite: int | bool = 0) -> dict:
	"""Set Company GL default links from existing CoA rows (by account_number). Empty fields only unless overwrite=1."""
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Company is required"))
	overwrite = int(overwrite or 0)
	doc = frappe.get_doc("Company", company)
	updated = []
	for fieldname, code in COMPANY_GL_CODE_BY_FIELD.items():
		if not doc.meta.has_field(fieldname):
			continue
		current = doc.get(fieldname)
		if current and not overwrite:
			continue
		gl = get_company_gl_by_account_number(company, code, branch=branch)
		if gl:
			doc.set(fieldname, gl)
			updated.append(fieldname)
	if updated:
		doc.save(ignore_permissions=True)
	return {"ok": True, "company": company, "updated_fields": updated, "branch_filter": branch}


def sync_global_defaults_from_company(company_name: str, currency: str | None = None) -> None:
	"""Keep single `Global Defaults` in sync with the primary company (site-level shortcut)."""
	if not frappe.db.exists("DocType", "Global Defaults"):
		return
	current = frappe.db.get_single_value("Global Defaults", "default_company")
	companies = frappe.get_all("Company", pluck="name")
	if len(companies) == 1 or not current or current == company_name:
		frappe.db.set_single_value("Global Defaults", "default_company", company_name)
		cur = currency or frappe.db.get_value("Company", company_name, "default_currency")
		if cur:
			frappe.db.set_single_value("Global Defaults", "default_currency", cur)


def validate_gl_for_company(gl_name: str | None, company: str) -> None:
	if not gl_name or not company:
		return
	if not _gl_exists():
		return
	row = frappe.db.get_value("GL Account", gl_name, ["company", "branch"], as_dict=True)
	if not row:
		frappe.throw(_("GL Account {0} does not exist.").format(gl_name))
	if row.company != company:
		frappe.throw(_("GL Account {0} must belong to company {1}.").format(gl_name, company))


def validate_gl_for_branch(gl_name: str | None, company: str, branch: str) -> None:
	if not gl_name:
		return
	if not _gl_exists():
		return
	row = frappe.db.get_value("GL Account", gl_name, ["company", "branch"], as_dict=True)
	if not row:
		frappe.throw(_("GL Account {0} does not exist.").format(gl_name))
	if row.company != company:
		frappe.throw(_("GL Account {0} must belong to company {1}.").format(gl_name, company))
	if row.branch and row.branch != branch:
		frappe.throw(_("GL Account {0} must be company-wide or belong to branch {1}.").format(gl_name, branch))


@frappe.whitelist(methods=["POST"])
def fill_company_financial_defaults_from_coa(
	company: str, branch: str | None = None, overwrite: int | str | bool = 0
):
	frappe.only_for("System Manager")
	return apply_company_default_gl_from_coa(company, branch=branch, overwrite=cint(overwrite))


BRANCH_DEFAULT_GL_FIELDS: tuple[str, ...] = (
	"branch_default_petty_cash_gl",
	"branch_default_bank_gl",
	"branch_default_receivable_gl",
	"branch_default_trade_payable_gl",
)

BRANCH_TO_COMPANY_DEFAULT_MAP: dict[str, str] = {
	"branch_default_petty_cash_gl": "default_petty_cash_gl",
	"branch_default_bank_gl": "default_bank_operating_gl",
	"branch_default_receivable_gl": "default_receivable_gl",
	"branch_default_trade_payable_gl": "default_trade_payable_gl",
}


def apply_branch_default_gl_from_company(company: str, branch: str, overwrite: int | bool = 0) -> dict:
	"""Copy company default GLs into branch financial defaults."""
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Company is required"))
	if not branch or not frappe.db.exists("Branch", branch):
		frappe.throw(_("Branch is required"))
	if frappe.db.get_value("Branch", branch, "company") != company:
		frappe.throw(_("Branch {0} must belong to company {1}").format(branch, company))

	overwrite = int(overwrite or 0)
	company_doc = frappe.get_doc("Company", company)
	branch_doc = frappe.get_doc("Branch", branch)
	updated = []
	for branch_field, company_field in BRANCH_TO_COMPANY_DEFAULT_MAP.items():
		if not (branch_doc.meta.has_field(branch_field) and company_doc.meta.has_field(company_field)):
			continue
		if branch_doc.get(branch_field) and not overwrite:
			continue
		source_gl = company_doc.get(company_field)
		if source_gl:
			branch_doc.set(branch_field, source_gl)
			updated.append(branch_field)
	if updated:
		branch_doc.save(ignore_permissions=True)
	return {"ok": True, "company": company, "branch": branch, "updated_fields": updated}


def run_company_financial_validations(doc, method=None):
	for fieldname in COMPANY_GL_CODE_BY_FIELD:
		if doc.meta.has_field(fieldname):
			validate_gl_for_company(doc.get(fieldname), doc.name)


def on_company_update_sync_globals(doc, method=None):
	sync_global_defaults_from_company(doc.name, doc.get("default_currency"))


def run_branch_financial_validations(doc, method=None):
	if doc.get("inherit_company_financial_defaults"):
		return
	for fieldname in BRANCH_DEFAULT_GL_FIELDS:
		if doc.meta.has_field(fieldname):
			validate_gl_for_branch(doc.get(fieldname), doc.company, doc.name)
