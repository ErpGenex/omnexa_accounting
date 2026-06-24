# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Seed Microlab company — minimal partner litigation accounting (2015–2026).

Accounting model (per legal instructions):
- Chart: capital (سيد 8000 / إلهام 2000), جاري سيد, مستحق من إلهام, four OPEX accounts only.
- Every expense: Dr Expense / Cr جاري سيد (paid by سيد هاشم حسن).
- Year-end: Dr مستحق من إلهام / Cr جاري سيد for 20% of annual expenses (إلهام مصطفى محمد أحمد).
- No assets, inventory, products, or software accounts.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, getdate, today

COMPANY_ABBR = "MLAB"
COMPANY_NAME = "Microlab Information Systems"
COMPANY_NAME_AR = "ميكرولاب لتطوير نظم المعلومات"
START_DATE = date(2015, 3, 1)
END_DATE = date(2026, 12, 31)
PARTNER_FUNDED = "سيد هاشم حسن"
PARTNER_SILENT = "إلهام مصطفى محمد أحمد"
OWNERSHIP_SAYED = Decimal("0.80")
OWNERSHIP_ELHAM = Decimal("0.20")
CAPITAL_SAYED = Decimal("8000")
CAPITAL_ELHAM = Decimal("2000")
FORMATION_AMOUNT = Decimal("14000")
MODIFICATION_AMOUNT = Decimal("15000")
SEED_TAG = "MICROLAB-SEED"

# Allowed Microlab leaf accounts only
ACCOUNT_SPECS: list[dict] = [
	{"code": "1", "name_en": "Assets", "name_ar": "الأصول", "type": "Asset", "group": 1, "parent": ""},
	{"code": "13", "name_en": "Other Receivables", "name_ar": "مدينون آخرون", "type": "Asset", "group": 1, "parent": "1"},
	{
		"code": "1332",
		"name_en": f"Due From Partner — {PARTNER_SILENT}",
		"name_ar": "مستحق من إلهام",
		"type": "Asset",
		"group": 0,
		"parent": "13",
		"main": "Assets",
		"sub": "Other Receivables",
	},
	{"code": "3", "name_en": "Equity", "name_ar": "حقوق الملكية", "type": "Equity", "group": 1, "parent": ""},
	{
		"code": "31011",
		"name_en": f"Partner Capital — {PARTNER_FUNDED}",
		"name_ar": "رأس مال سيد",
		"type": "Equity",
		"group": 0,
		"parent": "3",
		"main": "Equity",
		"sub": "Capital",
	},
	{
		"code": "31012",
		"name_en": f"Partner Capital — {PARTNER_SILENT}",
		"name_ar": "رأس مال إلهام",
		"type": "Equity",
		"group": 0,
		"parent": "3",
		"main": "Equity",
		"sub": "Capital",
	},
	{
		"code": "3111",
		"name_en": f"Partner Current — {PARTNER_FUNDED}",
		"name_ar": "جاري سيد",
		"type": "Equity",
		"group": 0,
		"parent": "3",
		"main": "Equity",
		"sub": "Partner Current",
	},
	{"code": "5", "name_en": "Expenses", "name_ar": "المصروفات", "type": "Expense", "group": 1, "parent": ""},
	{"code": "51", "name_en": "Operating Expenses", "name_ar": "مصروفات تشغيلية", "type": "Expense", "group": 1, "parent": "5"},
	{
		"code": "5101",
		"name_en": "Rent Expense",
		"name_ar": "مصروف إيجار",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5102",
		"name_en": "Electricity Expense",
		"name_ar": "مصروف كهرباء",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5103",
		"name_en": "Internet Expense",
		"name_ar": "مصروف إنترنت",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5104",
		"name_en": "Legal Fees Expense",
		"name_ar": "مصروف أتعاب محاماة",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
]

ALLOWED_ACCOUNT_CODES = frozenset(spec["code"] for spec in ACCOUNT_SPECS)
EXPENSE_CODES = frozenset({"5101", "5102", "5103", "5104"})

# Legacy codes to disable when re-seeding (assets / inventory / software / extra OPEX)
LEGACY_CODES_TO_DISABLE = frozenset(
	{
		"1104",
		"5105",
		"5106",
		"5107",
		"5109",
		"5111",
		"3112",
		"3191",
		"3192",
		"1331",
		"3103",
		"3101",
		"3102",
	}
)


def _d(value) -> Decimal:
	return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _submit(doc):
	if doc.docstatus == 0:
		doc.submit()


def _account(company: str, branch: str | None, code: str) -> str:
	filters = {"company": company, "account_number": code}
	if branch:
		filters["branch"] = branch
	name = frappe.db.get_value("GL Account", filters, "name")
	if not name:
		frappe.throw(_("GL Account {0} not found for company {1}").format(code, company))
	return name


def _account_label_ar(company: str, branch: str | None, code: str) -> str:
	acc = _account(company, branch, code)
	if frappe.db.has_column("GL Account", "account_name_ar"):
		ar = frappe.db.get_value("GL Account", acc, "account_name_ar")
		if ar:
			return ar
	for spec in ACCOUNT_SPECS:
		if spec["code"] == code:
			return spec.get("name_ar") or spec.get("name_en") or code
	return frappe.db.get_value("GL Account", acc, "account_name") or code


def _ensure_company() -> tuple[str, str]:
	if frappe.db.exists("Company", COMPANY_ABBR):
		company = COMPANY_ABBR
		updates = {}
		if frappe.db.get_value("Company", company, "company_name") != COMPANY_NAME:
			updates["company_name"] = COMPANY_NAME
		if frappe.db.has_column("Company", "company_name_ar"):
			updates["company_name_ar"] = COMPANY_NAME_AR
		if frappe.db.has_column("Company", "business_activity"):
			current = frappe.db.get_value("Company", COMPANY_ABBR, "business_activity")
			if current in (None, "", "Software"):
				updates["business_activity"] = "Services"
		if frappe.db.has_column("Company", "industry_sector"):
			sector = frappe.db.get_value("Company", COMPANY_ABBR, "industry_sector")
			if sector in (None, "", "Software"):
				updates["industry_sector"] = "Services"
		if updates:
			frappe.db.set_value("Company", company, updates, update_modified=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY_NAME,
				"abbr": COMPANY_ABBR,
				"default_currency": "EGP",
				"country": "Egypt",
				"industry_sector": "Services",
				"business_activity": "Services",
				"status": "Active",
				"enable_branches": 1,
			}
		)
		if doc.meta.has_field("company_name_ar"):
			doc.company_name_ar = COMPANY_NAME_AR
		doc.insert(ignore_permissions=True)
		company = doc.name

	branch = frappe.db.get_value("Branch", {"company": company}, "name", order_by="creation asc")
	if not branch:
		branch = frappe.db.get_value("Branch", {"company": company, "branch_name": ["like", "%Head%"]}, "name")
	if not branch:
		branch_doc = frappe.get_doc(
			{
				"doctype": "Branch",
				"branch_name": f"{COMPANY_ABBR} Head Office",
				"company": company,
			}
		)
		branch_doc.insert(ignore_permissions=True)
		branch = branch_doc.name
	return company, branch


