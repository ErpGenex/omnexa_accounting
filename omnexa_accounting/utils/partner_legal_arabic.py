# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Arabic-only rendering helpers for partner legal PDF package."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import frappe
from frappe.utils import flt, getdate

AR_MONTHS = (
	"يناير",
	"فبراير",
	"مارس",
	"أبريل",
	"مايو",
	"يونيو",
	"يوليو",
	"أغسطس",
	"سبتمبر",
	"أكتوبر",
	"نوفمبر",
	"ديسمبر",
)

AR_EXACT: dict[str, str] = {
	"Assets": "الأصول",
	"Liabilities": "الخصوم",
	"Equity": "حقوق الملكية",
	"Revenue": "الإيرادات",
	"Income": "الإيرادات",
	"Expense": "المصروفات",
	"Balance Sheet": "الميزانية العمومية",
	"Income Statement": "قائمة الدخل",
	"Net Result": "صافي النتيجة",
	"Total Assets": "إجمالي الأصول",
	"Total Liabilities": "إجمالي الخصوم",
	"Total Equity": "إجمالي حقوق الملكية",
	"Net Profit / Loss": "صافي الربح / الخسارة",
	"Opening Balance": "الرصيد الافتتاحي",
	"Capital Contribution Deficiency": "عجز مساهمة رأس المال",
	"Expense Contribution Deficiency": "عجز مساهمة المصروفات",
	"Loss Allocation": "توزيع الخسائر",
	"Settlements / Payments": "التسويات والمدفوعات",
	"Final Amount Due": "إجمالي المبلغ المستحق",
	"Partner": "الشريك",
	"Ownership %": "نسبة الملكية",
	"Required Funding": "التمويل المطلوب",
	"Actual Funding": "التمويل الفعلي",
	"Difference": "الفرق",
	"Variance": "الفرق",
	"Total Expenses": "إجمالي المصروفات",
	"Cumulative Debt": "المديونية المتراكمة",
	"Year": "السنة",
	"Fiscal Year": "السنة المالية",
	"Section": "القسم",
	"Account": "رقم الحساب",
	"Account Name": "اسم الحساب",
	"Account Name (Arabic)": "اسم الحساب",
	"Balance": "الرصيد",
	"Amount": "المبلغ",
	"Component": "البند",
	"Notes": "ملاحظات",
	"Line": "م",
	"Line No": "م",
	"Item": "البند",
	"Value": "القيمة",
	"Date": "التاريخ",
	"Posting Date": "تاريخ القيد",
	"Journal Entry": "قيد اليومية",
	"Reference": "المرجع",
	"Expense Type": "نوع المصروف",
	"Recovery Amount": "مبلغ الاسترداد",
	"Debit": "مدين",
	"Credit": "دائن",
	"Compare Year": "سنة المقارنة",
	"Compare Cumulative": "المديونية المقارنة",
	"Compare Amount": "المبلغ المقارن",
	"Compare Value": "القيمة المقارنة",
	"Change %": "نسبة التغيير",
	"Administrator": "مدير النظام",
	"All Branches": "جميع الفروع",
	"Consolidated Group": "المجموعة الموحّدة",
	"Primary Partner": "الشريك الرئيسي",
	"Secondary Partner": "الشريك الثانوي",
	"Funding Partner": "الشريك الممول",
	"No data": "لا توجد بيانات",
	"Opening balance for selected period.": "الرصيد الافتتاحي للفترة المحددة.",
	"Partner Debt Certificate amount.": "مبلغ شهادة مديونية الشريك.",
	"Partner Debt Certificate": "شهادة مديونية الشريك",
	"Legal Claim Statement": "بيان المطالبة القانونية",
	"Liquidation Historical Report": "تقرير التصفية التاريخي",
	"Liquidation Costs": "تكاليف التصفية",
	"Net Liquidation Value": "صافي قيمة التصفية",
	"Line Item": "البند",
	"Equity Snapshot (book)": "لقطة حقوق الملكية (دفترياً)",
	"Historical Liquidation Snapshot": "ملخص التصفية التاريخي",
	"Net": "الصافي",
	"Liquidation": "التصفية",
	"Liquidation cost": "تكلفة التصفية",
	"Partner debt (due)": "مديونية الشريك (مستحق)",
	"Net liquidation value": "صافي قيمة التصفية",
	"Share after debt adjustment": "الحصة بعد تسوية المديونية",
}

