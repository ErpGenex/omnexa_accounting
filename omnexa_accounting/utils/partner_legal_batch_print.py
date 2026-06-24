# Copyright (c) 2026, Omnexa and contributors
# License: MIT

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.desk.query_report import generate_report_result, get_report_doc
from frappe.utils.pdf import get_file_data_from_writer, get_pdf
from pypdf import PdfWriter

from omnexa_accounting.omnexa_accounting.doctype.company_partner_legal_setup.company_partner_legal_setup import (
	get_funding_partner,
	get_primary_liable_partner,
)
from omnexa_accounting.utils.partner_legal_arabic import (
	arabize_row,
	arabize_text,
	format_cell_ar,
	format_date_ar,
	format_money_ar,
	get_branch_name_ar,
	get_company_name_ar,
	get_user_display_ar,
	prepare_columns_for_arabic,
)
from omnexa_accounting.utils.partner_legal_reporting import generate_court_evidence_package

# ── أسماء المستندات القانونية بالعربية ─────────────────────────────────────
LEGAL_DOC_SECTIONS: list[dict[str, Any]] = [
	{"kind": "final_summary", "doc_no": 1, "title_ar": "التقرير النهائي عن المدة — ملخص مديونيات الشركاء"},
	{"kind": "report", "doc_no": 2, "report": "Balance Sheet", "title_ar": "الميزانية العمومية لكل سنة"},
	{"kind": "report", "doc_no": 3, "report": "Income Statement", "title_ar": "قائمة الدخل لكل سنة"},
	{
		"kind": "report",
		"doc_no": 4,
		"report": "Partner Debt Statement",
		"title_ar": "كشف مديونية الشريك — تفصيل سنوي",
		"debt_pct_fraction": True,
	},
	{"kind": "report", "doc_no": 5, "report": "Partner Contribution Report", "title_ar": "تقرير مساهمة الشركاء في التمويل"},
	{"kind": "report", "doc_no": 6, "report": "Partner Loss Allocation Report", "title_ar": "تقرير توزيع الخسائر على الشركاء"},
	{"kind": "report", "doc_no": 7, "report": "Partner Recovery Report", "title_ar": "تقرير استرداد مساهمات الشريك"},
	{"kind": "report", "doc_no": 8, "report": "Legal Claim Statement", "title_ar": "بيان المطالبة القانونية — إثبات المديونية"},
	{
		"kind": "report",
		"doc_no": 9,
		"report": "Liquidation Historical Report",
		"title_ar": "تقرير التصفية التاريخي",
		"as_of_only": True,
	},
]

AR_META = {
	"company": "الشركة",
	"period": "الفترة",
	"from": "من",
	"to": "إلى",
	"branch": "الفرع",
	"all_branches": "جميع الفروع",
	"legal_case": "مرجع القضية",
	"doc_no": "رقم المستند",
	"generated_by": "أُعد بواسطة",
	"printed_at": "تاريخ الطباعة",
	"no_data": "لا توجد بيانات",
	"serial": "م",
}


def _format_datetime_ar() -> str:
	dt = frappe.utils.get_datetime(frappe.utils.now_datetime())
	return f"{format_date_ar(dt.date())} — {dt.hour:02d}:{dt.minute:02d}"


def _arabic_notes(text: str | None) -> str:
	if not text:
		return ""
	return arabize_text(text)


def _read_financial_print_css() -> str:
	path = frappe.get_app_path("omnexa_accounting", "public", "css", "financial_reports.css")
	try:
		with open(path, encoding="utf-8") as handle:
			return handle.read()
	except OSError:
		return ""


