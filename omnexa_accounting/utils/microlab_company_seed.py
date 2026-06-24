# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Seed Microlab company — legal partner debt tracking + litigation-ready accounting.

Key legal/accounting model:
- 100% of historical funding paid by Partner 1 (سيد هاشم حسن).
- Expenses are *never* split at entry time; they stay as actually paid:
  Dr Expense / Cr Partner Current — Sayed (3111)
- Year-end engines:
  - Close current year result into partner retained earnings (3191/3192) by ownership %.
  - Recognize Elham unpaid funding share as Due From Partner — Elham (1332),
    offset to Partner Current — Sayed (3111) as recoverable claim.
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
FORMATION_AMOUNT = Decimal("14000")
MODIFICATION_AMOUNT = Decimal("15000")
PRODUCT_VALUE = Decimal("150000")
PRODUCT_NAME = "برنامج ERP ونقاط بيع POS"
SEED_TAG = "MICROLAB-SEED"

# Arabic GL labels (fallback for legal outputs)
ACCOUNTS_AR = {
	"5104": "إيجارات وتأجير — مصروفات تشغيلية",
	"5105": "مرافق واتصالات — كهرباء ومياه وإنترنت",
	"5107": "اتعاب مهنية وقانونية — تأسيس وتعديل بيانات",
	"5109": "تكاليف تمويل — عمولات ورسوم بنكية",
	"5111": "صيانة وإصلاحات — المقر والأجهزة",
	"5106": "قرطاسية ومطبوعات — مستلزمات مكتبية",
	"1104": "مخزون برمجيات — أصل متداول (ERP/POS)",
	"3101": f"رأس مال الشريك — {PARTNER_FUNDED}",
	"3102": f"رأس مال الشريك — {PARTNER_SILENT}",
	"3111": f"جاري الشريك — {PARTNER_FUNDED}",
	"3112": f"جاري الشريك — {PARTNER_SILENT}",
	"3191": f"أرباح محتجزة — {PARTNER_FUNDED}",
	"3192": f"أرباح محتجزة — {PARTNER_SILENT}",
	"1331": f"مدينون — مستحق من الشريك {PARTNER_FUNDED}",
	"1332": f"مدينون — مستحق من الشريك {PARTNER_SILENT}",
	"3103": "نتيجة العام الحالي (إقفال)",
}


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
	return ACCOUNTS_AR.get(code, frappe.db.get_value("GL Account", acc, "account_name") or code)


def _ensure_partner_accounts(company: str, branch: str | None, parent_map: dict) -> dict[str, str]:
	from omnexa_accounting.utils.production_readiness import _ensure_account

	# NOTE: base CoA uses 3101/3102 as Share Capital / Retained Earnings defaults.
	# For legal partner tracking we create partner-specific accounts:
	# - Partner Capital: 31011/31012
	# - Partner Current: 3111/3112
	# - Retained Earnings: 3191/3192
	# - Due From Partner: 1331/1332
	entries = [
		{
			"code": "31011",
			"name_en": f"Partner Capital — {PARTNER_FUNDED}",
			"name_ar": f"رأس مال الشريك — {PARTNER_FUNDED}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Capital",
		},
		{
			"code": "31012",
			"name_en": f"Partner Capital — {PARTNER_SILENT}",
			"name_ar": f"رأس مال الشريك — {PARTNER_SILENT}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Capital",
		},
		{
			"code": "3111",
			"name_en": f"Partner Current — {PARTNER_FUNDED}",
			"name_ar": f"جاري الشريك — {PARTNER_FUNDED}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Partner Current",
		},
		{
			"code": "3112",
			"name_en": f"Partner Current — {PARTNER_SILENT}",
			"name_ar": f"جاري الشريك — {PARTNER_SILENT}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Partner Current",
		},
		{
			"code": "3191",
			"name_en": f"Retained Earnings — {PARTNER_FUNDED}",
			"name_ar": f"الأرباح المحتجزة — {PARTNER_FUNDED}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Retained Earnings",
		},
		{
			"code": "3192",
			"name_en": f"Retained Earnings — {PARTNER_SILENT}",
			"name_ar": f"الأرباح المحتجزة — {PARTNER_SILENT}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Retained Earnings",
		},
		{
			"code": "1331",
			"name_en": f"Due From Partner — {PARTNER_FUNDED}",
			"name_ar": f"مدينون — مستحق من الشريك {PARTNER_FUNDED}",
			"type": "Asset",
			"group": 0,
			"parent": "13",
			"main": "Assets",
			"sub": "Other Receivables",
		},
		{
			"code": "1332",
			"name_en": f"Due From Partner — {PARTNER_SILENT}",
			"name_ar": f"مدينون — مستحق من الشريك {PARTNER_SILENT}",
			"type": "Asset",
			"group": 0,
			"parent": "13",
			"main": "Assets",
			"sub": "Other Receivables",
		},
	]
	out = {}
	for entry in entries:
		out[entry["code"]] = _ensure_account(entry, company, branch, parent_map)
	return out