AR_PHRASE_PATTERNS: list[tuple[str, str]] = [
	(r"^As at (.+)$", r"كما في \1"),
	(r"^Fiscal Year (.+)$", r"السنة المالية \1"),
	(r"^Paid by (.+)$", r"مدفوع بواسطة \1"),
	(r"^(.+) Share Before Debt$", r"حصة \1 قبل المديونية"),
	(r"^(.+) Share After Debt$", r"حصة \1 بعد المديونية"),
	(r"^(.+) Debt$", r"مديونية \1"),
	(r"^(.+) Share$", r"حصة \1"),
	(r"^(.+) Paid$", r"مسدد \1"),
	(r"^(.+) Debt \(year\)$", r"مديونية \1 (السنة)"),
	(r"^Cumulative (.+) Loss$", r"خسائر \1 المتراكمة"),
	(r"^Cumulative Recovery for (.+)$", r"الاسترداد المتراكم لـ \1"),
	(r"^(.+) unpaid ownership share of funding\.$", r"حصة الملكية غير المسددة من التمويل لـ \1."),
	(r"^(.+) unpaid expense share across funded expenses\.$", r"حصة المصروفات غير المسددة عبر المصروفات الممولة لـ \1."),
	(r"^(.+) share of cumulative losses\.$", r"حصة الخسائر المتراكمة لـ \1."),
	(r"^Credits posted as settlement \(Due From Partner account\) for (.+)\.$", r"قيود دائنة مسجّلة كتسوية (حساب مستحق من الشريك) لـ \1."),
]

AR_WORD_REPLACEMENTS = {
	" Share": " حصة",
	" Paid": " المسدد",
	" Debt": " المديونية",
	"Cumulative ": "المتراكم ",
	"Recovery ": "استرداد ",
	"Compare ": "مقارنة ",
	"Change ": "تغيير ",
}


def format_date_ar(value: Any) -> str:
	if not value:
		return "—"
	d = getdate(value)
	return f"{d.day} {AR_MONTHS[d.month - 1]} {d.year}"


def format_money_ar(value: Any) -> str:
	if value in (None, ""):
		return "—"
	amount = flt(value)
	negative = amount < 0
	amount = abs(amount)
	formatted = f"{amount:,.2f}".replace(",", "٬").replace(".", "٫")
	prefix = "(-) " if negative else ""
	return f"{prefix}{formatted} ج.م."


def get_company_name_ar(company: str) -> str:
	if frappe.db.has_column("Company", "company_name_ar"):
		name_ar = frappe.db.get_value("Company", company, "company_name_ar")
		if name_ar:
			return str(name_ar).strip()
	return frappe.db.get_value("Company", company, "company_name") or company


def get_branch_name_ar(branch: str | None) -> str:
	if not branch:
		return "جميع الفروع"
	for field in ("branch_name_ar", "branch_ar", "name_ar"):
		if frappe.db.has_column("Branch", field):
			val = frappe.db.get_value("Branch", branch, field)
			if val:
				return str(val).strip()
	return branch


def get_user_display_ar(user: str | None = None) -> str:
	user = user or frappe.session.user
	if user == "Administrator":
		return "مدير النظام"
	full_name = frappe.db.get_value("User", user, "full_name")
	return full_name or user


def _pick_account_label(row: dict) -> str:
	ar = (row.get("account_name_ar") or "").strip()
	if ar:
		return ar
	name = (row.get("account_name") or row.get("name") or "").strip()
	if not name:
		return ""
	# Prefer Arabic segment from bilingual labels like "Partner Current — جاري سيد"
	if "—" in name or " - " in name:
		for part in re.split(r"\s*[—\-]\s*", name):
			if re.search(r"[\u0600-\u06FF]", part):
				return part.strip()
	arabic_chunks = re.findall(r"[\u0600-\u06FF][\u0600-\u06FF\s]*", name)
	if arabic_chunks:
		return max(arabic_chunks, key=len).strip()
	return name


@lru_cache(maxsize=64)
def _account_maps(company: str) -> tuple[dict[str, str], dict[str, str]]:
	by_id: dict[str, str] = {}
	by_number: dict[str, str] = {}
	fields = ["name", "account_number", "account_name"]
	if frappe.db.has_column("GL Account", "account_name_ar"):
		fields.append("account_name_ar")
	for row in frappe.get_all("GL Account", filters={"company": company}, fields=fields, limit_page_length=0):
		label = _pick_account_label(row)
		by_id[row["name"]] = label
		if row.get("account_number"):
			by_number[str(row["account_number"]).strip()] = label
	return by_id, by_number


