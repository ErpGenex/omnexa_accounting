# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils import getdate

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company = filters.get("company")
	if not company:
		frappe.throw(_("Company filter is required."), title=_("Filters"))

	conditions = ["je.company = %(company)s", "je.docstatus = 1"]
	if filters.get("from_date"):
		conditions.append("je.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("je.posting_date <= %(to_date)s")
	if filters.get("branch"):
		conditions.append("je.branch = %(branch)s")
	allowed = get_allowed_branches(company=company)
	if allowed is not None:
		if not allowed:
			return columns(), []
		filters.allowed_branches = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	cols = columns()
	data = frappe.db.sql(
		f"""
		SELECT
			je.posting_date,
			je.name AS voucher,
			je.reference,
			je.branch,
			jea.account,
			jea.party_type,
			jea.party,
			jea.debit,
			jea.credit,
			je.remarks
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		WHERE {' AND '.join(conditions)}
		ORDER BY je.posting_date, je.name, jea.idx
		""",
		filters,
		as_dict=True,
	)
	grouped = _group_by_year(data, filters.get("from_date"), filters.get("to_date"))
	chart = auto_chart_for_columns(grouped, cols)
	return cols, grouped, None, chart


def _group_by_year(rows, from_date=None, to_date=None):
	grouped = []
	current_year = None
	year_debit = 0.0
	year_credit = 0.0
	for row in rows:
		year = getdate(row.posting_date).year
		if current_year != year:
			if current_year is not None:
				grouped.append(
					{
						"fiscal_year": str(current_year),
						"voucher": _("Year Total"),
						"debit": year_debit,
						"credit": year_credit,
						"bold": 1,
						"is_total_row": 1,
					}
				)
			current_year = year
			year_debit = 0.0
			year_credit = 0.0
			grouped.append(
				{
					"fiscal_year": str(year),
					"voucher": _("Journal Entries for Fiscal Year {0}").format(year),
					"remarks": _(
						"Official journal from {0} to {1}"
					).format(from_date or "", to_date or ""),
					"bold": 1,
					"year_header": 1,
					"page_break_before": 1 if grouped else 0,
				}
			)
		row["fiscal_year"] = str(year)
		year_debit += float(row.get("debit") or 0)
		year_credit += float(row.get("credit") or 0)
		grouped.append(row)
	if current_year is not None:
		grouped.append(
			{
				"fiscal_year": str(current_year),
				"voucher": _("Year Total"),
				"debit": year_debit,
				"credit": year_credit,
				"bold": 1,
				"is_total_row": 1,
			}
		)
	return grouped


def columns():
	return [
		{"label": _("Year"), "fieldname": "fiscal_year", "fieldtype": "Data", "width": 70},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Voucher"), "fieldname": "voucher", "fieldtype": "Link", "options": "Journal Entry", "width": 130},
		{"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 130},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "GL Account", "width": 170},
		{"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Data", "width": 100},
		{"label": _("Party"), "fieldname": "party", "fieldtype": "Data", "width": 130},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 120},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 120},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 220},
	]
