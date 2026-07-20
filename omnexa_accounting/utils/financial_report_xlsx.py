# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Unified Excel export for core financial Script Reports."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.query_report import generate_report_result, get_report_doc
from frappe.utils.xlsxutils import make_xlsx

SUPPORTED_FINANCIAL_REPORTS = frozenset(
	{
		"Trial Balance",
		"Adjusted Trial Balance",
		"Profit and Loss Statement",
		"Balance Sheet",
		"Statement of Changes in Equity",
		"VAT Position",
		"General Ledger",
		"General Journal",
		"Income Statement",
		"Cash Flow Statement (Indirect)",
		"Cash Flow Statement Structured",
	}
)


def _rows_to_xlsx_matrix(columns: list, rows: list) -> list[list]:
	header = [col.get("label") or col.get("fieldname") or "" for col in columns]
	matrix = [header]
	fieldnames = [col.get("fieldname") for col in columns]
	for row in rows or []:
		if isinstance(row, dict):
			matrix.append([row.get(fn) for fn in fieldnames])
	return matrix


def build_financial_report_xlsx(report_name: str, filters: dict | None = None) -> bytes:
	if report_name not in SUPPORTED_FINANCIAL_REPORTS:
		frappe.throw(_("Report {0} is not enabled for unified Excel export.").format(report_name))
	report = get_report_doc(report_name)
	result = generate_report_result(report, filters=filters or {})
	columns = result.get("columns") or []
	rows = result.get("result") or []
	matrix = _rows_to_xlsx_matrix(columns, rows)
	sheet_title = (report_name or "Report")[:31]
	return make_xlsx(matrix, sheet_title).getvalue()


@frappe.whitelist()
def export_financial_report_xlsx(report_name: str, filters: str | dict | None = None) -> dict:
	"""Generate and attach an XLSX file for a supported financial report."""
	frappe.only_for(("System Manager", "Accounts Manager", "Accounts User"))
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) if filters else {}
	filters = filters or {}
	xlsx_bytes = build_financial_report_xlsx(report_name, filters)
	company = filters.get("company") or "All"
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{report_name.replace(' ', '_')}_{company}.xlsx",
			"is_private": 1,
			"content": xlsx_bytes,
		}
	)
	file_doc.save(ignore_permissions=True)
	return {
		"ok": True,
		"report": report_name,
		"file_url": file_doc.file_url,
		"file_name": file_doc.file_name,
	}
