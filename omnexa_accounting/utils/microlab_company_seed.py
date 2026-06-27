# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Seed Microlab company — minimal partner litigation accounting (2015–2026).

Accounting model (per legal instructions):
- Chart: capital (سيد 8000 / إلهام 2000), جاري سيد, مستحق من إلهام, seven expense accounts.
- Monthly: إيجار، إنترنت، كهرباء، صيانة، مياه (per spreadsheet / rent schedule by year).
- One-time: مصروفات التأسيس (2015)، مصروفات تعديل السجل (2020).
- Every expense: Dr Expense / Cr جاري سيد (paid by سيد هاشم حسن).
- Year-end: Dr مستحق من إلهام / Cr جاري سيد for 20% of annual expenses (إلهام مصطفى محمد أحمد).
- Account names and journal entry text: Arabic only.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, getdate, now_datetime, today

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
MODIFICATION_AMOUNT = Decimal("10000")
SEED_TAG = "MICROLAB-SEED"
EXPENSE_EMPLOYEE_NAME = "سيد هاشم حسن"
EXPENSE_EMPLOYEE_CODE = "MLAB-EXP-001"
EXPENSE_DOCTYPE = "HR Expense Claim"
SEED_LOGGER = "microlab_company_seed"

# Monthly rates by year (spreadsheet); years without a row inherit the previous defined year.
_YEARLY_RATES_TABLE: dict[int, dict[str, str]] = {
	2015: {"internet": "180", "electricity": "100", "maintenance": "200", "water": "50"},
	2019: {"internet": "240", "electricity": "120", "maintenance": "250", "water": "75"},
	2020: {"internet": "240", "electricity": "120", "maintenance": "300", "water": "100"},
	2021: {"internet": "240", "electricity": "150", "maintenance": "350", "water": "125"},
	2022: {"internet": "240", "electricity": "170", "maintenance": "400", "water": "150"},
	2023: {"internet": "240", "electricity": "200", "maintenance": "450", "water": "175"},
	2024: {"internet": "319.2", "electricity": "300", "maintenance": "500", "water": "200"},
	2026: {"internet": "450.3", "electricity": "500", "maintenance": "550", "water": "225"},
}

_MONTHLY_EXPENSE_SPECS: tuple[tuple[str, str, str], ...] = (
	("internet", "5101", "مصروف الإنترنت"),
	("electricity", "5102", "مصروف الكهرباء"),
	("maintenance", "5103", "مصروف الصيانة"),
	("water", "5104", "مصروف المياه"),
)

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
		"name_en": "مصروف الإنترنت",
		"name_ar": "مصروف الإنترنت",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5102",
		"name_en": "مصروف الكهرباء",
		"name_ar": "مصروف الكهرباء",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5103",
		"name_en": "مصروف الصيانة",
		"name_ar": "مصروف الصيانة",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5104",
		"name_en": "مصروف المياه",
		"name_ar": "مصروف المياه",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5107",
		"name_en": "مصروف الإيجار",
		"name_ar": "مصروف الإيجار",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5105",
		"name_en": "مصروفات التأسيس",
		"name_ar": "مصروفات التأسيس",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
	{
		"code": "5106",
		"name_en": "مصروفات تعديل السجل التجاري",
		"name_ar": "مصروفات تعديل السجل التجاري",
		"type": "Expense",
		"group": 0,
		"parent": "51",
		"main": "Expense",
		"sub": "OPEX",
		"pl_bucket": "Operating Expense",
	},
]

ALLOWED_ACCOUNT_CODES = frozenset(spec["code"] for spec in ACCOUNT_SPECS)
EXPENSE_CODES = frozenset({"5101", "5102", "5103", "5104", "5105", "5106", "5107"})

