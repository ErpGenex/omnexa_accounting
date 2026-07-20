# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Submitted Budget vs Journal Entry actuals (Income/Expense), optional Cost Center and For Month per line."""

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt, getdate

from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	budget_name = filters.get("budget")
	if not budget_name:
		frappe.throw(_("Budget is required."), title=_("Filters"))

	bdoc = frappe.get_doc("Budget", budget_name)
	if bdoc.docstatus != 1:
		frappe.throw(_("Select a submitted Budget."), title=_("Budget"))

	company = bdoc.company
	from_date, to_date = bdoc.from_date, bdoc.to_date
	if not bdoc.budget_lines:
		return _cols(), [], _("No lines on this budget."), None, None, False

	types = {}
	names = {}
	for row in bdoc.budget_lines:
		if not row.gl_account:
			continue
		types[row.gl_account] = frappe.db.get_value("GL Account", row.gl_account, "account_type")
		names[row.gl_account] = frappe.db.get_value("GL Account", row.gl_account, "account_name")

	data = []
	for row in bdoc.budget_lines:
		if not row.gl_account:
			continue
		actual = _line_actual(
			company=company,
			from_date=from_date,
			to_date=to_date,
			gl_account=row.gl_account,
			line_cost_center=(row.cost_center or "").strip() or None,
			period_month=row.period_month,
			report_branch=filters.get("branch"),
			report_cost_center_filter=(filters.get("cost_center") or "").strip() or None,
		)
		at = types.get(row.gl_account) or ""
		budget_amt = flt(row.budget_amount)
		variance = flt(budget_amt - actual)
		data.append(
			{
				"gl_account": row.gl_account,
				"account_name": names.get(row.gl_account) or "",
				"account_type": at,
				"line_cost_center": row.cost_center or "",
				"period_month": row.period_month or None,
				"budget_amount": budget_amt,
				"actual_amount": actual,
				"variance": variance,
			}
		)

	msg = _(
		"Expense: actual = debit − credit. Income: actual = credit − debit. "
		"If **For Month** is set on a line, only Journal Entries in that calendar month are included. "
		"If a line **Cost Center** is set, Journal Entry Account lines must match (string match). "
		"Optional report filter **Cost Center** further restricts lines to that center."
	)
	columns = _cols()
	chart = auto_chart_for_columns(data, columns)
	return columns, data, msg, chart, None, False
def _line_actual(
	*,
	company: str,
	from_date,
	to_date,
	gl_account: str,
	line_cost_center: str | None,
	period_month,
	report_branch,
	report_cost_center_filter: str | None,
) -> float:
	params = {
		"company": company,
		"from_date": from_date,
		"to_date": to_date,
		"account": gl_account,
	}
	conditions = [
		"je.company = %(company)s",
		"je.docstatus = 1",
		"je.posting_date BETWEEN %(from_date)s AND %(to_date)s",
		"jea.account = %(account)s",
	]

	if period_month:
		pm = getdate(period_month)
		params["pm_y"] = pm.year
		params["pm_m"] = pm.month
		conditions.append("YEAR(je.posting_date) = %(pm_y)s AND MONTH(je.posting_date) = %(pm_m)s")

	if line_cost_center:
		params["lcc"] = line_cost_center
		conditions.append("IFNULL(jea.cost_center, '') = %(lcc)s")
	elif report_cost_center_filter:
		params["rcc"] = report_cost_center_filter
		conditions.append("IFNULL(jea.cost_center, '') = %(rcc)s")

	allowed = get_allowed_branches(company=company)
	if allowed is not None:
		if not allowed:
			return 0.0
		params["allowed_branches"] = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	if report_branch:
		params["branch"] = report_branch
		conditions.append("je.branch = %(branch)s")

	where_sql = " AND ".join(conditions)
	row = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(jea.debit), 0) AS debit, COALESCE(SUM(jea.credit), 0) AS credit
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		WHERE {where_sql}
		""",
		params,
		as_dict=True,
	)
	r = row[0] if row else {}
	dr, cr = flt(r.get("debit")), flt(r.get("credit"))
	at = frappe.db.get_value("GL Account", gl_account, "account_type")
	if at == "Expense":
		return flt(dr - cr)
	if at == "Income":
		return flt(cr - dr)
	return flt(dr - cr)


def _cols():
	return [
		{"label": _("GL Account"), "fieldname": "gl_account", "fieldtype": "Link", "options": "GL Account", "width": 150},
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 180},
		{"label": _("Type"), "fieldname": "account_type", "fieldtype": "Data", "width": 90},
		{"label": _("Line Cost Center"), "fieldname": "line_cost_center", "fieldtype": "Data", "width": 120},
		{"label": _("For Month"), "fieldname": "period_month", "fieldtype": "Date", "width": 100},
		{"label": _("Budget"), "fieldname": "budget_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Actual"), "fieldname": "actual_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Currency", "width": 110},
	]