def _ensure_minimal_coa(company: str, branch: str) -> dict[str, str]:
	from omnexa_accounting.utils.production_readiness import _ensure_account

	parent_map: dict[str, str] = {}
	for row in frappe.get_all(
		"GL Account",
		filters={"company": company, "branch": branch},
		fields=["name", "account_number"],
	):
		if row.account_number:
			parent_map[row.account_number] = row.name

	accounts: dict[str, str] = {}
	for spec in ACCOUNT_SPECS:
		code = spec["code"]
		accounts[code] = _ensure_account(spec, company, branch, parent_map)
		parent_map[code] = accounts[code]
	return accounts


def _disable_legacy_microlab_accounts(company: str, branch: str) -> int:
	"""Freeze asset/inventory/software/extra expense accounts not in the minimal chart."""
	if not frappe.db.has_column("GL Account", "is_frozen"):
		return 0
	frozen = 0
	rows = frappe.get_all(
		"GL Account",
		filters={"company": company, "branch": branch, "is_group": 0},
		fields=["name", "account_number", "is_frozen"],
	)
	for row in rows:
		code = (row.account_number or "").strip()
		if not code or code in ALLOWED_ACCOUNT_CODES:
			continue
		if code in LEGACY_CODES_TO_DISABLE or code.startswith(("11", "12", "14", "15", "16", "17", "18", "19")):
			if not row.is_frozen:
				frappe.db.set_value("GL Account", row.name, "is_frozen", 1, update_modified=False)
				frozen += 1
	return frozen