# Legacy codes to disable when re-seeding (assets / inventory / software / extra OPEX)
LEGACY_CODES_TO_DISABLE = frozenset(
	{
		"1104",
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


def _seed_logger():
	"""إرجاع مسجل مخصص لبذرة ميكرولاب."""
	return frappe.logger(SEED_LOGGER)


def _log_info(message: str, payload: dict | None = None) -> None:
	"""تسجيل رسالة معلومات بعد كل عملية إدخال أو خطوة مهمة."""
	try:
		_seed_logger().info({"message": message, "payload": payload or {}, "ts": str(now_datetime())})
	except Exception:
		pass


def _log_failure(title: str, exc: Exception, payload: dict | None = None) -> None:
	"""تسجيل الأخطاء في سجل النظام مع تفاصيل كافية للتتبع."""
	frappe.log_error(
		title=title,
		message=frappe.as_json(
			{
				"error": str(exc),
				"payload": payload or {},
				"traceback": frappe.get_traceback(),
			},
			indent=2,
		),
	)


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


def _default_cost_center(company: str) -> str | None:
	"""إرجاع مركز التكلفة الافتراضي للشركة إن وجد."""
	if not frappe.db.exists("DocType", "Cost Center"):
		return None
	return frappe.db.get_value("Cost Center", {"company": company}, "name", order_by="creation asc") or None


def _ensure_expense_employee(company: str, cost_center: str | None = None) -> str:
	"""إنشاء موظف افتراضي لاستخدامه في سجلات المصروفات عند الحاجة."""
	existing = frappe.db.get_value(
		"Employee",
		{"company": company, "employee_code": EXPENSE_EMPLOYEE_CODE},
		"name",
	)
	if existing:
		return existing

	doc = frappe.get_doc(
		{
			"doctype": "Employee",
			"employee_code": EXPENSE_EMPLOYEE_CODE,
			"employee_name": EXPENSE_EMPLOYEE_NAME,
			"company": company,
			"department": "الإدارة",
			"designation": "مسؤول مصروفات الشركة",
			"date_of_joining": str(START_DATE),
			"status": "Active",
			"external_reference": f"{SEED_TAG}-EMPLOYEE",
		}
	)
	if cost_center and doc.meta.has_field("hr_default_cost_center"):
		doc.hr_default_cost_center = cost_center
	doc.insert(ignore_permissions=True)
	_log_info("تم إنشاء موظف المصروفات الافتراضي", {"employee": doc.name, "company": company})
	return doc.name


def _expense_claim_reference(kind: str, year: int, month: int | None = None) -> str:
	"""مرجع فريد لمنع تكرار إنشاء سجلات المصروفات."""
	if month is None:
		return f"{SEED_TAG}-EXP-{kind}-{year:04d}"
	return f"{SEED_TAG}-EXP-{kind}-{year:04d}-{month:02d}"


def _expense_claim_exists(company: str, description: str) -> str | None:
	"""التحقق من وجود سجل مصروف سابقاً باستخدام الوصف المرجعي."""
	if not frappe.db.exists("DocType", EXPENSE_DOCTYPE):
		return None
	return frappe.db.get_value(EXPENSE_DOCTYPE, {"company": company, "description": description}, "name")


def _insert_expense_claim(
	*,
	company: str,
	branch: str,
	employee: str,
	expense_date: date,
	amount: Decimal,
	expense_type: str,
	title_ar: str,
	reference: str,
	cost_center: str | None = None,
) -> str | None:
	"""إنشاء سجل مصروف مستقل باستخدام get_doc و insert مع منع التكرار."""
	if not frappe.db.exists("DocType", EXPENSE_DOCTYPE):
		return None

	description = f"{title_ar} | {reference}"
	existing = _expense_claim_exists(company, description)
	if existing:
		_log_info("تم تجاوز سجل مصروف مكرر", {"doctype": EXPENSE_DOCTYPE, "name": existing, "reference": reference})
		return None

	try:
		doc = frappe.get_doc(
			{
				"doctype": EXPENSE_DOCTYPE,
				"employee": employee,
				"company": company,
				"branch": branch,
				"expense_date": str(expense_date),
				"posting_date": str(expense_date),
				"expense_type": expense_type,
				"amount": float(amount),
				"currency": "EGP",
				"status": "Draft",
				"description": description,
			}
		)
		if cost_center and doc.meta.has_field("cost_center"):
			doc.cost_center = cost_center
		doc.insert(ignore_permissions=True)
		_log_info(
			"تم إدخال سجل مصروف",
			{
				"doctype": EXPENSE_DOCTYPE,
				"name": doc.name,
				"reference": reference,
				"date": str(expense_date),
				"amount": float(amount),
			},
		)
		return doc.name
	except Exception as exc:
		_log_failure(
			"Microlab Expense Claim Insert Failed",
			exc,
			{
				"company": company,
				"branch": branch,
				"employee": employee,
				"expense_date": str(expense_date),
				"amount": str(amount),
				"reference": reference,
			},
		)
		raise frappe.ValidationError(f"تعذر إنشاء سجل المصروف {title_ar} بتاريخ {expense_date}: {exc}") from exc


def _write_seed_log(company: str, branch: str | None, activity: str, summary: dict, status: str = "Success") -> str | None:
	"""إنشاء سجل تشغيل للبذرة داخل Production Seed Log إن كان متاحاً."""
	if not frappe.db.exists("DocType", "Production Seed Log"):
		return None
	try:
		doc = frappe.get_doc(
			{
				"doctype": "Production Seed Log",
				"operation": "Seed Demo Data",
				"company": company,
				"branch": branch,
				"activity": activity,
				"executed_by": frappe.session.user,
				"executed_on": now_datetime(),
				"dry_run": 0,
				"status": status,
				"summary_json": frappe.as_json(summary),
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name
	except Exception as exc:
		_log_failure("Microlab Seed Log Failed", exc, {"company": company, "branch": branch, "activity": activity})
		return None


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

	prev_lang = getattr(frappe.local, "lang", None)
	frappe.local.lang = "ar"
	try:
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
	finally:
		frappe.local.lang = prev_lang


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
	__slots__ = ("account", "debit", "credit", "remark_ar", "cost_center")

	def __init__(self, account: str, debit: Decimal, credit: Decimal, remark_ar: str, cost_center: str | None = None):
		self.account = account
		self.debit = debit
		self.credit = credit
		self.remark_ar = remark_ar
		self.cost_center = cost_center


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
		if line.cost_center:
			row["cost_center"] = line.cost_center
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
	cost_center: str | None,
	year_expense_totals: dict[int, Decimal],
) -> bool:
	if amount <= 0:
		return False
	exp_label = _account_label_ar(company, branch, expense_code)
	remarks = f"{title_ar} | {exp_label} | دفع: {PARTNER_FUNDED} | {reference}"
	lines = [
		_JeLine(expense_acc, amount, Decimal("0"), f"مدين — {exp_label}", cost_center=cost_center),
		_JeLine(partner_sayed, Decimal("0"), amount, f"دائن — جاري سيد — {PARTNER_FUNDED}", cost_center=cost_center),
	]
	created = _create_je(company, branch, posting_date, reference, remarks, lines)
	if created:
		year_expense_totals[posting_date.year] += amount
	return bool(created)


def _rates_for_year(year: int) -> dict[str, Decimal]:
	applicable = min(_YEARLY_RATES_TABLE)
	for y in sorted(_YEARLY_RATES_TABLE):
		if y <= year:
			applicable = y
	row = _YEARLY_RATES_TABLE[applicable]
	return {key: _d(value) for key, value in row.items()}


def _monthly_rent(year: int, month: int) -> Decimal:
	"""إيجار شهري — يبدأ من 03/2015؛ زيادة 10% سنوياً حتى 2020، ثم 2000 (2021–2022)، 3000 (2023+)."""
	if year < 2015 or (year == 2015 and month < 3):
		return Decimal("0")
	if year >= 2023:
		return Decimal("3000")
	if year >= 2021:
		return Decimal("2000")
	years_since_2015 = year - 2015
	base = Decimal("1000")
	return _d(base * (Decimal("1.1") ** years_since_2015))


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
def delete_microlab_company() -> dict:
	"""Delete Microlab transactions and legal setup for a fresh re-seed."""
	if frappe.session.user != "Guest":
		frappe.only_for("System Manager")
	if not frappe.db.exists("Company", COMPANY_ABBR):
		return {"ok": True, "existed": False}

	from omnexa_accounting.utils.production_readiness import run_reset_transactions_batched
	reset = {}
	try:
		from omnexa_accounting.utils.production_readiness import wipe_company_all_data

		reset = wipe_company_all_data(company=COMPANY_ABBR, confirm_text="DELETE ALL")
		if frappe.db.exists("Company", COMPANY_ABBR):
			frappe.delete_doc("Company", COMPANY_ABBR, force=1, ignore_permissions=True)
		_log_info("تم حذف شركة ميكرولاب بالكامل", {"company": COMPANY_ABBR})
	except Exception as exc:
		_log_failure("Microlab Full Company Delete Failed", exc, {"company": COMPANY_ABBR})
		reset = run_reset_transactions_batched(company=COMPANY_ABBR, limit=0, skip_log=True)
	if frappe.db.exists("DocType", EXPENSE_DOCTYPE):
		names = frappe.get_all(EXPENSE_DOCTYPE, filters={"company": COMPANY_ABBR}, pluck="name")
		for name in names:
			frappe.delete_doc(EXPENSE_DOCTYPE, name, force=1, ignore_permissions=True)
	if frappe.db.exists("DocType", "Employee"):
		employee = frappe.db.get_value("Employee", {"company": COMPANY_ABBR, "employee_code": EXPENSE_EMPLOYEE_CODE}, "name")
		if employee:
			frappe.delete_doc("Employee", employee, force=1, ignore_permissions=True)
	if frappe.db.exists("Company Partner Legal Setup", COMPANY_ABBR):
		frappe.delete_doc("Company Partner Legal Setup", COMPANY_ABBR, force=1, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "existed": True, "company": COMPANY_ABBR, "reset": reset}


def _ensure_partner_legal_setup(company: str, branch: str) -> None:
	sayed_current = frappe.db.get_value("GL Account", {"company": company, "account_number": "3111"}, "name")
	elham_due = frappe.db.get_value("GL Account", {"company": company, "account_number": "1332"}, "name")
	if not sayed_current or not elham_due:
		return

	if frappe.db.exists("Company Partner Legal Setup", company):
		doc = frappe.get_doc("Company Partner Legal Setup", company)
	else:
		doc = frappe.new_doc("Company Partner Legal Setup")
		doc.company = company

	doc.branch = branch
	doc.default_from_date = getdate(START_DATE)
	doc.default_to_date = getdate(END_DATE)
	doc.legal_case_reference = "قضية شركاء ميكرولاب"
	doc.notes = "أُنشئ تلقائياً من بذرة ميكرولاب — الشريك الممول يدفع المصروفات والشريك المدين يستحق حصة الملكية."
	doc.set("partners", [])
	doc.append(
		"partners",
		{
			"partner_name": PARTNER_FUNDED,
			"partner_name_ar": PARTNER_FUNDED,
			"ownership_percent": 80,
			"is_funding_partner": 1,
			"partner_current_account": sayed_current,
		},
	)
	doc.append(
		"partners",
		{
			"partner_name": PARTNER_SILENT,
			"partner_name_ar": PARTNER_SILENT,
			"ownership_percent": 20,
			"is_funding_partner": 0,
			"due_from_partner_account": elham_due,
		},
	)
	doc.flags.ignore_permissions = True
	doc.save()


@frappe.whitelist()
def reset_and_seed_microlab_company(*, enqueue: int = 0) -> dict:
	"""Wipe Microlab seed data and recreate company accounting from scratch."""
	if frappe.session.user != "Guest":
		frappe.only_for("System Manager")
	delete_microlab_company()
	return seed_microlab_company(enqueue=enqueue)


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
	try:
		company, branch = _ensure_company()
		accounts = _ensure_minimal_coa(company, branch)
		disabled_legacy = _disable_legacy_microlab_accounts(company, branch)
		_delete_microlab_product(company)

		capital_sayed = accounts["31011"]
		capital_elham = accounts["31012"]
		partner_sayed = accounts["3111"]
		due_from_elham = accounts["1332"]
		exp_internet = accounts["5101"]
		exp_electric = accounts["5102"]
		exp_maintenance = accounts["5103"]
		exp_water = accounts["5104"]
		exp_rent = accounts["5107"]
		exp_formation = accounts["5105"]
		exp_modification = accounts["5106"]
		expense_accounts = {
			"5101": exp_internet,
			"5102": exp_electric,
			"5103": exp_maintenance,
			"5104": exp_water,
			"5107": exp_rent,
			"5105": exp_formation,
			"5106": exp_modification,
		}
		cost_center = _default_cost_center(company)
		expense_employee = _ensure_expense_employee(company, cost_center=cost_center)

		created = {"journal_entries": 0, "expense_claims": 0, "frozen_legacy_accounts": disabled_legacy}
		year_expense_totals: dict[int, Decimal] = defaultdict(Decimal)

		# —— قيد رأس المال الافتتاحي — 01-03-2015
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

		# —— مصروفات التأسيس كسجل مستقل غير متكرر — 01-03-2015
		formation_ref = _expense_claim_reference("FORMATION", 2015)
		if _insert_expense_claim(
			company=company,
			branch=branch,
			employee=expense_employee,
			expense_date=START_DATE,
			amount=FORMATION_AMOUNT,
			expense_type="Other",
			title_ar="مصروفات التأسيس",
			reference=formation_ref,
			cost_center=cost_center,
		):
			created["expense_claims"] += 1
		if not _je_exists(company, f"{SEED_TAG}-FORMATION"):
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=START_DATE,
				reference=f"{SEED_TAG}-FORMATION",
				expense_acc=exp_formation,
				expense_code="5105",
				partner_sayed=partner_sayed,
				amount=FORMATION_AMOUNT,
				title_ar=f"مصروفات التأسيس — {COMPANY_NAME_AR}",
				cost_center=cost_center,
				year_expense_totals=year_expense_totals,
			):
				created["journal_entries"] += 1

		# —— مصروفات تعديل السجل التجاري كسجل مستقل غير متكرر — 01-01-2020
		modification_date = date(2020, 1, 1)
		modification_ref = _expense_claim_reference("MODIFICATION", 2020)
		if _insert_expense_claim(
			company=company,
			branch=branch,
			employee=expense_employee,
			expense_date=modification_date,
			amount=MODIFICATION_AMOUNT,
			expense_type="Other",
			title_ar="مصروفات تعديل السجل التجاري",
			reference=modification_ref,
			cost_center=cost_center,
		):
			created["expense_claims"] += 1
		if not _je_exists(company, f"{SEED_TAG}-MODIFICATION"):
			if _expense_je(
				company=company,
				branch=branch,
				posting_date=modification_date,
				reference=f"{SEED_TAG}-MODIFICATION",
				expense_acc=exp_modification,
				expense_code="5106",
				partner_sayed=partner_sayed,
				amount=MODIFICATION_AMOUNT,
				title_ar="مصروفات تعديل السجل التجاري",
				cost_center=cost_center,
				year_expense_totals=year_expense_totals,
			):
				created["journal_entries"] += 1

		end = min(END_DATE, getdate(today()))

		for year, month in _iter_months(START_DATE, end):
			posting = date(year, month, 1)
			rates = _rates_for_year(year)

			for rate_key, expense_code, label_ar in _MONTHLY_EXPENSE_SPECS:
				amount = rates[rate_key]
				ref = _expense_claim_reference(expense_code, year, month)
				if _insert_expense_claim(
					company=company,
					branch=branch,
					employee=expense_employee,
					expense_date=posting,
					amount=amount,
					expense_type="Other",
					title_ar=f"{label_ar} — {month:02d}/{year}",
					reference=ref,
					cost_center=cost_center,
				):
					created["expense_claims"] += 1
				if _expense_je(
					company=company,
					branch=branch,
					posting_date=posting,
					reference=f"{SEED_TAG}-{expense_code}-{year:04d}-{month:02d}",
					expense_acc=expense_accounts[expense_code],
					expense_code=expense_code,
					partner_sayed=partner_sayed,
					amount=amount,
					title_ar=f"{label_ar} — {month:02d}/{year}",
					cost_center=cost_center,
					year_expense_totals=year_expense_totals,
				):
					created["journal_entries"] += 1

			# —— إيجار شهري — حساب 5107
			rent_amount = _monthly_rent(year, month)
			if rent_amount > 0:
				rent_code = "5107"
				rent_label = "مصروف الإيجار"
				rent_ref = _expense_claim_reference(rent_code, year, month)
				if _insert_expense_claim(
					company=company,
					branch=branch,
					employee=expense_employee,
					expense_date=posting,
					amount=rent_amount,
					expense_type="Other",
					title_ar=f"{rent_label} — {month:02d}/{year}",
					reference=rent_ref,
					cost_center=cost_center,
				):
					created["expense_claims"] += 1
				if _expense_je(
					company=company,
					branch=branch,
					posting_date=posting,
					reference=f"{SEED_TAG}-{rent_code}-{year:04d}-{month:02d}",
					expense_acc=expense_accounts[rent_code],
					expense_code=rent_code,
					partner_sayed=partner_sayed,
					amount=rent_amount,
					title_ar=f"{rent_label} — {month:02d}/{year}",
					cost_center=cost_center,
					year_expense_totals=year_expense_totals,
				):
					created["journal_entries"] += 1

		# —— إثبات حصة الشريك من إجمالي المصروفات السنوية
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
		_ensure_partner_legal_setup(company, branch)
		frappe.db.commit()
		legal_report = get_microlab_legal_report(company)
		summary = {
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
			"default_cost_center": cost_center,
			"expense_employee": expense_employee,
			"year_expense_totals": {str(y): float(v) for y, v in sorted(year_expense_totals.items())},
			"year_expense_cumulative": {str(y): float(v) for y, v in sorted(expense_cum.items())},
			"legal_report": legal_report,
			"report_links": get_microlab_report_links(company, branch),
			"message": _("Microlab company seeded (minimal chart, litigation reports ready)."),
		}
		summary["seed_log"] = _write_seed_log(company, branch, "Microlab monthly expense seed", summary, status="Success")
		return summary
	except Exception as exc:
		try:
			frappe.db.rollback()
		except Exception:
			pass
		_log_failure("Microlab Seed Failed", exc, {"company": COMPANY_ABBR})
		_write_seed_log(COMPANY_ABBR, None, "Microlab monthly expense seed", {"error": str(exc)}, status="Failed")
		raise


@frappe.whitelist()
def get_partner_equity_report(company: str | None = None) -> dict:
	"""Backward-compatible alias — returns Microlab legal litigation package."""
	return get_microlab_legal_report(company)
