# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Apply enhanced financial print HTML to core accounting reports."""

FINANCIAL_REPORTS = (
	"Trial Balance",
	"Balance Sheet",
	"Income Statement",
	"General Ledger",
	"General Journal",
	"Cash Flow (Simplified)",
	"Cash Flow Statement Structured",
	"Cash Flow Statement Indirect",
	"Receivables Aging",
	"Payables Aging",
	"Customer Ledger",
	"Supplier Ledger",
	"Financial KPI Summary",
	"Consolidated Trial Balance",
)


def execute():
	from pathlib import Path

	import frappe

	app_path = Path(frappe.get_app_path("omnexa_accounting"))
	template = (app_path / "templates" / "erpgenex_financial_report_print.html").read_text(encoding="utf-8")
	base = app_path / "omnexa_accounting" / "report"
	written = 0
	for name in FINANCIAL_REPORTS:
		slug = frappe.scrub(name)
		folder = base / slug
		if not folder.is_dir():
			continue
		html_path = folder / f"{slug}.html"
		if html_path.exists() and "omn-fin-report-hero" in html_path.read_text(encoding="utf-8"):
			continue
		html_path.write_text(template, encoding="utf-8")
		written += 1
	return {"written": written}