def _delete_microlab_product(company: str) -> None:
	if not frappe.db.exists("DocType", "Item"):
		return
	for code in ("ERP-POS-MICROLAB",):
		name = frappe.db.get_value("Item", {"company": company, "item_code": code}, "name")
		if name:
			frappe.delete_doc("Item", name, force=1, ignore_permissions=True)


def _je_exists(company: str, reference: str) -> bool:
	return bool(frappe.db.exists("Journal Entry", {"company": company, "reference": reference}))


class _JeLine:
	__slots__ = ("account", "debit", "credit", "remark_ar")

	def __init__(self, account: str, debit: Decimal, credit: Decimal, remark_ar: str):
		self.account = account
		self.debit = debit
		self.credit = credit
		self.remark_ar = remark_ar


def _create_je(
	company: str,
	branch: str,
	posting_date: date,
	reference: str,
	remarks: str,
	lines: list[_JeLine],
) -> str | None:
	if _je_exists(company, reference):
		return frappe.db.get_value("Journal Entry", {"company": company, "reference": reference}, "name")

	accounts = []
	for line in lines:
		if line.debit <= 0 and line.credit <= 0:
			continue
		row = {
			"account": line.account,
			"debit": float(line.debit),
			"credit": float(line.credit),
		}
		if line.remark_ar:
			row["external_reference"] = line.remark_ar[:140]
		accounts.append(row)

	if len(accounts) < 2:
		return None

	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": company,
			"branch": branch,
			"posting_date": posting_date,
			"reference": reference,
			"remarks": remarks,
			"accounts": accounts,
		}
	)
	je.flags.ignore_branch_access = True
	je.insert(ignore_permissions=True)
	_submit(je)
	return je.name


def _recognize_elham_expense_share(
	company: str,
	branch: str,
	year: int,
	*,
	due_from_elham: str,
	partner_current_sayed: str,
	annual_expenses: Decimal,
) -> bool:
	"""Year-end: Dr مستحق من إلهام / Cr جاري سيد for 20% of annual expenses."""
	ref = f"{SEED_TAG}-DEBT-{year}"
	if _je_exists(company, ref):
		return False
	share = _d(annual_expenses * OWNERSHIP_ELHAM)
	if share <= 0:
		return False
	remarks = (
		f"إثبات حصة الشريك {PARTNER_SILENT} (20%) من مصروفات العام {year} "
		f"— مدفوعة بالكامل من {PARTNER_FUNDED} — مستحق لصالح جاري سيد"
	)
	lines = [
		_JeLine(due_from_elham, share, Decimal("0"), f"مدين — مستحق من إلهام — {year}"),
		_JeLine(partner_current_sayed, Decimal("0"), share, f"دائن — جاري سيد — تحميل حصة الشريك"),
	]
	return bool(_create_je(company, branch, date(year, 12, 31), ref, remarks, lines))


def _expense_je(
	*,
	company: str,
	branch: str,
	posting_date: date,
	reference: str,
	expense_acc: str,
	expense_code: str,
	partner_sayed: str,
	amount: Decimal,
	title_ar: str,
	year_expense_totals: dict[int, Decimal],
) -> bool:
	if amount <= 0:
		return False
	exp_label = _account_label_ar(company, branch, expense_code)
	remarks = f"{title_ar} | {exp_label} | دفع: {PARTNER_FUNDED} | {reference}"
	lines = [
		_JeLine(expense_acc, amount, Decimal("0"), f"مدين — {exp_label}"),
		_JeLine(partner_sayed, Decimal("0"), amount, f"دائن — جاري سيد — {PARTNER_FUNDED}"),
	]
	created = _create_je(company, branch, posting_date, reference, remarks, lines)
	if created:
		year_expense_totals[posting_date.year] += amount
	return bool(created)


def _monthly_rent(year: int, month: int) -> Decimal:
	if year < 2015 or (year == 2015 and month < 3):
		return Decimal("0")
	if year >= 2023:
		return Decimal("3000")
	if year >= 2021:
		return Decimal("2000")
	years_since_2015 = year - 2015
	base = Decimal("1000")
	return _d(base * (Decimal("1.1") ** years_since_2015))


def _gradual_monthly(start: Decimal, end: Decimal, year: int, start_year: int = 2015, end_year: int = 2026) -> Decimal:
	if year <= start_year:
		return start
	if year >= end_year:
		return end
	span = end_year - start_year
	step = (end - start) / span
	return _d(start + step * (year - start_year))


def _electricity_amount(year: int, month: int) -> Decimal:
	base = 100 + ((year * 12 + month) % 101)
	return _d(min(200, max(100, base)))


