# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""IFRS 7-style indirect operating section (MVP): net income from P&L + working capital from GL buckets."""

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {"company": filters.company, "fd": filters.from_date, "td": filters.to_date}
	conditions = ["je.company = %(company)s", "je.docstatus = 1"]

	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return _empty()
		params["allowed_branches"] = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	if filters.get("branch"):
		params["branch"] = filters.branch
		conditions.append("je.branch = %(branch)s")

	where_sql = " AND ".join(conditions)

	net_income = flt(
		frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(
				CASE ga.account_type
					WHEN 'Income' THEN jea.credit - jea.debit
					WHEN 'Expense' THEN jea.debit - jea.credit
					ELSE 0
				END
			), 0)
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			INNER JOIN `tabGL Account` ga ON ga.name = jea.account
			WHERE {where_sql}
				AND je.posting_date BETWEEN %(fd)s AND %(td)s
				AND ga.account_type IN ('Income', 'Expense')
			""",
			params,
		)[0][0]
	)

	wc_rows = frappe.db.sql(
		f"""
		SELECT
			ga.name AS account,
			ga.working_capital_bucket AS bucket,
			ga.account_type AS atype,
			SUM(CASE WHEN je.posting_date < %(fd)s THEN jea.debit - jea.credit ELSE 0 END) AS open_dr_net,
			SUM(CASE WHEN je.posting_date <= %(td)s THEN jea.debit - jea.credit ELSE 0 END) AS close_dr_net
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {where_sql}
			AND IFNULL(ga.working_capital_bucket, '') NOT IN ('', 'Exclude')
		GROUP BY ga.name, ga.working_capital_bucket, ga.account_type
		""",
		params,
		as_dict=True,
	)

	bucket_adj = {}
	for r in wc_rows:
		bucket = (r.bucket or "").strip()
		if not bucket or bucket == "Exclude":
			continue
		delta = flt(r.close_dr_net) - flt(r.open_dr_net)
		adj = -delta
		bucket_adj[bucket] = bucket_adj.get(bucket, 0.0) + adj

	wc_adjustment = sum(bucket_adj.values())
	detail_lines = [{"line": _("WC — {0}").format(b), "amount": flt(a)} for b, a in sorted(bucket_adj.items())]

	operating_indirect = flt(net_income + wc_adjustment)

	columns = [
		{"label": _("Line"), "fieldname": "line", "fieldtype": "Data", "width": 420},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
	]

	data = [
		{"line": _("Net income (Income − Expense, Journal Entry period)"), "amount": net_income},
		{"line": _("Working capital adjustment (sum of buckets below)"), "amount": wc_adjustment},
	]
	data.extend(detail_lines)
	data.append({"line": _("Operating cash flow (indicative, indirect)"), "amount": operating_indirect})

	report_summary = [
		{"value": net_income, "label": _("Net income"), "datatype": "Currency"},
		{"value": wc_adjustment, "label": _("WC adj"), "datatype": "Currency"},
		{"value": operating_indirect, "label": _("Operating (indirect)"), "datatype": "Currency"},
	]

	msg = _(
		"MVP indirect method: P&L from Journal Entry only; working capital adjustment = "
		"−Δ(cumulative debit−credit) on each GL account tagged with **Working Capital Bucket** (assets & liabilities). "
		"Excludes investing/financing schedules, D&A lines, taxes, intercompany elimination, and full IAS 7 notes."
	)

	return columns, data, msg, None, report_summary, True


def _empty():
	return (
		[
			{"label": _("Line"), "fieldname": "line", "fieldtype": "Data", "width": 420},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140},
		],
		[],
		None,
		None,
		[],
		True,
	)