def resolve_account_label(company: str, account_ref: Any) -> str:
	if not account_ref:
		return "—"
	ref = str(account_ref).strip()
	by_id, by_number = _account_maps(company)
	if ref in by_id:
		return by_id[ref]
	if ref in by_number:
		return by_number[ref]
	if frappe.db.exists("GL Account", ref):
		return by_id.get(ref) or ref
	return arabize_text(ref)


def _apply_pattern(text: str) -> str | None:
	for pattern, repl in AR_PHRASE_PATTERNS:
		if re.match(pattern, text):
			return re.sub(pattern, repl, text)
	return None


def arabize_text(value: Any) -> str:
	if value in (None, ""):
		return "—"
	text = str(value).strip()
	if not text:
		return "—"
	if text in AR_EXACT:
		return AR_EXACT[text]
	as_at = re.match(r"^As at (.+)$", text)
	if as_at:
		return f"كما في {format_date_ar(as_at.group(1))}"
	pattern_out = _apply_pattern(text)
	if pattern_out:
		return pattern_out
	out = text
	for en, ar in AR_WORD_REPLACEMENTS.items():
		out = out.replace(en, ar)
	if out in AR_EXACT:
		return AR_EXACT[out]
	return out


def arabize_column_label(label: Any) -> str:
	text = str(label or "").strip()
	if not text:
		return "—"
	if text in AR_EXACT:
		return AR_EXACT[text]
	pattern_out = _apply_pattern(text)
	if pattern_out:
		return pattern_out
	out = text
	for en, ar in AR_WORD_REPLACEMENTS.items():
		out = out.replace(en, ar)
	for en, ar in AR_EXACT.items():
		if en in out and len(en) > 3:
			out = out.replace(en, ar)
	return out


def prepare_columns_for_arabic(columns: list[dict]) -> list[dict]:
	"""Keep one Arabic account-name column; arabize all headers."""
	has_ar_name = any(c.get("fieldname") == "account_name_ar" for c in columns)
	out: list[dict] = []
	for col in columns:
		fieldname = col.get("fieldname")
		if fieldname == "_check":
			continue
		if fieldname == "account_name" and has_ar_name:
			continue
		if fieldname == "account_name_ar":
			col = dict(col)
			col["label"] = "اسم الحساب"
		else:
			col = dict(col)
			col["label"] = arabize_column_label(col.get("label") or fieldname)
		out.append(col)
	return out


def arabize_row(row: dict, *, company: str) -> dict:
	out = dict(row)
	company = company or out.get("company") or ""

	for key in ("section", "component", "expense_type", "item", "statement", "partner", "notes"):
		if out.get(key):
			out[key] = arabize_text(out[key])

	if out.get("line"):
		out["line"] = arabize_text(out["line"])

	if out.get("account_name_ar"):
		out["account_name"] = out["account_name_ar"]
	elif company and out.get("account"):
		out["account_name"] = resolve_account_label(company, out.get("account"))
	elif out.get("account_name"):
		out["account_name"] = arabize_text(out.get("account_name"))

	if out.get("account") and company:
		out["account"] = resolve_account_label(company, out.get("account"))

	for key in ("journal_entry", "reference", "voucher"):
		if out.get(key):
			out[key] = arabize_text(out.get(key))

	return out


def format_cell_ar(
	value: Any,
	fieldtype: str | None,
	row: dict | None,
	fieldname: str | None,
	*,
	company: str,
) -> str:
	row = row or {}
	ft = (fieldtype or "").strip()

	if fieldname in ("account_name", "account_name_ar"):
		val = row.get("account_name_ar") or row.get("account_name")
		if company and row.get("account"):
			val = resolve_account_label(company, row.get("account")) or val
		return arabize_text(val)

	if fieldname == "account" and company:
		return resolve_account_label(company, value)

	if fieldname in ("partner", "component", "section", "expense_type", "item", "notes", "statement", "line"):
		return arabize_text(value)

	if value in (None, ""):
		return "—"
	if ft == "Currency":
		return format_money_ar(value)
	if ft == "Percent":
		return f"{float(value or 0):.2f}٪"
	if ft == "Float":
		return f"{float(value or 0):,.2f}".replace(",", "٬").replace(".", "٫")
	if ft == "Int":
		return str(int(value or 0))
	if ft == "Date":
		return format_date_ar(value)
	if ft == "Datetime":
		return format_date_ar(value)
	return arabize_text(value)