def _ensure_operating_accounts(company: str, branch: str | None, parent_map: dict) -> dict[str, str]:
	"""Accounts required by Microlab seed but only in General activity extension."""
	from omnexa_accounting.utils.production_readiness import _ensure_account

	entries = [
		{
			"code": "5111",
			"name_en": "Repairs & Maintenance",
			"name_ar": ACCOUNTS_AR["5111"],
			"type": "Expense",
			"group": 0,
			"parent": "5",
			"main": "Expense",
			"sub": "OPEX",
			"pl_bucket": "Operating Expense",
		},
	]
	out: dict[str, str] = {}
	for entry in entries:
		out[entry["code"]] = _ensure_account(entry, company, branch, parent_map)
	return out


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


def _ensure_coa(company: str, branch: str) -> dict:
	from omnexa_accounting.utils.production_readiness import _run_professional_coa_sync

	result = _run_professional_coa_sync(company, branch, "Services")
	parent_map = {}
	for row in frappe.get_all(
		"GL Account",
		filters={"company": company, "branch": branch},
		fields=["name", "account_number"],
	):
		if row.account_number:
			parent_map[row.account_number] = row.name
	partners = _ensure_partner_accounts(company, branch, parent_map)
	operating = _ensure_operating_accounts(company, branch, parent_map)
	partners.update(operating)
	return {"coa": result, "partners": partners, "parent_map": parent_map}


def _ensure_product(company: str) -> str:
	if not frappe.db.exists("DocType", "Item"):
		return ""
	code = "ERP-POS-MICROLAB"
	item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name", order_by="creation asc") or "All Item Groups"
	existing = frappe.db.get_value("Item", {"company": company, "item_code": code}, "name")
	if existing:
		return existing
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": PRODUCT_NAME,
			"company": company,
			"item_group": item_group,
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"valuation_rate": float(PRODUCT_VALUE),
			"standard_rate": float(PRODUCT_VALUE),
			"description": "برنامج ERP ونقاط بيع — أصل متداول / مخزون برمجيات (بدون إهلاك).",
		}
	)
	item.flags.ignore_branch_access = True
	item.insert(ignore_permissions=True)
	return item.name


def _je_exists(company: str, reference: str) -> bool:
	return bool(frappe.db.exists("Journal Entry", {"company": company, "reference": reference}))


def _budget_exists(company: str, year: int) -> bool:
	title = f"موازنة تقديرية حكومية — {COMPANY_NAME_AR} — {year}"
	return bool(frappe.db.exists("Budget", {"company": company, "title": title, "docstatus": 1}))


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


def _sum_year_net_result(company: str, branch: str, year: int) -> Decimal:
	"""Compute net profit/loss for the year from Journal Entries (docstatus=1)."""
	from_date = date(year, 1, 1)
	to_date = date(year, 12, 31)
	rows = frappe.db.sql(
		"""
		SELECT
			ga.account_type,
			SUM(jea.debit) AS dr,
			SUM(jea.credit) AS cr
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE je.company=%s AND je.branch=%s AND je.docstatus=1
		  AND je.posting_date BETWEEN %s AND %s
		GROUP BY ga.account_type
		""",
		(company, branch, from_date, to_date),
		as_dict=True,
	)
	revenue = Decimal("0")
	expense = Decimal("0")
	for r in rows:
		at = (r.account_type or "").strip()
		dr = _d(r.dr or 0)
		cr = _d(r.cr or 0)
		if at in ("Revenue", "Income"):
			revenue += cr - dr
		elif at == "Expense":
			expense += dr - cr
	return _d(revenue - expense)


