# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""IAS 7 indirect operating section + investing/financing from bank GL cash-flow classification."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches

_SECTIONS = ("Operating Activities", "Investing Activities", "Financing Activities")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	params = {"company": filters.company, "fd": filters.from_date, "td": filters.to_date
	}
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
			SUM(CASE WHEN je.posting_date < %(fd)s THEN jea.debit - jea.credit ELSE 0 END) AS open_dr_net,
			SUM(CASE WHEN je.posting_date <= %(td)s THEN jea.debit - jea.credit ELSE 0 END) AS close_dr_net
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {where_sql}
			AND IFNULL(ga.working_capital_bucket, '') NOT IN ('', 'Exclude')
		GROUP BY ga.name, ga.working_capital_bucket
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
		bucket_adj[bucket] = bucket_adj.get(bucket, 0.0) + (-delta)

	wc_adjustment = sum(bucket_adj.values())
	operating_indirect = flt(net_income + wc_adjustment)

	investing, financing, operating_je = _bank_section_totals(filters, params, where_sql)

	columns = [
		{"label": _("Line"), "fieldname": "line", "fieldtype": "Data", "width": 420
	},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140
	},
	]

	data = [
		{"line": _("A. Cash flows from operating activities"), "amount": None, "indent": 0
	},
		{"line": _("Net income (Income − Expense)"), "amount": net_income, "indent": 1
	},
		{"line": _("Adjustments — working capital"), "amount": wc_adjustment, "indent": 1
	},
	]
	for b, a in sorted(bucket_adj.items()):
		data.append({"line": _("  WC — {0}").format(b), "amount": flt(a), "indent": 2
	})
	data.append({"line": _("Operating — bank JE (classified)"), "amount": operating_je, "indent": 1
	})
	operating_total = flt(operating_indirect + operating_je)
	data.append({"line": _("Net cash from operating activities"), "amount": operating_total, "indent": 0
	})

	data.extend(
		[
			{"line": _("B. Cash flows from investing activities"), "amount": None, "indent": 0
	},
			{"line": _("Investing — bank JE (classified)"), "amount": investing, "indent": 1
	},
			{"line": _("Net cash from investing activities"), "amount": investing, "indent": 0
	},
			{"line": _("C. Cash flows from financing activities"), "amount": None, "indent": 0
	},
			{"line": _("Financing — bank JE (classified)"), "amount": financing, "indent": 1
	},
			{"line": _("Net cash from financing activities"), "amount": financing, "indent": 0
	},
		]
	)

	net_change = flt(operating_total + investing + financing)
	data.append({"line": _("Net increase (decrease) in cash and cash equivalents"), "amount": net_change, "indent": 0
	})

	report_summary = [
		{"value": operating_total, "label": _("Operating"), "datatype": "Currency"
	},
		{"value": investing, "label": _("Investing"), "datatype": "Currency"
	},
		{"value": financing, "label": _("Financing"), "datatype": "Currency"
	},
		{"value": net_change, "label": _("Net change"), "datatype": "Currency"
	},
	]

	msg = _(
		"IAS 7 layout: indirect operating (net income + working-capital buckets on GL accounts) "
		"plus investing/financing from bank-side Journal Entry lines classified via "
		"GL Account → Cash Flow Section. Not a full audited statement — excludes D&A add-backs, "
		"tax paid, interest split, and opening/closing cash reconciliation."
	)

	return columns, data, msg, None, report_summary, True


def _bank_section_totals(filters, params, je_where):
	bank_gl = set(
		frappe.db.sql(
			"""SELECT DISTINCT gl_account FROM `tabBank Account`
			WHERE company = %(company)s AND IFNULL(gl_account,'') != ''""",
			{"company": filters.company
	},
			pluck=True,
		)
	)
	if not bank_gl:
		return 0.0, 0.0, 0.0

	section_by_account = {
		r.name: (r.cash_flow_section or "").strip() or "Exclude"
		for r in frappe.db.get_all(
			"GL Account",
			filters={"company": filters.company
	},
			fields=["name", "cash_flow_section"],
		)
	}

	je_names = frappe.db.sql(
		f"""SELECT je.name FROM `tabJournal Entry` je
		WHERE {je_where} AND je.posting_date BETWEEN %(fd)s AND %(td)s""",
		params,
		pluck=True,
	)

	je_totals = defaultdict(float)
	for je_name in je_names:
		lines = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabJournal Entry Account` WHERE parent = %s""",
			je_name,
			as_dict=True,
		)
		bank_net = 0.0
		non_bank = []
		for L in lines:
			net = flt(L.debit) - flt(L.credit)
			if L.account in bank_gl:
				bank_net += net
			else:
				non_bank.append((L.account, abs(net)))
		if abs(bank_net) < 1e-9:
			continue
		section = "Operating Activities"
		if non_bank:
			dominant = max(non_bank, key=lambda x: x[1])[0]
			s = section_by_account.get(dominant, "Exclude")
			if s in _SECTIONS:
				section = s
		je_totals[section] += bank_net

	return (
		flt(je_totals["Investing Activities"]),
		flt(je_totals["Financing Activities"]),
		flt(je_totals["Operating Activities"]),
	)


def _empty():
	return (
		[
			{"label": _("Line"), "fieldname": "line", "fieldtype": "Data", "width": 420
	},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 140
	},
		],
		[],
		None,
		None,
		[],
		True,
	)
