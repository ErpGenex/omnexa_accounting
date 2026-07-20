# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Period totals from GL: P&L buckets (Revenue, COGS, gross margin), then full Income/Expense net margin."""

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params: dict = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date
	}

	conditions = [
		"je.company = %(company)s",
		"je.docstatus = 1",
		"je.posting_date BETWEEN %(from_date)s AND %(to_date)s",
	]

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _empty_result()
		params["allowed_branches"] = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	if filters.get("branch"):
		conditions.append("je.branch = %(branch)s")
		params["branch"] = filters.branch

	base_where = " AND ".join(conditions)

	def _sum_signed(account_type: str, bucket_clause: str) -> float:
		"""Income: credit − debit. Expense: debit − credit."""
		p = frappe._dict(params)
		p.account_type = account_type
		rows = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(jea.debit), 0) AS td, COALESCE(SUM(jea.credit), 0) AS tc
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			INNER JOIN `tabGL Account` ga ON ga.name = jea.account
			WHERE {base_where}
			  AND ga.account_type = %(account_type)s
			  AND ({bucket_clause})
			""",
			p,
			as_dict=True,
		)
		if not rows:
			return 0.0
		r = rows[0]
		if account_type == "Income":
			return flt(r.tc) - flt(r.td)
		return flt(r.td) - flt(r.tc)

	revenue_pl = _sum_signed(
		"Income",
		"IFNULL(ga.pl_bucket, '') IN ('', 'Revenue')",
	)
	other_income = _sum_signed("Income", "ga.pl_bucket = 'Other Income'")
	cogs = _sum_signed("Expense", "ga.pl_bucket = 'COGS'")
	operating_exp = _sum_signed(
		"Expense",
		"IFNULL(ga.pl_bucket, '') IN ('', 'Operating Expense')",
	)
	other_expense = _sum_signed("Expense", "ga.pl_bucket = 'Other Expense'")

	total_income = _sum_signed("Income", "1=1")
	total_expense = _sum_signed("Expense", "1=1")

	gross_profit = flt(revenue_pl - cogs)
	gross_margin_pct = flt((gross_profit / revenue_pl) * 100.0, 2) if revenue_pl else None

	net = flt(total_income - total_expense)
	net_margin_pct = flt((net / total_income) * 100.0, 2) if total_income else None

	columns = [
		{"label": _("Metric"), "fieldname": "metric", "fieldtype": "Data", "width": 300
	},
		{"label": _("Value"), "fieldname": "value", "fieldtype": "Float", "width": 160
	},
	]

	data = [
		{"metric": _("Revenue (P&L bucket)"), "value": flt(revenue_pl, 2)},
		{"metric": _("Other income"), "value": flt(other_income, 2)},
		{"metric": _("COGS (tagged accounts)"), "value": flt(cogs, 2)},
		{"metric": _("Gross profit (Revenue − COGS)"), "value": flt(gross_profit, 2)},
		{
			"metric": _("Gross margin % (÷ Revenue bucket)"),
			"value": flt(gross_margin_pct, 2) if gross_margin_pct is not None else None},
		{"metric": _("Operating expense (bucket)"), "value": flt(operating_exp, 2)},
		{"metric": _("Other expense (bucket)"), "value": flt(other_expense, 2)},
		{"metric": _("Total income (all GL Income)"), "value": flt(total_income, 2)},
		{"metric": _("Total expense (all GL Expense)"), "value": flt(total_expense, 2)},
		{"metric": _("Net (Income − Expense)"), "value": flt(net, 2)},
		{
			"metric": _("Net margin % (÷ total income)"),
			"value": flt(net_margin_pct, 2) if net_margin_pct is not None else None},
	]

	report_summary = [
		{"value": revenue_pl, "label": _("Revenue (bucket)"), "datatype": "Currency"
	},
		{"value": cogs, "label": _("COGS"), "datatype": "Currency"
	},
		{"value": gross_profit, "label": _("Gross profit"), "datatype": "Currency"
	},
		{
			"value": gross_margin_pct if gross_margin_pct is not None else 0.0,
			"label": _("Gross margin %"),
			"datatype": "Float"
	},
		{"value": net, "label": _("Net"), "datatype": "Currency"
	},
		{
			"value": net_margin_pct if net_margin_pct is not None else 0.0,
			"label": _("Net margin %"),
			"datatype": "Float"
	},
	]

	message = _(
		"Tag GL accounts with P&L Bucket: COGS on cost accounts; Revenue vs Other Income; "
		"Operating vs Other Expense. Empty bucket on Income counts as Revenue; empty on Expense as Operating Expense."
	)

	return columns, data, message, None, report_summary, True


def _empty_result():
	columns = [
		{"label": _("Metric"), "fieldname": "metric", "fieldtype": "Data", "width": 300
	},
		{"label": _("Value"), "fieldname": "value", "fieldtype": "Float", "width": 160
	},
	]
	return columns, [], None, None, [], True