def _close_year_result_to_retained(
	company: str,
	branch: str,
	year: int,
	*,
	current_year_result_acc: str,
	retained_sayed: str,
	retained_elham: str,
) -> bool:
	"""Post closing entry: 3103 -> retained earnings split by ownership."""
	ref = f"{SEED_TAG}-CLOSE-PL-{year}"
	if _je_exists(company, ref):
		return False
	net = _sum_year_net_result(company, branch, year)
	if net == 0:
		return False
	sayed_share = _d(net * OWNERSHIP_SAYED)
	elham_share = _d(net - sayed_share)
	remarks = f"قيد إقفال نتيجة العام {year} وتوزيع الربح/الخسارة حسب نسب الملكية (80%/20%)"
	lines: list[_JeLine] = []
	posting = date(year, 12, 31)
	# Profit: net > 0
	if net > 0:
		lines.append(_JeLine(current_year_result_acc, net, Decimal("0"), f"مدين — إقفال ربح العام {year}"))
		lines.append(_JeLine(retained_sayed, Decimal("0"), sayed_share, f"دائن — أرباح محتجزة سيد ({int(OWNERSHIP_SAYED*100)}%)"))
		lines.append(_JeLine(retained_elham, Decimal("0"), elham_share, f"دائن — أرباح محتجزة إلهام ({int(OWNERSHIP_ELHAM*100)}%)"))
	else:
		loss = _d(-net)
		lines.append(_JeLine(current_year_result_acc, Decimal("0"), loss, f"دائن — إقفال خسارة العام {year}"))
		lines.append(_JeLine(retained_sayed, _d(loss * OWNERSHIP_SAYED), Decimal("0"), f"مدين — خسائر محتجزة سيد ({int(OWNERSHIP_SAYED*100)}%)"))
		lines.append(_JeLine(retained_elham, _d(loss * OWNERSHIP_ELHAM), Decimal("0"), f"مدين — خسائر محتجزة إلهام ({int(OWNERSHIP_ELHAM*100)}%)"))
	return bool(_create_je(company, branch, posting, ref, remarks, lines))


def _recognize_elham_funding_debt(
	company: str,
	branch: str,
	year: int,
	*,
	due_from_elham: str,
	partner_current_sayed: str,
	total_funding_to_date: Decimal,
	elham_actual_paid_to_date: Decimal,
) -> bool:
	"""Recognize Elham unpaid share of total funding as receivable (1332) owed to Sayed (3111)."""
	ref = f"{SEED_TAG}-DEBT-{year}"
	if _je_exists(company, ref):
		return False
	required = _d(total_funding_to_date * OWNERSHIP_ELHAM)
	debt = _d(required - elham_actual_paid_to_date)
	if debt <= 0:
		return False
	remarks = (
		f"إثبات مديونية الشريك {PARTNER_SILENT} حتى 31/12/{year} "
		f"(حصة 20% من إجمالي تمويل الشركة) — مستحق لصالح {PARTNER_FUNDED}"
	)
	lines = [
		_JeLine(due_from_elham, debt, Decimal("0"), f"مدين — مستحق من {PARTNER_SILENT} حتى {year}"),
		_JeLine(partner_current_sayed, Decimal("0"), debt, f"دائن — مستحق لصالح {PARTNER_FUNDED}"),
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
	year_funding_totals: dict[int, Decimal],
) -> bool:
	if amount <= 0:
		return False
	exp_label = _account_label_ar(company, branch, expense_code)
	partner_label = _account_label_ar(company, branch, "3111")
	remarks = (
		f"{title_ar} | حساب المصروف: {exp_label} | تمويل من {PARTNER_FUNDED} | "
		f"مرجع: {reference}"
	)
	lines = [
		_JeLine(expense_acc, amount, Decimal("0"), f"مدين — {exp_label} — {title_ar}"),
		_JeLine(partner_sayed, Decimal("0"), amount, f"دائن — {partner_label} — تمويل الشريك"),
	]
	created = _create_je(company, branch, posting_date, reference, remarks, lines)
	if created:
		year_expense_totals[posting_date.year] += amount
		year_funding_totals[posting_date.year] += amount
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


