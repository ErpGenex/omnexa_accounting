# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import csv
import io

import frappe
from frappe import _
from frappe.utils import cint

from omnexa_accounting.utils.coa_seed_templates import ACTIVITY_EXTENSIONS, BASE_COA_TEMPLATE

_INDUSTRY_ALIASES = {
	"Service": "Services",
	"Projects": "Construction",
}


CSV_COLUMNS = (
	"account_number",
	"account_name_ar",
	"account_name_en",
	"account_type",
	"main_account_type",
	"sub_account_type",
	"parent_account",
	"is_group",
	"industry_tag",
	"pl_bucket",
	"cash_flow_section",
	"working_capital_bucket",
	"is_stock_valuation",
)

_MAIN_ACCOUNT_TYPES = {
	"",
	"Assets",
	"Current Assets",
	"Non-Current Assets",
	"Liabilities",
	"Current Liabilities",
	"Non-Current Liabilities",
	"Equity",
	"Income",
	"Revenue",
	"Other Income",
	"Expenses",
	"Expense",
	"COGS",
	"Operating Expenses",
	"Other Expenses",
}

_SUB_ACCOUNT_TYPES = {
	"",
	"Header",
	"Current Assets",
	"Non-Current Assets",
	"Current Liabilities",
	"Non-Current Liabilities",
	"Equity",
	"Income",
	"Revenue",
	"Expense",
	"Expenses",
	"Assets",
	"Liabilities",
	"Receivables",
	"Payables",
	"VAT",
	"Tax",
	"Fixed Assets",
	"Cash",
	"Bank",
	"Trade Receivables",
	"Other Receivables",
	"Inventory",
	"Prepayments",
	"Input VAT Recoverable",
	"PPE",
	"Intangible Assets",
	"Investments",
	"ROU Assets",
	"Trade Payables",
	"Accruals",
	"Output VAT Payable",
	"Payroll Liabilities",
	"Taxes & Zakat",
	"Lease Liabilities",
	"Retained Earnings",
	"Share Capital",
	"Sales Revenue",
	"Service Revenue",
	"Discounts & Returns",
	"Interest Income",
	"Other Non-Operating Income",
	"Direct Materials",
	"Direct Labor",
	"Manufacturing Overhead",
	"Selling Expenses",
	"General & Administrative",
	"Depreciation",
	"Amortization",
	"Finance Costs",
	"Impairment & Provisions",
	"Other Non-Operating Expenses",
}


def _clean_main_account_type(value: str | None) -> str:
	v = (value or "").strip()
	return v if v in _MAIN_ACCOUNT_TYPES else ""


def _clean_sub_account_type(value: str | None) -> str:
	v = (value or "").strip()
	return v if v in _SUB_ACCOUNT_TYPES else ""


def _lang_is_ar(lang: str | None = None) -> bool:
	lang = (lang or getattr(frappe.local, "lang", None) or "").lower()
	return lang.startswith("ar")


def _row_account_name(row: dict, lang: str | None = None) -> str:
	if _lang_is_ar(lang):
		return (row.get("account_name_ar") or row.get("account_name_en") or "").strip()
	return (row.get("account_name_en") or row.get("account_name_ar") or "").strip()


def get_seed_rows(industry_tag: str = "All") -> list[dict]:
	industry_tag = (industry_tag or "All").strip()
	resolved_tag = _INDUSTRY_ALIASES.get(industry_tag, industry_tag)
	rows = list(BASE_COA_TEMPLATE)
	ext = ACTIVITY_EXTENSIONS.get(resolved_tag)
	if ext:
		rows.extend(list(ext))

	out = []
	for r in rows:
		out.append(
			{
				"account_number": str(r.get("code") or "").strip(),
				"account_name_ar": str(r.get("name_ar") or "").strip(),
				"account_name_en": str(r.get("name_en") or "").strip(),
				"account_type": str(r.get("type") or "").strip(),
				"main_account_type": str(r.get("main") or "").strip(),
				"sub_account_type": str(r.get("sub") or "").strip(),
				"parent_account": str(r.get("parent") or "").strip(),
				"is_group": 1 if int(r.get("group") or 0) else 0,
				"industry_tag": industry_tag if industry_tag else "All",
				"pl_bucket": str(r.get("pl_bucket") or "").strip(),
				"cash_flow_section": str(r.get("cash_flow_section") or "").strip(),
				"working_capital_bucket": str(r.get("working_capital_bucket") or "").strip(),
				"is_stock_valuation": 1 if int(r.get("is_stock_valuation") or 0) else 0,
			}
		)
	return out