def _annual_legal_fee(year: int) -> Decimal:
	return _d(2500 + (year - 2015) * 150)


def _iter_months(start: date, end: date):
	cursor = get_first_day(start)
	last = get_first_day(end)
	while cursor <= last:
		yield cursor.year, cursor.month
		cursor = add_months(cursor, 1)


def _cumulative_by_year(year_totals: dict[int, Decimal]) -> dict[int, Decimal]:
	out: dict[int, Decimal] = {}
	running = Decimal("0")
	for y in sorted(year_totals.keys()):
		running += _d(year_totals[y])
		out[y] = _d(running)
	return out


def _report_url(report_name: str, **params) -> str:
	from urllib.parse import urlencode

	base = f"/app/query-report/{report_name}"
	if not params:
		return base
	return f"{base}?{urlencode(params)}"


def get_microlab_report_links(company: str | None = None, branch: str | None = None) -> dict:
	"""Standard + partner litigation report routes for Microlab."""
	company = company or COMPANY_ABBR
	if not branch:
		branch = frappe.db.get_value("Branch", {"company": company}, "name")
	sayed_acc = frappe.db.get_value(
		"GL Account", {"company": company, "account_number": "3111", "branch": branch}, "name"
	)
	elham_due = frappe.db.get_value(
		"GL Account", {"company": company, "account_number": "1332", "branch": branch}, "name"
	)
	common = {
		"company": company,
		"from_date": str(START_DATE),
		"to_date": str(END_DATE),
	}
	partner_filters = {
		**common,
		"branch": branch or "",
		"primary_partner_name": PARTNER_FUNDED,
		"secondary_partner_name": PARTNER_SILENT,
		"secondary_pct": "20",
	}
	return {
		"general_journal": {
			"title_ar": "اليومية العامة",
			"url": _report_url("General Journal", **common),
		},
		"general_ledger": {
			"title_ar": "الأستاذ العام",
			"url": _report_url("General Ledger", **common),
		},
		"trial_balance": {
			"title_ar": "ميزان المراجعة",
			"url": _report_url("Trial Balance", **common),
		},
		"income_statement": {
			"title_ar": "قائمة الدخل",
			"url": _report_url("Profit and Loss Statement", **common),
		},
		"balance_sheet": {
			"title_ar": "الميزانية العمومية",
			"url": _report_url("Balance Sheet", **{**common, "as_on_date": str(END_DATE)}),
		},
		"sayed_current_statement": {
			"title_ar": "كشف جاري سيد",
			"url": _report_url(
				"General Ledger",
				**common,
				account=sayed_acc or "",
			),
		},
		"elham_debt_statement": {
			"title_ar": "كشف مديونية إلهام",
			"url": _report_url("Partner Debt Statement", **partner_filters),
		},
		"legal_claim_statement": {
			"title_ar": "تقرير قانوني — إثبات مديونية الشريك",
			"url": _report_url("Legal Claim Statement", **partner_filters),
		},
		"partner_recovery_report": {
			"title_ar": "تقرير استرداد مساهمات الشريك",
			"url": _report_url("Partner Recovery Report", **partner_filters),
		},
		"account_elham_due": elham_due,
		"account_sayed_current": sayed_acc,
	}