def _annual_insurance(year: int) -> Decimal:
	return _d(1800 + (year - 2015) * 120)


def _quarterly_stationery(year: int, quarter: int) -> Decimal:
	return _d(400 + quarter * 50 + (year - 2015) * 30)


def _monthly_bank_charges(year: int) -> Decimal:
	return _d(75 + (year - 2015) * 5)


def _iter_months(start: date, end: date):
	cursor = get_first_day(start)
	last = get_first_day(end)
	while cursor <= last:
		yield cursor.year, cursor.month
		cursor = add_months(cursor, 1)


def _create_annual_budget(
	company: str,
	branch: str,
	year: int,
	budget_lines: list[tuple[str, str, date, Decimal]],
) -> str | None:
	if _budget_exists(company, year):
		return None
	if not budget_lines:
		return None

	from_date = date(year, 1, 1) if year > START_DATE.year else START_DATE
	to_date = date(year, 12, 31)
	if to_date > END_DATE:
		to_date = END_DATE

	title = f"موازنة تقديرية حكومية — {COMPANY_NAME_AR} — {year}"
	policy = f"قرار مجلس الإدارة / موازنة تقديرية سنوية — السنة المالية {year} — جمهورية مصر العربية"

	aggregated: dict[tuple[str, date], Decimal] = defaultdict(Decimal)
	for gl_code, _gl_name, period_month, amount in budget_lines:
		if amount <= 0:
			continue
		aggregated[(gl_code, period_month)] += _d(amount)

	rows = []
	for (gl_code, period_month), amount in sorted(aggregated.items()):
		if amount <= 0:
			continue
		acc = _account(company, branch, gl_code)
		rows.append(
			{
				"gl_account": acc,
				"period_month": period_month,
				"budget_amount": float(amount),
				"policy_reference": policy,
			}
		)
	if not rows:
		return None

	bdoc = frappe.get_doc(
		{
			"doctype": "Budget",
			"title": title,
			"company": company,
			"from_date": from_date,
			"to_date": to_date,
			"budget_scenario": "Base",
			"policy_reference": policy,
			"budget_lines": rows,
		}
	)
	bdoc.insert(ignore_permissions=True)
	_submit(bdoc)
	return bdoc.name


def _cumulative_by_year(year_totals: dict[int, Decimal]) -> dict[int, Decimal]:
	out: dict[int, Decimal] = {}
	running = Decimal("0")
	for y in sorted(year_totals.keys()):
		running += _d(year_totals[y])
		out[y] = _d(running)
	return out