@frappe.whitelist(methods=["POST"])
def seed_coa_template(template_name: str, industry_tag: str = "All") -> dict:
	"""Create/replace a COA Template using the curated seed dataset."""
	frappe.only_for("System Manager")
	if not template_name or not str(template_name).strip():
		frappe.throw(_("Template Name is required"), title=_("COA Template"))

	template_name = str(template_name).strip()
	industry_tag = (industry_tag or "All").strip() or "All"

	rows = get_seed_rows(industry_tag=industry_tag)
	if frappe.db.exists("COA Template", {"template_name": template_name}):
		name = frappe.db.get_value("COA Template", {"template_name": template_name}, "name")
		doc = frappe.get_doc("COA Template", name)
		doc.accounts = []
	else:
		doc = frappe.new_doc("COA Template")

	doc.template_name = template_name
	doc.industry_tag = industry_tag
	doc.is_active = 1
	for r in rows:
		doc.append(
			"accounts",
			{
				"account_number": r["account_number"],
				"account_name_ar": r["account_name_ar"],
				"account_name_en": r["account_name_en"],
				"account_type": r["account_type"],
				"main_account_type": r["main_account_type"],
				"sub_account_type": r["sub_account_type"],
				"parent_account_number": r["parent_account"],
				"is_group": r["is_group"],
				"industry_tag": r["industry_tag"],
				"pl_bucket": r["pl_bucket"],
				"cash_flow_section": r["cash_flow_section"],
				"working_capital_bucket": r["working_capital_bucket"],
				"is_stock_valuation": r["is_stock_valuation"],
			},
		)
	doc.save(ignore_permissions=True)
	return {"ok": True, "template": doc.name, "template_name": doc.template_name, "industry_tag": doc.industry_tag, "lines": len(doc.accounts)}


@frappe.whitelist()
def export_coa_template_csv(template: str) -> str:
	"""Return CSV text for a COA Template."""
	if not template:
		frappe.throw(_("Template is required"), title=_("COA Template"))
	doc = frappe.get_doc("COA Template", template)
	buf = io.StringIO()
	writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
	writer.writeheader()
	for row in doc.accounts or []:
		writer.writerow(
			{
				"account_number": (row.account_number or "").strip(),
				"account_name_ar": (row.account_name_ar or "").strip(),
				"account_name_en": (row.account_name_en or "").strip(),
				"account_type": (row.account_type or "").strip(),
				"main_account_type": (row.main_account_type or "").strip(),
				"sub_account_type": (row.sub_account_type or "").strip(),
				"parent_account": (row.parent_account_number or "").strip(),
				"is_group": int(row.is_group or 0),
				"industry_tag": (row.industry_tag or doc.industry_tag or "All").strip(),
				"pl_bucket": (row.pl_bucket or "").strip(),
				"cash_flow_section": (row.cash_flow_section or "").strip(),
				"working_capital_bucket": (row.working_capital_bucket or "").strip(),
				"is_stock_valuation": int(row.is_stock_valuation or 0),
			}
		)
	return buf.getvalue()


def _parse_csv_text(csv_text: str) -> list[dict]:
	if not csv_text or not str(csv_text).strip():
		return []
	reader = csv.DictReader(io.StringIO(csv_text))
	rows = []
	for r in reader:
		rows.append({(k or "").strip(): (v or "").strip() for k, v in (r or {}).items()})
	return rows