@frappe.whitelist()
def get_microlab_legal_report(company: str | None = None) -> dict:
	"""Litigation-ready package: expenses by year, Elham 20%, cumulative debt 2015–2026."""
	company = company or COMPANY_ABBR
	if not frappe.db.exists("Company", company):
		return {"error": "Company not found"}

	branch = frappe.db.get_value("Branch", {"company": company}, "name")
	from omnexa_accounting.utils.partner_legal_reporting import (
		generate_court_evidence_package,
		partner_debt_rows,
		resolve_partner_accounts,
	)

	years = list(range(START_DATE.year, END_DATE.year + 1))
	accounts = resolve_partner_accounts(company, {}, branch=branch)
	debt_rows = partner_debt_rows(
		company=company,
		branch=branch,
		years=years,
		primary_current_account=accounts["primary_current"],
		secondary_due_account=accounts["secondary_due"],
		secondary_pct=OWNERSHIP_ELHAM,
	)
	cumulative = debt_rows[-1]["cumulative_debt"] if debt_rows else 0.0
	total_expenses = sum(r["total_expenses"] for r in debt_rows)
	total_elham_share = sum(r["secondary_share"] for r in debt_rows)

	package = generate_court_evidence_package(
		company=company,
		branch=branch,
		from_date=str(START_DATE),
		to_date=str(END_DATE),
		from_year=START_DATE.year,
		to_year=END_DATE.year,
		primary_partner_name=PARTNER_FUNDED,
		secondary_partner_name=PARTNER_SILENT,
		secondary_pct="0.20",
	)

	return {
		"company": company,
		"company_name": COMPANY_NAME,
		"company_name_ar": COMPANY_NAME_AR,
		"partner_funded": PARTNER_FUNDED,
		"partner_silent": PARTNER_SILENT,
		"ownership_silent_pct": 20,
		"period": {"from": str(START_DATE), "to": str(END_DATE)},
		"total_expenses_paid_by_sayed": total_expenses,
		"total_elham_share_20pct": total_elham_share,
		"cumulative_debt_elham": cumulative,
		"yearly_breakdown": debt_rows,
		"legal_narrative_ar": (
			f"أثبتت الشركة {COMPANY_NAME_AR} أن الشريك {PARTNER_FUNDED} تحمّل مصروفات التشغيل "
			f"بالكامل من {START_DATE.year} حتى {END_DATE.year} بإجمالي {total_expenses:,.2f} جنيه مصري. "
			f"حصة الشريك {PARTNER_SILENT} البالغة 20% من المصروفات تبلغ {total_elham_share:,.2f} جنيه مصري. "
			f"الرصيد المستحق على الشريك إلهام (تراكمي) حتى {END_DATE.year}: {cumulative:,.2f} جنيه مصري."
		),
		"report_links": get_microlab_report_links(company, branch),
		"court_package": package,
	}


@frappe.whitelist()
def seed_microlab_company(*, enqueue: int = 0) -> dict:
	"""Create Microlab company and monthly expense history (2015–2026)."""
	if frappe.session.user != "Guest":
		frappe.only_for("System Manager")
	if int(enqueue or 0):
		job = frappe.enqueue(
			"omnexa_accounting.utils.microlab_company_seed._seed_microlab_company",
			queue="long",
			timeout=7200,
		)
		job_id = getattr(job, "id", None) or str(job)
		return {
			"ok": True,
			"queued": True,
			"job_id": job_id,
			"message": _("Microlab seed started in background (job {0}).").format(job_id),
		}
	return _seed_microlab_company()


def execute():
	"""bench execute entry point — runs synchronously."""
	return seed_microlab_company(enqueue=0)