def build_report_filters_from_setup(setup, from_date: str, to_date: str) -> dict[str, Any]:
	funder = get_funding_partner(setup)
	liable = get_primary_liable_partner(setup)
	if not funder or not liable:
		frappe.throw(_("Partner legal setup must include one funding partner and one liable partner."))

	liable_pct = float(liable.ownership_percent or 0)
	primary_pct = max(0.0, 100.0 - liable_pct)

	return {
		"company": setup.company,
		"branch": setup.branch,
		"from_date": from_date,
		"to_date": to_date,
		"as_of_date": to_date,
		"primary_partner_name": funder.partner_name,
		"secondary_partner_name": liable.partner_name,
		"primary_pct": primary_pct,
		"secondary_pct": liable_pct,
		"primary_current_account": funder.partner_current_account,
		"secondary_current_account": liable.partner_current_account,
		"secondary_due_account": liable.due_from_partner_account,
		"legal_case_reference": setup.legal_case_reference,
	}


def _report_filters(base: dict, spec: dict) -> dict:
	filters = dict(base)
	if spec.get("debt_pct_fraction"):
		filters["secondary_pct"] = float(base.get("secondary_pct") or 0) / 100.0
	if spec.get("as_of_only"):
		filters.pop("from_date", None)
		filters.pop("to_date", None)
	return filters