@frappe.whitelist()
def seed_microlab_company(*, enqueue: int = 0) -> dict:
	"""Create Microlab company and full monthly accounting history (2015–2026)."""
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
	coa = _ensure_coa(company, branch)
	partner_sayed = coa["partners"]["3111"]
	partner_elham = coa["partners"]["3112"]
	retained_sayed = coa["partners"]["3191"]
	retained_elham = coa["partners"]["3192"]
	due_from_elham = coa["partners"]["1332"]
	product_item = _ensure_product(company)

	exp_formation = _account(company, branch, "5107")
	exp_modification = _account(company, branch, "5107")
	exp_rent = _account(company, branch, "5104")
	exp_utilities = _account(company, branch, "5105")
	exp_maintenance = _account(company, branch, "5111")
	exp_stationery = _account(company, branch, "5106")
	exp_bank = _account(company, branch, "5109")
	inventory = _account(company, branch, "1104")
	current_year_result = _account(company, branch, "3103")

	created = {"journal_entries": 0, "skipped": 0, "budgets": 0}
	year_expense_totals: dict[int, Decimal] = defaultdict(Decimal)
	year_funding_totals: dict[int, Decimal] = defaultdict(Decimal)
	budget_accumulator: dict[int, list[tuple[str, str, date, Decimal]]] = defaultdict(list)

	def _bud(year: int, code: str, label: str, period: date, amount: Decimal):
		budget_accumulator[year].append((code, label, period, amount))

	# —— Formation — 01-03-2015
	if not _je_exists(company, f"{SEED_TAG}-FORMATION"):
		_create_je(
			company,
			branch,
			START_DATE,
			f"{SEED_TAG}-FORMATION",
			f"مصروفات تأسيس الشركة — {COMPANY_NAME_AR} — بموجب عقد التأسيس",
			[
				_JeLine(
					exp_formation,
					FORMATION_AMOUNT,
					Decimal("0"),
					f"مدين — {_account_label_ar(company, branch, '5107')} — تأسيس",
				),
				_JeLine(
					partner_sayed,
					Decimal("0"),
					FORMATION_AMOUNT,
					f"دائن — {_account_label_ar(company, branch, '3111')} — تمويل سيد هاشم",
				),
			],
		)
		created["journal_entries"] += 1
		year_funding_totals[START_DATE.year] += FORMATION_AMOUNT

	# —— Product capitalization
	if not _je_exists(company, f"{SEED_TAG}-PRODUCT"):
		_create_je(
			company,
			branch,
			START_DATE,
			f"{SEED_TAG}-PRODUCT",
			f"قيد إثبات المنتج البرمجي (ERP/POS) — مخزون / أصل متداول — {PRODUCT_NAME}",
			[
				_JeLine(
					inventory,
					PRODUCT_VALUE,
					Decimal("0"),
					f"مدين — {_account_label_ar(company, branch, '1104')}",
				),
				_JeLine(
					partner_sayed,
					Decimal("0"),
					PRODUCT_VALUE,
					f"دائن — {_account_label_ar(company, branch, '3111')} — تمويل سيد هاشم",
				),
			],
		)
		created["journal_entries"] += 1
		year_funding_totals[START_DATE.year] += PRODUCT_VALUE

	# —— Company modification — 01-01-2020
	if not _je_exists(company, f"{SEED_TAG}-MODIFICATION"):
		_create_je(
			company,
			branch,
			date(2020, 1, 1),
			f"{SEED_TAG}-MODIFICATION",
			"مصروفات تعديل بيانات الشركة لدى السجل التجاري",
			[
				_JeLine(
					exp_modification,
					MODIFICATION_AMOUNT,
					Decimal("0"),
					f"مدين — {_account_label_ar(company, branch, '5107')} — تعديل بيانات",
				),
				_JeLine(
					partner_sayed,
					Decimal("0"),
					MODIFICATION_AMOUNT,
					f"دائن — {_account_label_ar(company, branch, '3111')}",
				),
			],
		)
		created["journal_entries"] += 1
		year_funding_totals[2020] += MODIFICATION_AMOUNT

	end = min(END_DATE, getdate(today()))

	for year, month in _iter_months(START_DATE, end):
		posting = date(year, month, calendar.monthrange(year, month)[1])
		month_first = date(year, month, 1)

		rent = _monthly_rent(year, month)
		if rent > 0:
			ref = f"{SEED_TAG}-RENT-{year:04d}-{month:02d}"
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=posting,
				reference=ref,
				expense_acc=exp_rent,
				expense_code="5104",
				partner_sayed=partner_sayed,
				amount=rent,
				title_ar=f"إيجار المقر — {month:02d}/{year}",
				year_expense_totals=year_expense_totals,
				year_funding_totals=year_funding_totals,
			):
				created["journal_entries"] += 1
				_bud(year, "5104", "إيجارات", month_first, rent)

		electric = _electricity_amount(year, month)
		ref = f"{SEED_TAG}-ELEC-{year:04d}-{month:02d}"
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=posting,
			reference=ref,
			expense_acc=exp_utilities,
			expense_code="5105",
			partner_sayed=partner_sayed,
			amount=electric,
			title_ar=f"كهرباء ومياه — {month:02d}/{year}",
			year_expense_totals=year_expense_totals,
			year_funding_totals=year_funding_totals,
		):
			created["journal_entries"] += 1
			_bud(year, "5105", "مرافق — كهرباء", month_first, electric)

		internet = _gradual_monthly(Decimal("250"), Decimal("525"), year)
		ref = f"{SEED_TAG}-NET-{year:04d}-{month:02d}"
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=posting,
			reference=ref,
			expense_acc=exp_utilities,
			expense_code="5105",
			partner_sayed=partner_sayed,
			amount=internet,
			title_ar=f"إنترنت واتصالات — {month:02d}/{year}",
			year_expense_totals=year_expense_totals,
			year_funding_totals=year_funding_totals,
		):
			created["journal_entries"] += 1
			_bud(year, "5105", "مرافق — إنترنت", month_first, internet)

		maint = _gradual_monthly(Decimal("100"), Decimal("550"), year)
		ref = f"{SEED_TAG}-MAINT-{year:04d}-{month:02d}"
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=posting,
			reference=ref,
			expense_acc=exp_maintenance,
			expense_code="5111",
			partner_sayed=partner_sayed,
			amount=maint,
			title_ar=f"صيانة وإصلاحات — {month:02d}/{year}",
			year_expense_totals=year_expense_totals,
			year_funding_totals=year_funding_totals,
		):
			created["journal_entries"] += 1
			_bud(year, "5111", "صيانة", month_first, maint)

		bank = _monthly_bank_charges(year)
		ref = f"{SEED_TAG}-BANK-{year:04d}-{month:02d}"
		if _expense_je(
			company=company,
			branch=branch,
			posting_date=posting,
			reference=ref,
			expense_acc=exp_bank,
			expense_code="5109",
			partner_sayed=partner_sayed,
			amount=bank,
			title_ar=f"عمولات بنكية — {month:02d}/{year}",
			year_expense_totals=year_expense_totals,
			year_funding_totals=year_funding_totals,
		):
			created["journal_entries"] += 1
			_bud(year, "5109", "تكاليف تمويل", month_first, bank)

		# Quarterly stationery (Mar, Jun, Sep, Dec)
		if month in (3, 6, 9, 12):
			q = {3: 1, 6: 2, 9: 3, 12: 4}[month]
			stationery = _quarterly_stationery(year, q)
			ref = f"{SEED_TAG}-STAT-{year:04d}-Q{q}"
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=posting,
				reference=ref,
				expense_acc=exp_stationery,
				expense_code="5106",
				partner_sayed=partner_sayed,
				amount=stationery,
				title_ar=f"قرطاسية ومطبوعات — الربع {q} / {year}",
				year_expense_totals=year_expense_totals,
				year_funding_totals=year_funding_totals,
			):
				created["journal_entries"] += 1
				_bud(year, "5106", "قرطاسية", month_first, stationery)

		# Annual legal & insurance in December
		if month == 12:
			legal = _annual_legal_fee(year)
			ref = f"{SEED_TAG}-LEGAL-{year:04d}"
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=posting,
				reference=ref,
				expense_acc=exp_formation,
				expense_code="5107",
				partner_sayed=partner_sayed,
				amount=legal,
				title_ar=f"اتعاب قانونية وامتثال سنوي — {year}",
				year_expense_totals=year_expense_totals,
				year_funding_totals=year_funding_totals,
			):
				created["journal_entries"] += 1
				_bud(year, "5107", "اتعاب قانونية", month_first, legal)

			insurance = _annual_insurance(year)
			ref = f"{SEED_TAG}-INS-{year:04d}"
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=posting,
				reference=ref,
				expense_acc=exp_maintenance,
				expense_code="5111",
				partner_sayed=partner_sayed,
				amount=insurance,
				title_ar=f"تأمين مقر سنوي — {year}",
				year_expense_totals=year_expense_totals,
				year_funding_totals=year_funding_totals,
			):
				created["journal_entries"] += 1
				_bud(year, "5111", "تأمين", month_first, insurance)

	# —— Annual government budgets
	for year in range(START_DATE.year, END_DATE.year + 1):
		if budget_accumulator.get(year):
			if _create_annual_budget(company, branch, year, budget_accumulator[year]):
				created["budgets"] += 1

	# —— Year-end engines: (1) Close P/L to retained earnings, (2) Recognize Elham unpaid funding share as receivable.
	funding_cum = _cumulative_by_year(year_funding_totals)
	# For now we assume Elham actual cash funding = credits to her partner current in seed (typically 0).
	elham_actual_paid_to_date = Decimal("0")
	for year in range(START_DATE.year, end.year + 1):
		# (1) closing entry
		if _close_year_result_to_retained(
			company,
			branch,
			year,
			current_year_result_acc=current_year_result,
			retained_sayed=retained_sayed,
			retained_elham=retained_elham,
		):
			created["journal_entries"] += 1
		# (2) debt recognition vs total funding to date
		total_funding_to_date = funding_cum.get(year, Decimal("0"))
		if _recognize_elham_funding_debt(
			company,
			branch,
			year,
			due_from_elham=due_from_elham,
			partner_current_sayed=partner_sayed,
			total_funding_to_date=total_funding_to_date,
			elham_actual_paid_to_date=elham_actual_paid_to_date,
		):
			created["journal_entries"] += 1

	frappe.db.commit()
	partner_report = get_partner_equity_report(company)
	return {
		"ok": True,
		"company": company,
		"company_name": COMPANY_NAME,
		"company_name_ar": COMPANY_NAME_AR,
		"branch": branch,
		"product_item": product_item,
		"period": {"from": str(START_DATE), "to": str(end)},
		"created": created,
		"year_expense_totals": {str(y): float(v) for y, v in sorted(year_expense_totals.items())},
		"year_funding_totals": {str(y): float(v) for y, v in sorted(year_funding_totals.items())},
		"partner_report": partner_report,
		"message": _("Microlab company seeded successfully (legal debt tracking enabled)."),
	}


