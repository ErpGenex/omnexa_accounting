# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from omnexa_core.omnexa_core.branch_access import get_allowed_branches
from omnexa_accounting.utils.coa_settings import should_use_consolidation_view
from omnexa_accounting.utils.report_bilingual import (
	gl_account_name_ar_select,
	has_gl_account_name_ar,
	insert_account_name_ar_column,
)
from omnexa_accounting.utils.report_charts import balance_sheet_chart


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	columns = insert_account_name_ar_column(
		[
			{"label": _("Year"), "fieldname": "fiscal_year", "fieldtype": "Data", "width": 70},
			{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 140},
			{"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 180},
			{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 220},
			{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 140},
		]
	)

	consolidation_view = should_use_consolidation_view(filters, filters.company)
	data = []
	chart_assets = chart_liabilities = chart_equity = 0.0
	last_year = None
	for year, year_filters in _iter_year_filters(filters):
		assets = _rows_for_type(year_filters, "Asset", "Assets", consolidation_view=consolidation_view)
		liabilities = _rows_for_type(year_filters, "Liability", "Liabilities", consolidation_view=consolidation_view)
		equity = _rows_for_type(year_filters, "Equity", "Equity", consolidation_view=consolidation_view)
		asset_total = flt(sum(flt((r or {}).get("balance")) for r in assets))
		liability_total = flt(sum(flt((r or {}).get("balance")) for r in liabilities))
		equity_total = flt(sum(flt((r or {}).get("balance")) for r in equity))
		data.append(
			{
				"fiscal_year": str(year),
				"section": _("Balance Sheet"),
				"account_name": _("As at {0}").format(year_filters.to_date),
				"bold": 1,
				"year_header": 1,
				"page_break_before": 1 if data else 0,
			}
		)
		for row in assets + liabilities + equity:
			row["fiscal_year"] = str(year)
			data.append(row)
		data.extend(
			[
				{
					"fiscal_year": str(year),
					"section": _("Assets"),
					"account_name": _("Total Assets"),
					"balance": asset_total,
					"bold": 1,
					"is_total_row": 1,
				},
				{
					"fiscal_year": str(year),
					"section": _("Liabilities"),
					"account_name": _("Total Liabilities"),
					"balance": liability_total,
					"bold": 1,
					"is_total_row": 1,
				},
				{
					"fiscal_year": str(year),
					"section": _("Equity"),
					"account_name": _("Total Equity"),
					"balance": equity_total,
					"bold": 1,
					"is_total_row": 1,
				},
			]
		)
		chart_assets, chart_liabilities, chart_equity = asset_total, liability_total, equity_total
		last_year = year
	chart = balance_sheet_chart(chart_assets, chart_liabilities, chart_equity)
	return columns, data, None, chart


def _iter_year_filters(filters):
	start = getdate(filters.from_date)
	end = getdate(filters.to_date)
	for year in range(start.year, end.year + 1):
		year_end = min(end, getdate(f"{year}-12-31"))
		year_filters = frappe._dict(filters.copy())
		year_filters.to_date = year_end
		yield year, year_filters


def _rows_for_type(filters, account_type, section_label, consolidation_view=False):
	conditions = ["je.company = %(company)s", "je.docstatus = 1", "ga.account_type = %(account_type)s"]
	params = frappe._dict(filters.copy())
	params.account_type = account_type

	if filters.get("to_date"):
		conditions.append("je.posting_date <= %(to_date)s")

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return []
		params.allowed_branches = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	rows = frappe.db.sql(
		f"""
		SELECT
			jea.account,
			ga.account_name,
			ga.consolidation_account_code,
			SUM(jea.debit) AS total_debit,
			SUM(jea.credit) AS total_credit
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {' AND '.join(conditions)}
		GROUP BY jea.account, ga.account_name{", ga.account_name_ar" if has_gl_account_name_ar() else ""}, ga.consolidation_account_code
		ORDER BY ga.account_number, ga.account_name
		""",
		params,
		as_dict=True,
	)

	data = []
	aggregate = {}
	for row in rows:
		if account_type == "Asset":
			balance = flt(row.total_debit) - flt(row.total_credit)
		else:
			balance = flt(row.total_credit) - flt(row.total_debit)
		account_display = row.account
		account_name = row.account_name
		if consolidation_view:
			account_display = (row.consolidation_account_code or row.account or "").strip()
			account_name = _("Consolidated Group")
			aggregate.setdefault(account_display, 0.0)
			aggregate[account_display] += balance
			continue
		data.append(
			{
				"section": _(section_label),
				"account": account_display,
				"account_name": account_name,
				"account_name_ar": row.account_name_ar,
				"balance": balance,
			}
		)
	if consolidation_view:
		data = [
			{
				"section": _(section_label),
				"account": k,
				"account_name": _("Consolidated Group"),
				"balance": v,
			}
			for k, v in sorted(aggregate.items())
		]
	return data