def _seed_microlab_company() -> dict:
	company, branch = _ensure_company()
	accounts = _ensure_minimal_coa(company, branch)
	disabled_legacy = _disable_legacy_microlab_accounts(company, branch)
	_delete_microlab_product(company)

	capital_sayed = accounts["31011"]
	capital_elham = accounts["31012"]
	partner_sayed = accounts["3111"]
	due_from_elham = accounts["1332"]
	exp_rent = accounts["5101"]
	exp_electric = accounts["5102"]
	exp_internet = accounts["5103"]
	exp_legal = accounts["5104"]

	created = {"journal_entries": 0, "frozen_legacy_accounts": disabled_legacy}
	year_expense_totals: dict[int, Decimal] = defaultdict(Decimal)

	# —— Opening capital (سيد 8000 / إلهام 2000) funded via جاري سيد — 01-03-2015
	if not _je_exists(company, f"{SEED_TAG}-CAPITAL"):
		total_capital = CAPITAL_SAYED + CAPITAL_ELHAM
		_create_je(
			company,
			branch,
			START_DATE,
			f"{SEED_TAG}-CAPITAL",
			f"قيد رأس المال — {PARTNER_FUNDED} 80% / {PARTNER_SILENT} 20%",
			[
				_JeLine(partner_sayed, total_capital, Decimal("0"), "مدين — جاري سيد — تمويل رأس المال"),
				_JeLine(capital_sayed, Decimal("0"), CAPITAL_SAYED, "دائن — رأس مال سيد"),
				_JeLine(capital_elham, Decimal("0"), CAPITAL_ELHAM, "دائن — رأس مال إلهام"),
			],
		)
		created["journal_entries"] += 1

	# —— Formation legal fees — 01-03-2015
	if not _je_exists(company, f"{SEED_TAG}-FORMATION"):
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=START_DATE,
			reference=f"{SEED_TAG}-FORMATION",
			expense_acc=exp_legal,
			expense_code="5104",
			partner_sayed=partner_sayed,
			amount=FORMATION_AMOUNT,
			title_ar=f"أتعاب محاماة تأسيس الشركة — {COMPANY_NAME_AR}",
			year_expense_totals=year_expense_totals,
		):
			created["journal_entries"] += 1

	# —— Company modification legal fees — 01-01-2020
	if not _je_exists(company, f"{SEED_TAG}-MODIFICATION"):
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=date(2020, 1, 1),
			reference=f"{SEED_TAG}-MODIFICATION",
			expense_acc=exp_legal,
			expense_code="5104",
			partner_sayed=partner_sayed,
			amount=MODIFICATION_AMOUNT,
			title_ar="أتعاب محاماة تعديل بيانات الشركة لدى السجل التجاري",
			year_expense_totals=year_expense_totals,
		):
			created["journal_entries"] += 1

	end = min(END_DATE, getdate(today()))

	for year, month in _iter_months(START_DATE, end):
		posting = date(year, month, calendar.monthrange(year, month)[1])

		rent = _monthly_rent(year, month)
		if rent > 0:
			ref = f"{SEED_TAG}-RENT-{year:04d}-{month:02d}"
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=posting,
				reference=ref,
				expense_acc=exp_rent,
				expense_code="5101",
				partner_sayed=partner_sayed,
				amount=rent,
				title_ar=f"إيجار المقر — {month:02d}/{year}",
				year_expense_totals=year_expense_totals,
			):
				created["journal_entries"] += 1

		electric = _electricity_amount(year, month)
		ref = f"{SEED_TAG}-ELEC-{year:04d}-{month:02d}"
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=posting,
			reference=ref,
			expense_acc=exp_electric,
			expense_code="5102",
			partner_sayed=partner_sayed,
			amount=electric,
			title_ar=f"كهرباء — {month:02d}/{year}",
			year_expense_totals=year_expense_totals,
		):
			created["journal_entries"] += 1

		internet = _gradual_monthly(Decimal("250"), Decimal("525"), year)
		ref = f"{SEED_TAG}-NET-{year:04d}-{month:02d}"
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=posting,
			reference=ref,
			expense_acc=exp_internet,
			expense_code="5103",
			partner_sayed=partner_sayed,
			amount=internet,
			title_ar=f"إنترنت — {month:02d}/{year}",
			year_expense_totals=year_expense_totals,
		):
			created["journal_entries"] += 1

		if month == 12:
			legal = _annual_legal_fee(year)
			ref = f"{SEED_TAG}-LEGAL-{year:04d}"
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=posting,
				reference=ref,
				expense_acc=exp_legal,
				expense_code="5104",
				partner_sayed=partner_sayed,
				amount=legal,
				title_ar=f"أتعاب محاماة وامتثال سنوي — {year}",
				year_expense_totals=year_expense_totals,
			):
				created["journal_entries"] += 1

	# —— Year-end: 20% of annual expenses → مستحق من إلهام / جاري سيد
	expense_cum = _cumulative_by_year(year_expense_totals)
	for year in range(START_DATE.year, end.year + 1):
		annual = year_expense_totals.get(year, Decimal("0"))
		if _recognize_elham_expense_share(
			company,
			branch,
			year,
			due_from_elham=due_from_elham,
			partner_current_sayed=partner_sayed,
			annual_expenses=annual,
		):
			created["journal_entries"] += 1

	frappe.db.commit()
	legal_report = get_microlab_legal_report(company)
	return {
		"ok": True,
		"company": company,
		"company_name": COMPANY_NAME,
		"company_name_ar": COMPANY_NAME_AR,
		"branch": branch,
		"accounts": {
			"capital_sayed": "31011",
			"capital_elham": "31012",
			"sayed_current": "3111",
			"due_from_elham": "1332",
			"expenses": sorted(EXPENSE_CODES),
		},
		"period": {"from": str(START_DATE), "to": str(end)},
		"created": created,
		"year_expense_totals": {str(y): float(v) for y, v in sorted(year_expense_totals.items())},
		"year_expense_cumulative": {str(y): float(v) for y, v in sorted(expense_cum.items())},
		"legal_report": legal_report,
		"report_links": get_microlab_report_links(company, branch),
		"message": _("Microlab company seeded (minimal chart, litigation reports ready)."),
	}


@frappe.whitelist()
def get_partner_equity_report(company: str | None = None) -> dict:
	"""Backward-compatible alias — returns Microlab legal litigation package."""
	return get_microlab_legal_report(company)