@frappe.whitelist()
def get_partner_equity_report(company: str | None = None) -> dict:
	company = company or COMPANY_ABBR
	if not frappe.db.exists("Company", company):
		return {"error": "Company not found"}

	branch = frappe.db.get_value("Branch", {"company": company}, "name")
	partner_sayed_acc = frappe.db.get_value(
		"GL Account", {"company": company, "account_number": "3111", "branch": branch}, "name"
	)
	partner_elham_acc = frappe.db.get_value(
		"GL Account", {"company": company, "account_number": "3112", "branch": branch}, "name"
	)

	from omnexa_accounting.utils.ledger_tools import get_gl_account_balance

	sayed_bal = Decimal("0")
	elham_bal = Decimal("0")
	if partner_sayed_acc:
		sayed_bal = _d(get_gl_account_balance(company, partner_sayed_acc, branch=branch).get("balance") or 0)
	if partner_elham_acc:
		elham_bal = _d(get_gl_account_balance(company, partner_elham_acc, branch=branch).get("balance") or 0)

	# Equity partner current: credit balance negative in some conventions — normalize for display
	sayed_credit = -sayed_bal if sayed_bal < 0 else sayed_bal
	elham_debit = elham_bal if elham_bal > 0 else -elham_bal

	total_expense_alloc = elham_debit
	ownership_target_20 = _d(sayed_credit * OWNERSHIP_ELHAM / (Decimal("1") - OWNERSHIP_ELHAM))

	return {
		"company": company,
		"company_name": COMPANY_NAME,
		"company_name_ar": COMPANY_NAME_AR,
		"partner_funded": PARTNER_FUNDED,
		"partner_silent": PARTNER_SILENT,
		"ownership_funded_pct": 80,
		"ownership_silent_pct": 20,
		"sayed_role": "دائن (ممول)",
		"elham_role": "مدين (حصة 20% من المصروفات)",
		"sayed_partner_current_balance": float(sayed_bal),
		"sayed_display_credit": float(sayed_credit),
		"elham_partner_current_balance": float(elham_bal),
		"elham_display_debit": float(elham_debit),
		"elham_cumulative_20pct_expenses": float(total_expense_alloc),
		"elham_capital_gap_to_20pct": float(max(Decimal("0"), ownership_target_20)),
		"reports_hint": {
			"trial_balance": f"/app/query-report/Trial Balance?company={company}",
			"balance_sheet": f"/app/query-report/Balance Sheet?company={company}",
			"profit_and_loss": f"/app/query-report/Profit and Loss Statement?company={company}",
			"general_ledger": f"/app/query-report/General Ledger?company={company}",
			"budget_vs_actual": f"/app/query-report/Budget vs Actual?company={company}",
		},
	}