@frappe.whitelist(methods=["POST"])
def import_coa_template_csv(
	template: str,
	csv_text: str,
	replace: int | str | bool = 1,
	dry_run: int | str | bool = 0,
) -> dict:
	"""Import CSV lines into COA Template (replace=1 replaces all rows, dry_run validates only)."""
	frappe.only_for("System Manager")
	if not template:
		frappe.throw(_("Template is required"), title=_("COA Template"))
	doc = frappe.get_doc("COA Template", template)
	rows = _parse_csv_text(csv_text)
	if not rows:
		frappe.throw(_("CSV is empty or invalid."), title=_("COA Template"))

	seen = set()
	lines = []
	for r in rows:
		code = (r.get("account_number") or "").strip()
		if not code:
			frappe.throw(_("CSV row missing account_number."), title=_("COA Template"))
		if code in seen:
			frappe.throw(_("CSV contains duplicate account_number: {0}").format(code), title=_("COA Template"))
		seen.add(code)
		lines.append(r)

	if int(replace or 0):
		doc.accounts = []

	for r in lines:
		row_code = (r.get("account_number") or "").strip()
		if (r.get("account_type") or "").strip() not in {"Asset", "Liability", "Equity", "Income", "Expense"}:
			frappe.throw(
				_("CSV contains invalid account_type for account_number {0}.").format(row_code),
				title=_("COA Template"),
			)
		if (r.get("is_group") or "").strip() not in {"", "0", "1", "true", "false", "yes", "no"}:
			frappe.throw(
				_("CSV contains invalid is_group for account_number {0}.").format(row_code),
				title=_("COA Template"),
			)
		if (r.get("is_stock_valuation") or "").strip() not in {"", "0", "1", "true", "false", "yes", "no"}:
			frappe.throw(
				_("CSV contains invalid is_stock_valuation for account_number {0}.").format(row_code),
				title=_("COA Template"),
			)

	if int(dry_run or 0):
		return {
			"ok": True,
			"template": doc.name,
			"lines": len(lines),
			"replaced": bool(int(replace or 0)),
			"dry_run": True,
		}

	for r in lines:
		doc.append(
			"accounts",
			{
				"account_number": r.get("account_number"),
				"account_name_ar": r.get("account_name_ar"),
				"account_name_en": r.get("account_name_en"),
				"account_type": r.get("account_type"),
				"main_account_type": r.get("main_account_type"),
				"sub_account_type": r.get("sub_account_type"),
				"parent_account_number": r.get("parent_account"),
				"is_group": 1 if str(r.get("is_group") or "").strip() in {"1", "true", "yes"} else 0,
				"industry_tag": r.get("industry_tag") or doc.industry_tag or "All",
				"pl_bucket": r.get("pl_bucket"),
				"cash_flow_section": r.get("cash_flow_section"),
				"working_capital_bucket": r.get("working_capital_bucket"),
				"is_stock_valuation": 1 if str(r.get("is_stock_valuation") or "").strip() in {"1", "true", "yes"} else 0,
			},
		)
	doc.save(ignore_permissions=True)
	return {
		"ok": True,
		"template": doc.name,
		"lines": len(doc.accounts),
		"replaced": bool(int(replace or 0)),
		"dry_run": False,
	}


