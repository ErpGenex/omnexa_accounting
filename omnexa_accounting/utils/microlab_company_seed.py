# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Seed Microlab company — full accounting history from Mar 2015 to today."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, get_last_day, getdate, today

COMPANY_ABBR = "MLAB"
COMPANY_NAME = "Microlab Information Systems"
COMPANY_NAME_AR = "ميكرولاب لتطوير نظم المعلومات"
START_DATE = date(2015, 3, 1)
PARTNER_FUNDED = "سيد هاشم حسن"
PARTNER_SILENT = "إلهام مصطفى محمد أحمد"
FORMATION_AMOUNT = Decimal("14000")
MODIFICATION_AMOUNT = Decimal("15000")
PRODUCT_VALUE = Decimal("150000")
PRODUCT_NAME = "برنامج ERP ونقاط بيع POS"
SEED_TAG = "MICROLAB-SEED"


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


def _ensure_partner_accounts(company: str, branch: str | None, parent_map: dict) -> dict[str, str]:
	from omnexa_accounting.utils.production_readiness import _ensure_account

	entries = [
		{
			"code": "3111",
			"name_en": f"Partner Current — {PARTNER_FUNDED}",
			"name_ar": f"جاري الشريك {PARTNER_FUNDED}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Partner Current",
		},
		{
			"code": "3112",
			"name_en": f"Partner Current — {PARTNER_SILENT}",
			"name_ar": f"جاري الشريك {PARTNER_SILENT}",
			"type": "Equity",
			"group": 0,
			"parent": "3",
			"main": "Equity",
			"sub": "Partner Current",
		},
	]
	out = {}
	for entry in entries:
		out[entry["code"]] = _ensure_account(entry, company, branch, parent_map)
	return out


def _ensure_company() -> tuple[str, str]:
	if frappe.db.exists("Company", COMPANY_ABBR):
		company = COMPANY_ABBR
		if frappe.db.has_column("Company", "business_activity"):
			current = frappe.db.get_value("Company", COMPANY_ABBR, "business_activity")
			if current in (None, "", "Software"):
				frappe.db.set_value(
					"Company",
					COMPANY_ABBR,
					{"business_activity": "Services", "industry_sector": "Services"},
					update_modified=False,
				)
		if frappe.db.has_column("Company", "industry_sector"):
			sector = frappe.db.get_value("Company", COMPANY_ABBR, "industry_sector")
			if sector in (None, "", "Software"):
				frappe.db.set_value("Company", COMPANY_ABBR, "industry_sector", "Services", update_modified=False)
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
			"description": "Internally developed ERP & POS software — current asset / inventory, no depreciation.",
		}
	)
	item.flags.ignore_branch_access = True
	item.insert(ignore_permissions=True)
	return item.name


def _je_exists(company: str, reference: str) -> bool:
	return bool(frappe.db.exists("Journal Entry", {"company": company, "reference": reference}))


def _create_je(
	company: str,
	branch: str,
	posting_date: date,
	reference: str,
	remarks: str,
	lines: list[tuple[str, Decimal, Decimal]],
) -> str | None:
	if _je_exists(company, reference):
		return frappe.db.get_value("Journal Entry", {"company": company, "reference": reference}, "name")

	accounts = []
	for acc, debit, credit in lines:
		if debit <= 0 and credit <= 0:
			continue
		accounts.append({"account": acc, "debit": float(debit), "credit": float(credit)})

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


def _gradual_monthly(start: Decimal, end: Decimal, year: int, start_year: int = 2015, end_year: int | None = None) -> Decimal:
	end_year = end_year or date.today().year
	if year <= start_year:
		return start
	if year >= end_year:
		return end
	span = end_year - start_year
	step = (end - start) / span
	return _d(start + step * (year - start_year))


def _electricity_amount(year: int, month: int) -> Decimal:
	# 100–200 EGP, stable pseudo-random spread
	base = 100 + ((year * 12 + month) % 101)
	return _d(min(200, max(100, base)))


def _iter_months(start: date, end: date):
	cursor = get_first_day(start)
	last = get_first_day(end)
	while cursor <= last:
		yield cursor.year, cursor.month
		cursor = add_months(cursor, 1)


