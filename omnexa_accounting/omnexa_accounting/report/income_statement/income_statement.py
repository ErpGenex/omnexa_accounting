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


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	columns = insert_account_name_ar_column(
		[
			{"label": _("Year"), "fieldname": "fiscal_year", "fieldtype": "Data", "width": 70
	},
			{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 140
	},
			{"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 180
	},
			{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 220
	},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140
	},
		]
	)

	consolidation_view = should_use_consolidation_view(filters, filters.company)
	data = []
	chart_labels = []
	chart_values = []
	for year, year_filters in _iter_year_filters(filters):
		income_rows = _rows_for_type(year_filters, "Revenue", "Revenue", consolidation_view=consolidation_view)
		expense_rows = _rows_for_type(year_filters, "Expense", "Expense", consolidation_view=consolidation_view)
		revenue_total = flt(sum(flt((r or {}).get("amount")) for r in income_rows))
		expense_total = flt(sum(flt((r or {}).get("amount")) for r in expense_rows))
		net_profit = revenue_total - expense_total
		data.append(
			{
				"fiscal_year": str(year),
				"section": _("Income Statement"),
				"account_name": _("Fiscal Year {0}").format(year),
				"bold": 1,
				"year_header": 1,
				"page_break_before": 1 if data else 0
	}
		)
		for row in income_rows + expense_rows:
			row["fiscal_year"] = str(year)
			data.append(row)
		data.append(
			{
				"fiscal_year": str(year),
				"section": _("Net Result"),
				"account_name": _("Net Profit / Loss"),
				"amount": net_profit,
				"bold": 1,
				"is_total_row": 1
	}
		)
		chart_labels.append(str(year))
		chart_values.append(net_profit)

	chart = {
		"data": {
			"labels": chart_labels,
			"datasets": [{"name": _("Net Result"), "values": chart_values}]
	},
		"type": "bar",
		"title": _("Income Statement by Year"),
		"height": 260
	}
	return columns, data, None, chart


def _iter_year_filters(filters):
	start = getdate(filters.from_date)
	end = getdate(filters.to_date)
	for year in range(start.year, end.year + 1):
		year_start = max(start, getdate(f"{year}-01-01"))
		year_end = min(end, getdate(f"{year}-12-31"))
		year_filters = frappe._dict(filters.copy())
		year_filters.from_date = year_start
		year_filters.to_date = year_end
		yield year, year_filters


def _rows_for_type(filters, account_type, section_label, consolidation_view=False):
	conditions = [
		"je.company = %(company)s",
		"je.docstatus = 1",
		"je.posting_date between %(from_date)s and %(to_date)s",
	]
	params = frappe._dict(filters.copy())
	params.account_type = account_type
	if account_type == "Revenue":
		conditions.append("(ga.account_type = 'Revenue' OR ga.account_type = 'Income')")
	else:
		conditions.append("ga.account_type = %(account_type)s")

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
			{gl_account_name_ar_select()} AS account_name_ar,
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
		amount = flt(row.total_credit) - flt(row.total_debit) if account_type == "Revenue" else flt(row.total_debit) - flt(row.total_credit)
		account_display = row.account
		account_name = row.account_name
		if consolidation_view:
			account_display = (row.consolidation_account_code or row.account or "").strip()
			account_name = _("Consolidated Group")
			aggregate.setdefault(account_display, 0.0)
			aggregate[account_display] += amount
			continue
		data.append(
			{
				"section": _(section_label),
				"account": account_display,
				"account_name": account_name,
				"account_name_ar": row.account_name_ar,
				"amount": amount
	}
		)
	if consolidation_view:
		data = [
			{"section": _(section_label), "account": k, "account_name": _("Consolidated Group"), "amount": v
	}
			for k, v in sorted(aggregate.items())
		]
	return data