@frappe.whitelist(methods=["POST"])
def apply_coa_template_to_company(
	template: str,
	company: str,
	branch: str | None = None,
	lang: str | None = None,
	overwrite_names: int | str | bool = 0,
) -> dict:
	"""
	Create/update GL Accounts by account_number for a company (optionally branch-scoped).

	Idempotent rules:
	- key = (company, branch, account_number) if branch provided else (company, account_number + empty-branch preference)
	- creates missing accounts
	- updates metadata fields; updates names only if overwrite_names=1
	"""
	frappe.only_for("System Manager")
	if not template or not company:
		frappe.throw(_("Template and Company are required."), title=_("COA Template"))
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company does not exist."), title=_("COA Template"))

	doc = frappe.get_doc("COA Template", template)
	lines = []
	for row in doc.accounts or []:
		lines.append(
			{
				"account_number": (row.account_number or "").strip(),
				"account_name_ar": (row.account_name_ar or "").strip(),
				"account_name_en": (row.account_name_en or "").strip(),
				"account_type": (row.account_type or "").strip(),
				"main_account_type": (row.main_account_type or "").strip(),
				"sub_account_type": (row.sub_account_type or "").strip(),
				"parent_account_number": (row.parent_account_number or "").strip(),
				"is_group": int(row.is_group or 0),
				"industry_tag": (row.industry_tag or doc.industry_tag or "All").strip(),
				"pl_bucket": (row.pl_bucket or "").strip(),
				"cash_flow_section": (row.cash_flow_section or "").strip(),
				"working_capital_bucket": (row.working_capital_bucket or "").strip(),
				"is_stock_valuation": int(row.is_stock_valuation or 0),
			}
		)

	# Parent-first ordering (simple + stable): shortest account_number first, then lexicographic.
	lines.sort(key=lambda r: (len(r["account_number"]), r["account_number"]))

	# Map account_number -> GL Account.name
	mapping: dict[str, str] = {}
	created = 0
	updated = 0

	def _ensure_parent_is_group(gl_name: str | None) -> str | None:
		if not gl_name:
			return None
		if cint(frappe.db.get_value("GL Account", gl_name, "is_group")):
			return gl_name
		# Recover from legacy/partial trees: parent must be a group/header.
		doc = frappe.get_doc("GL Account", gl_name)
		doc.is_group = 1
		if doc.meta.has_field("posting_type"):
			doc.posting_type = "Header"
		doc.save(ignore_permissions=True)
		return doc.name

	def find_existing_gl(code: str, require_group: bool = False) -> str | None:
		if not code:
			return None
		if branch:
			filters = {"company": company, "branch": branch, "account_number": code}
			if require_group:
				filters["is_group"] = 1
			match = frappe.db.get_value("GL Account", filters, "name")
			if match:
				return match
		# Prefer company-wide (empty branch) first.
		filters = {"company": company, "branch": ["in", ("", None)], "account_number": code}
		if require_group:
			filters["is_group"] = 1
		match = frappe.db.get_value("GL Account", filters, "name")
		if match:
			return match
		# Fallback: any match in company.
		filters = {"company": company, "account_number": code}
		if require_group:
			filters["is_group"] = 1
		match = frappe.db.get_value("GL Account", filters, "name")
		if match:
			return match
		if require_group:
			# Last resort: promote any matching account to group.
			return _ensure_parent_is_group(frappe.db.get_value("GL Account", {"company": company, "account_number": code}, "name"))
		return frappe.db.get_value("GL Account", filters, "name")

	overwrite_names = int(overwrite_names or 0)

	for r in lines:
		code = r["account_number"]
		if not code:
			continue

		parent_gl = None
		parent_code = r.get("parent_account_number")
		if parent_code:
			parent_gl = _ensure_parent_is_group(mapping.get(parent_code)) or find_existing_gl(parent_code, require_group=True)

		existing = find_existing_gl(code)
		if existing:
			gl = frappe.get_doc("GL Account", existing)
			if overwrite_names:
				name_value = _row_account_name(r, lang=lang)
				if name_value:
					gl.account_name = name_value
			gl.account_type = r.get("account_type") or gl.account_type
			incoming_main = _clean_main_account_type(r.get("main_account_type"))
			incoming_sub = _clean_sub_account_type(r.get("sub_account_type"))
			gl.main_account_type = incoming_main or gl.main_account_type
			gl.sub_account_type = incoming_sub or gl.sub_account_type
			gl.is_group = int(r.get("is_group") or 0)
			gl.pl_bucket = r.get("pl_bucket") or gl.pl_bucket
			gl.cash_flow_section = r.get("cash_flow_section") or gl.cash_flow_section
			gl.working_capital_bucket = r.get("working_capital_bucket") or gl.working_capital_bucket
			gl.is_stock_valuation = int(r.get("is_stock_valuation") or 0)
			if gl.company != company:
				# Safety: never cross-company mutate
				frappe.throw(_("GL Account {0} belongs to a different company.").format(existing), title=_("COA Template"))
			if branch and not gl.branch:
				# Keep company-wide accounts company-wide unless explicitly created per-branch from scratch.
				pass
			if parent_gl:
				gl.parent_account = parent_gl
			gl.save(ignore_permissions=True)
			mapping[code] = gl.name
			updated += 1
			continue

		gl = frappe.new_doc("GL Account")
		gl.company = company
		if branch:
			gl.branch = branch
		gl.account_number = code
		gl.account_name = _row_account_name(r, lang=lang) or code
		gl.account_type = r.get("account_type")
		gl.main_account_type = _clean_main_account_type(r.get("main_account_type"))
		gl.sub_account_type = _clean_sub_account_type(r.get("sub_account_type"))
		gl.is_group = int(r.get("is_group") or 0)
		gl.pl_bucket = r.get("pl_bucket")
		gl.cash_flow_section = r.get("cash_flow_section")
		gl.working_capital_bucket = r.get("working_capital_bucket")
		gl.is_stock_valuation = int(r.get("is_stock_valuation") or 0)
		if parent_gl:
			gl.parent_account = parent_gl
		gl.insert(ignore_permissions=True)
		mapping[code] = gl.name
		created += 1

	return {
		"ok": True,
		"template": doc.name,
		"company": company,
		"branch": branch,
		"created": created,
		"updated": updated,
		"total": len(lines),
	}