@frappe.whitelist()
def seed_microlab_company(*, enqueue: int = 0) -> dict:
	"""Create Microlab company and full monthly accounting history."""
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
	product_item = _ensure_product(company)

	exp_formation = _account(company, branch, "5109")
	exp_modification = _account(company, branch, "5109")
	exp_rent = _account(company, branch, "5104")
	exp_utilities = _account(company, branch, "5105")
	exp_maintenance = _account(company, branch, "5108")
	inventory = _account(company, branch, "1104")

	created = {"journal_entries": 0, "skipped": 0}

	# Formation — 01-03-2015
	if not _je_exists(company, f"{SEED_TAG}-FORMATION"):
		_create_je(
			company,
			branch,
			START_DATE,
			f"{SEED_TAG}-FORMATION",
			"مصروفات تأسيس الشركة",
			[(exp_formation, FORMATION_AMOUNT, Decimal("0")), (partner_sayed, Decimal("0"), FORMATION_AMOUNT)],
		)
		created["journal_entries"] += 1

	# Product capitalization as inventory / current asset
	if not _je_exists(company, f"{SEED_TAG}-PRODUCT"):
		_create_je(
			company,
			branch,
			START_DATE,
			f"{SEED_TAG}-PRODUCT",
			"قيد المنتج البرمجي — مخزون/أصل متداول",
			[(inventory, PRODUCT_VALUE, Decimal("0")), (partner_sayed, Decimal("0"), PRODUCT_VALUE)],
		)
		created["journal_entries"] += 1

	# Company modification — 01-01-2020
	if not _je_exists(company, f"{SEED_TAG}-MODIFICATION"):
		_create_je(
			company,
			branch,
			date(2020, 1, 1),
			f"{SEED_TAG}-MODIFICATION",
			"مصروفات تعديل بيانات الشركة",
			[(exp_modification, MODIFICATION_AMOUNT, Decimal("0")), (partner_sayed, Decimal("0"), MODIFICATION_AMOUNT)],
		)
		created["journal_entries"] += 1

	end = getdate(today())
	for year, month in _iter_months(START_DATE, end):
		posting = date(year, month, calendar.monthrange(year, month)[1])
		rent = _monthly_rent(year, month)
		if rent > 0:
			ref = f"{SEED_TAG}-RENT-{year:04d}-{month:02d}"
			if _create_je(
				company,
				branch,
				posting,
				ref,
				f"إيجار {month:02d}/{year}",
				[(exp_rent, rent, Decimal("0")), (partner_sayed, Decimal("0"), rent)],
			):
				created["journal_entries"] += 1
			else:
				created["skipped"] += 1

		electric = _electricity_amount(year, month)
		ref = f"{SEED_TAG}-ELEC-{year:04d}-{month:02d}"
		if _create_je(
			company,
			branch,
			posting,
			ref,
			f"كهرباء {month:02d}/{year}",
			[(exp_utilities, electric, Decimal("0")), (partner_sayed, Decimal("0"), electric)],
		):
			created["journal_entries"] += 1

		internet = _gradual_monthly(Decimal("250"), Decimal("525"), year)
		ref = f"{SEED_TAG}-NET-{year:04d}-{month:02d}"
		if _create_je(
			company,
			branch,
			posting,
			ref,
			f"إنترنت {month:02d}/{year}",
			[(exp_utilities, internet, Decimal("0")), (partner_sayed, Decimal("0"), internet)],
		):
			created["journal_entries"] += 1

		maint = _gradual_monthly(Decimal("100"), Decimal("550"), year)
		ref = f"{SEED_TAG}-MAINT-{year:04d}-{month:02d}"
		if _create_je(
			company,
			branch,
			posting,
			ref,
			f"صيانة مكتب {month:02d}/{year}",
			[(exp_maintenance, maint, Decimal("0")), (partner_sayed, Decimal("0"), maint)],
		):
			created["journal_entries"] += 1

	frappe.db.commit()
	partner_report = get_partner_equity_report(company)
	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"product_item": product_item,
		"created": created,
		"partner_report": partner_report,
		"message": _("Microlab company seeded successfully."),
	}


@frappe.whitelist()
def get_partner_equity_report(company: str | None = None) -> dict:
	company = company or COMPANY_ABBR
	if not frappe.db.exists("Company", company):
		return {"error": "Company not found"}

	branch = frappe.db.get_value("Branch", {"company": company}, "name")
	partner_acc = frappe.db.get_value(
		"GL Account", {"company": company, "account_number": "3111", "branch": branch}, "name"
	)
	sayed_total = Decimal("0")
	if partner_acc:
		from omnexa_accounting.utils.ledger_tools import get_gl_account_balance

		bal = get_gl_account_balance(company, partner_acc, branch=branch)
		sayed_total = _d(bal.get("balance") or 0)

	ownership_target_20 = _d(sayed_total * Decimal("0.20") / Decimal("0.80"))
	return {
		"company": company,
		"partner_funded": PARTNER_FUNDED,
		"partner_silent": PARTNER_SILENT,
		"ownership_funded_pct": 80,
		"ownership_silent_pct": 20,
		"sayed_paid_total": float(sayed_total),
		"sayed_partner_current_balance": float(sayed_total),
		"elham_paid_total": 0.0,
		"elham_capital_gap_to_20pct": float(max(Decimal("0"), ownership_target_20)),
		"reports_hint": {
			"trial_balance": f"/app/query-report/Trial Balance?company={company}",
			"balance_sheet": f"/app/query-report/Balance Sheet?company={company}",
			"profit_and_loss": f"/app/query-report/Profit and Loss Statement?company={company}",
			"general_ledger": f"/app/query-report/General Ledger?company={company}",
		},
	}