def _html_shell(*, css: str, body: str, landscape: bool = True) -> str:
	orientation = "landscape" if landscape else "portrait"
	return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<style>
{css}
@page {{ size: A4 {orientation}; margin: 12mm; }}
body {{ margin: 0; padding: 16px; font-family: "Cairo", "Noto Sans Arabic", Arial, sans-serif; }}
.legal-doc-header {{ background: #0f3d75; color: #fff; padding: 14px 18px; border-radius: 8px; margin-bottom: 12px; }}
.legal-doc-header h1 {{ margin: 0; font-size: 1.2rem; }}
.legal-doc-header h2 {{ margin: 4px 0 0; font-size: 0.9rem; font-weight: normal; opacity: 0.92; }}
.legal-doc-no {{ font-size: 0.8rem; opacity: 0.85; margin-top: 6px; }}
.legal-summary p {{ line-height: 1.7; font-size: 0.9rem; }}
.legal-summary table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
.legal-summary th, .legal-summary td {{ border: 1px solid #d1d8dd; padding: 6px 8px; font-size: 0.85rem; }}
.legal-summary th {{ background: #0f3d75; color: #fff; }}
.year-header td {{ background: #dbeafe !important; font-weight: 700; }}
.total-row td {{ font-weight: 700; background: #eff6ff !important; }}
</style>
</head>
<body>{body}</body>
</html>"""


def _doc_banner(*, doc_no: int | None, title_ar: str, subtitle_ar: str = "") -> str:
	doc_line = f'<div class="legal-doc-no">{AR_META["doc_no"]}: {doc_no}</div>' if doc_no else ""
	sub = f"<h2>{subtitle_ar}</h2>" if subtitle_ar else ""
	return f"""
<div class="legal-doc-header">
	<h1>{frappe.as_unicode(title_ar)}</h1>
	{sub}
	{doc_line}
</div>"""


def _meta_grid(filters: dict, company: str) -> str:
	period_from = format_date_ar(filters.get("from_date")) if filters.get("from_date") else "—"
	period_to = format_date_ar(filters.get("to_date") or filters.get("as_of_date")) if (
		filters.get("to_date") or filters.get("as_of_date")
	) else "—"
	items = [
		(AR_META["company"], get_company_name_ar(company)),
		(AR_META["period"], f'{AR_META["from"]}: {period_from} — {AR_META["to"]}: {period_to}'),
		(AR_META["branch"], get_branch_name_ar(filters.get("branch"))),
	]
	if filters.get("legal_case_reference"):
		items.append((AR_META["legal_case"], arabize_text(filters["legal_case_reference"]))
	)
	return "".join(
		f'<div class="erpg-fin-print__meta-box"><div class="erpg-fin-print__meta-label">{k}</div>'
		f'<div class="erpg-fin-print__meta-value">{frappe.as_unicode(v)}</div></div>'
		for k, v in items
	)


def _render_report_section_html(
	*,
	doc_no: int,
	title_ar: str,
	filters: dict,
	columns: list[dict],
	rows: list[dict],
) -> str:
	css = _read_financial_print_css()
	company = filters.get("company") or ""
	visible_columns = prepare_columns_for_arabic(
		[c for c in columns if c.get("fieldname") and c.get("fieldname") != "_check"]
	)

	head = "".join(f"<th>{frappe.as_unicode(col.get('label'))}</th>" for col in visible_columns)
	fieldnames = [c.get("fieldname") for c in visible_columns]
	body_rows = []
	row_num = 0
	for raw in rows or []:
		if isinstance(raw, (list, tuple)):
			raw = {fieldnames[i]: raw[i] if i < len(raw) else None for i in range(len(fieldnames))}
		if not isinstance(raw, dict):
			continue
		row = arabize_row(raw, company=company)
		row_class = ""
		if row.get("year_header"):
			row_class = "year-header"
		elif row.get("is_total_row") or row.get("bold"):
			row_class = "total-row"
		cells = "".join(
			f"<td>{format_cell_ar(row.get(col.get('fieldname')), col.get('fieldtype'), row, col.get('fieldname'), company=company)}</td>"
			for col in visible_columns
		)
		serial = "" if row.get("year_header") else str(row_num + 1)
		if not row.get("year_header"):
			row_num += 1
		body_rows.append(f'<tr class="{row_class}"><td>{serial}</td>{cells}</tr>')

	table_html = f"""
	<table class="table table-bordered erpg-fin-print__table">
		<thead><tr><th>{AR_META["serial"]}</th>{head}</tr></thead>
		<tbody>{''.join(body_rows) if body_rows else '<tr><td colspan="99">' + AR_META["no_data"] + "</td></tr>"}</tbody>
	</table>
	"""

	body = f"""
<div class="erpg-fin-print">
	{_doc_banner(doc_no=doc_no, title_ar=title_ar, subtitle_ar="مستند قانوني — محاسبة الشركاء")}
	<div class="erpg-fin-print__meta-grid">{_meta_grid(filters, filters.get("company"))}</div>
	{table_html}
	<div class="erpg-fin-print__footer-meta" style="margin-top:12px;font-size:9px;">
		{AR_META["generated_by"]}: {get_user_display_ar()} | {AR_META["printed_at"]}: {_format_datetime_ar()}
	</div>
</div>"""
	return _html_shell(css=css, body=body)


def _render_cover_html(*, setup, filters: dict, package: dict) -> str:
	css = _read_financial_print_css()
	cert = package.get("certificate") or {}
	company_label = get_company_name_ar(setup.company)

	partners_html = "".join(
		f"<li><b>{frappe.as_unicode(p.partner_name_ar or p.partner_name)}</b>"
		f" — نسبة الملكية: {float(p.ownership_percent or 0):.2f}٪"
		f"{' — <u>الشريك الممول</u>' if p.is_funding_partner else ''}</li>"
		for p in setup.partners or []
	)
	docs_html = "".join(
		f"<li>المستند {spec['doc_no']}: {frappe.as_unicode(spec['title_ar'])}</li>" for spec in LEGAL_DOC_SECTIONS
	)
	period_from = format_date_ar(filters.get("from_date"))
	period_to = format_date_ar(filters.get("to_date"))

	body = f"""
<div class="erpg-fin-print">
	<div class="legal-doc-header">
		<h1>حزمة المستندات القانونية للشركاء</h1>
		<h2>طباعة موحّدة لجميع التقارير المحاسبية والقانونية</h2>
	</div>
	<div class="erpg-fin-print__meta-grid">
		<div class="erpg-fin-print__meta-box"><div class="erpg-fin-print__meta-label">{AR_META['company']}</div>
		<div class="erpg-fin-print__meta-value">{company_label}</div></div>
		<div class="erpg-fin-print__meta-box"><div class="erpg-fin-print__meta-label">{AR_META['period']}</div>
		<div class="erpg-fin-print__meta-value">{period_from} — {period_to}</div></div>
		<div class="erpg-fin-print__meta-box"><div class="erpg-fin-print__meta-label">الشريك المدين</div>
		<div class="erpg-fin-print__meta-value">{arabize_text(cert.get('debtor_partner'))}</div></div>
		<div class="erpg-fin-print__meta-box"><div class="erpg-fin-print__meta-label">إجمالي المديونية المستحقة</div>
		<div class="erpg-fin-print__meta-value">{format_money_ar(cert.get('final_amount_due'))}</div></div>
	</div>
	<h4>الشركاء</h4><ul>{partners_html}</ul>
	<h4>قائمة المستندات المرفقة ({len(LEGAL_DOC_SECTIONS)} مستندات)</h4><ul>{docs_html}</ul>
	<p style="font-size:0.85rem;color:#444;">{_arabic_notes(setup.notes)}</p>
</div>"""
	return _html_shell(css=css, body=body, landscape=False)


def _render_final_period_summary_html(
	*, setup, filters: dict, package: dict, doc_no: int
) -> str:
	css = _read_financial_print_css()
	cert = package.get("certificate") or {}
	funder = get_funding_partner(setup)
	liable = get_primary_liable_partner(setup)
	company_label = get_company_name_ar(setup.company)
	liable_pct = float(liable.ownership_percent or 0) if liable else 0
	funder_name = (funder.partner_name_ar or funder.partner_name) if funder else "—"
	liable_name = (liable.partner_name_ar or liable.partner_name) if liable else "—"

	debt_rows = package.get("partner_debt_statement") or []
	loss_rows = package.get("partner_loss_allocation") or []
	total_expenses = sum(float(r.get("total_expenses") or 0) for r in debt_rows)
	total_share = sum(float(r.get("secondary_share") or 0) for r in debt_rows)
	total_paid = sum(float(r.get("secondary_paid") or 0) for r in debt_rows)
	final_debt = float(cert.get("final_amount_due") or 0)
	period_from = format_date_ar(filters.get("from_date"))
	period_to = format_date_ar(filters.get("to_date"))

	debt_table = "".join(
		f"<tr><td>{r.get('year')}</td>"
		f"<td>{format_money_ar(r.get('total_expenses'))}</td>"
		f"<td>{format_money_ar(r.get('secondary_share'))}</td>"
		f"<td>{format_money_ar(r.get('secondary_paid'))}</td>"
		f"<td>{format_money_ar(r.get('debt_year'))}</td>"
		f"<td>{format_money_ar(r.get('cumulative_debt'))}</td></tr>"
		for r in debt_rows
	)

	loss_table = "".join(
		f"<tr><td>{r.get('year')}</td>"
		f"<td>{format_money_ar(r.get('net_result'))}</td>"
		f"<td>{format_money_ar(r.get('secondary_share'))}</td>"
		f"<td>{format_money_ar(r.get('cumulative_loss_share'))}</td></tr>"
		for r in loss_rows
	)

	narrative = f"""
<p>
	نحن الموقّعون أدناه، نُصدر هذا <b>التقرير النهائي عن المدة</b> للفترة من
	<b>{period_from}</b> إلى <b>{period_to}</b>
	بخصوص شركة <b>{company_label}</b>.
</p>
<p>
	يُقرّ التقرير بأن الشريك الممول <b>{funder_name}</b> قام بتمويل مصروفات الشركة التشغيلية
	عبر حساب الجاري، وأن الشريك <b>{liable_name}</b> يتحمل نسبة ملكية قدرها
	<b>{liable_pct:.2f}٪</b> من النتائج والتزامات التمويل وفق القيود المحاسبية المُعتمدة.
</p>
<p>
	<b>ملخص المديونية:</b> إجمالي المصروفات الممولة خلال الفترة
	<b>{format_money_ar(total_expenses)}</b>، وحصة الشريك المدين
	<b>{format_money_ar(total_share)}</b>، والمبالغ المسددة
	<b>{format_money_ar(total_paid)}</b>، والمديونية المتراكمة المستحقة حتى نهاية الفترة
	<b>{format_money_ar(final_debt)}</b>.
</p>
"""

	conclusion = f"""
<p>
	<b>الخلاصة القانونية:</b> بناءً على الميزانية العمومية وقائمة الدخل لكل سنة،
	وكشوف مديونية الشركاء وتوزيع الخسائر وبيان المطالبة القانونية المرفقة،
	تُثبت المديونية المستحقة على الشريك <b>{liable_name}</b>
	بمبلغ <b>{format_money_ar(final_debt)}</b> حتى تاريخ
	<b>{period_to}</b>.
</p>
<p style="margin-top:24px;">
	<table style="width:100%;border:none;"><tr>
	<td style="width:33%;border:none;">مُعد التقرير: _______________</td>
	<td style="width:33%;border:none;text-align:center;">مراجع: _______________</td>
	<td style="width:33%;border:none;text-align:left;">يعتمد: _______________</td>
	</tr></table>
</p>
"""

	body = f"""
<div class="erpg-fin-print legal-summary">
	{_doc_banner(doc_no=doc_no, title_ar="التقرير النهائي عن المدة", subtitle_ar="ملخص مديونيات الشركاء والالتزامات المالية")}
	<div class="erpg-fin-print__meta-grid">{_meta_grid(filters, setup.company)}</div>
	{narrative}
	<h4>جدول (١) — تفصيل المديونية السنوية للشريك المدين</h4>
	<table>
		<thead><tr>
			<th>السنة</th><th>إجمالي المصروفات</th><th>حصة الشريك ({liable_pct:.0f}%)</th>
			<th>المسدد</th><th>مديونية السنة</th><th>المديونية المتراكمة</th>
		</tr></thead>
		<tbody>{debt_table or f'<tr><td colspan="6">{AR_META["no_data"]}</td></tr>'}</tbody>
	</table>
	<h4>جدول (٢) — توزيع النتائج والخسائر السنوية</h4>
	<table>
		<thead><tr>
			<th>السنة</th><th>صافي النتيجة</th><th>حصة الشريك المدين</th><th>خسائر متراكمة</th>
		</tr></thead>
		<tbody>{loss_table or f'<tr><td colspan="4">{AR_META["no_data"]}</td></tr>'}</tbody>
	</table>
	{conclusion}
</div>"""
	return _html_shell(css=css, body=body, landscape=False)


def _normalize_rows(rows: list, columns: list[dict]) -> list[dict]:
	if not rows:
		return []
	if isinstance(rows[0], dict):
		return rows
	names = [c.get("fieldname") for c in columns]
	out: list[dict] = []
	for row in rows:
		if isinstance(row, dict):
			out.append(row)
		elif isinstance(row, (list, tuple)):
			out.append({names[i]: row[i] if i < len(row) else None for i in range(len(names))})
	return out


def _run_report(report_name: str, filters: dict) -> tuple[list[dict], list[dict]]:
	report = get_report_doc(report_name)
	result = generate_report_result(report, filters=filters)
	columns = result.get("columns") or []
	rows = _normalize_rows(result.get("result") or [], columns)
	return columns, rows


def _iter_package_sections(setup, filters: dict, package: dict) -> list[tuple[dict, str, bool]]:
	"""Return (spec, html, landscape) for each section."""
	sections: list[tuple[dict, str, bool]] = []
	for spec in LEGAL_DOC_SECTIONS:
		if spec.get("kind") == "final_summary":
			sections.append(
				(
					spec,
					_render_final_period_summary_html(
						setup=setup, filters=filters, package=package, doc_no=spec["doc_no"]
					),
					False,
				)
			)
			continue

		report_filters = _report_filters(filters, spec)
		columns, rows = _run_report(spec["report"], report_filters)
		sections.append(
			(
				spec,
				_render_report_section_html(
					doc_no=spec["doc_no"],
					title_ar=spec["title_ar"],
					filters=report_filters,
					columns=columns,
					rows=rows,
				),
				True,
			)
		)
	return sections


def build_merged_partner_legal_pdf(company: str, from_date: str, to_date: str, branch: str | None = None) -> bytes:
	if not frappe.db.exists("Company Partner Legal Setup", company):
		frappe.throw(
			_("Create a Company Partner Legal Setup for {0} first.").format(company),
			title=_("Setup Required"),
		)

	setup = frappe.get_doc("Company Partner Legal Setup", company)
	if branch:
		setup.branch = branch
	filters = build_report_filters_from_setup(setup, from_date, to_date)

	package_filters = dict(filters)
	package_filters["secondary_pct"] = float(filters.get("secondary_pct") or 0) / 100.0
	package = generate_court_evidence_package(**package_filters)

	writer = PdfWriter()
	landscape_opts = {"orientation": "Landscape", "page-size": "A4"}
	portrait_opts = {"orientation": "Portrait", "page-size": "A4"}

	get_pdf(_render_cover_html(setup=setup, filters=filters, package=package), portrait_opts, output=writer)

	for spec, html, landscape in _iter_package_sections(setup, filters, package):
		get_pdf(html, landscape_opts if landscape else portrait_opts, output=writer)

	return get_file_data_from_writer(writer)


def _preview_section(spec: dict, filters: dict) -> dict:
	if spec.get("kind") == "final_summary":
		return {
			"doc_no": spec["doc_no"],
			"title_ar": spec["title_ar"],
			"kind": "final_summary",
			"ok": True,
		}
	report_filters = _report_filters(filters, spec)
	try:
		_, rows = _run_report(spec["report"], report_filters)
		return {
			"doc_no": spec["doc_no"],
			"title_ar": spec["title_ar"],
			"row_count": len(rows or []),
			"ok": True,
		}
	except Exception as exc:
		return {
			"doc_no": spec["doc_no"],
			"title_ar": spec["title_ar"],
			"ok": False,
			"error": arabize_text(str(exc)),
		}


@frappe.whitelist()
def get_partner_legal_print_preview(company: str, from_date: str, to_date: str, branch: str | None = None) -> dict:
	if not frappe.db.exists("Company Partner Legal Setup", company):
		return {"ok": False, "error": "لم يتم العثور على إعداد قانوني للشركاء لهذه الشركة."}

	setup = frappe.get_doc("Company Partner Legal Setup", company)
	if branch:
		setup.branch = branch
	filters = build_report_filters_from_setup(setup, from_date, to_date)
	package_filters = dict(filters)
	package_filters["secondary_pct"] = float(filters.get("secondary_pct") or 0) / 100.0
	package = generate_court_evidence_package(**package_filters)

	reports = [_preview_section(spec, filters) for spec in LEGAL_DOC_SECTIONS]

	return {
		"ok": True,
		"company": company,
		"company_display": get_company_name_ar(company),
		"from_date": from_date,
		"to_date": to_date,
		"branch": branch or setup.branch,
		"partners": [
			{
				"partner_name": row.partner_name,
				"partner_name_ar": row.partner_name_ar,
				"ownership_percent": float(row.ownership_percent or 0),
				"is_funding_partner": row.is_funding_partner,
			}
			for row in setup.partners or []
		],
		"certificate": package.get("certificate"),
		"reports": reports,
		"document_count": len(LEGAL_DOC_SECTIONS) + 1,
		"setup_url": f"/app/company-partner-legal-setup/{company}",
	}


@frappe.whitelist()
def download_partner_legal_package(company: str, from_date: str, to_date: str, branch: str | None = None):
	frappe.has_permission("Company Partner Legal Setup", "read", throw=True)
	pdf_bytes = build_merged_partner_legal_pdf(company, from_date, to_date, branch=branch)
	safe_company = company.replace(" ", "-")
	frappe.local.response.filename = f"حزمة-المستندات-القانونية-{safe_company}-{from_date}-{to_date}.pdf"
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "pdf"


def smoke_test_partner_legal_pdf(company: str, from_date: str, to_date: str) -> dict:
	pdf_bytes = build_merged_partner_legal_pdf(company, from_date, to_date)
	return {"ok": True, "bytes": len(pdf_bytes), "documents": len(LEGAL_DOC_SECTIONS) + 1}
