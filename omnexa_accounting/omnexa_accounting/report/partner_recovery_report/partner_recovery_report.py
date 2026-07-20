# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_accounting.utils.partner_legal_reporting import d, resolve_partner_accounts, resolve_partner_labels


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))
	secondary_pct = Decimal(str(filters.get("secondary_pct") or 20)) / Decimal("100")
	acc = resolve_partner_accounts(filters.company, filters, branch=filters.get("branch"))
	labels = resolve_partner_labels(filters)
	primary_current = acc["primary_current"]
	if not primary_current:
		frappe.throw(_("Primary current account was not resolved."))

	params = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"primary_current": primary_current
	}
	conds = ["je.company=%(company)s", "je.docstatus=1", "je.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
	if filters.get("branch") and frappe.get_meta("Journal Entry").has_field("branch"):
		conds.append("je.branch=%(branch)s")
		params["branch"] = filters.branch

	data = frappe.db.sql(
		f"""
		SELECT
			je.posting_date,
			je.name AS journal_entry,
			je.reference,
			ga.account_name AS expense_type,
			jea.debit AS amount_paid_by_primary
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {' AND '.join(conds)}
		  AND ga.account_type='Expense'
		  AND EXISTS (
			SELECT 1 FROM `tabJournal Entry Account` c
			WHERE c.parent = je.name
			  AND c.account = %(primary_current)s
			  AND c.credit > 0
		  )
		ORDER BY je.posting_date, je.name, jea.idx
		""",
		params,
		as_dict=True,
	)

	cum = Decimal("0")
	for row in data:
		amount = d(row.get("amount_paid_by_primary"))
		share = amount * secondary_pct
		cum += share
		row["secondary_share"] = float(share)
		row["cumulative_secondary_recovery"] = float(cum)

	columns = [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100
	},
		{"label": _("Journal Entry"), "fieldname": "journal_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 140
	},
		{"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 140
	},
		{"label": _("Expense Type"), "fieldname": "expense_type", "fieldtype": "Data", "width": 180
	},
		{"label": _("Paid by {0}").format(labels["primary_partner_name"]), "fieldname": "amount_paid_by_primary", "fieldtype": "Currency", "width": 170
	},
		{"label": _("{0} Share").format(labels["secondary_partner_name"]), "fieldname": "secondary_share", "fieldtype": "Currency", "width": 150
	},
		{
			"label": _("Cumulative Recovery for {0}").format(labels["secondary_partner_name"]),
			"fieldname": "cumulative_secondary_recovery",
			"fieldtype": "Currency",
			"width": 150
	},
	]
	chart = {
		"data": {
			"labels": [str(r.get("posting_date")) for r in data[:24]],
			"datasets": [{"name": _("Secondary Share"), "values": [flt(r.get("secondary_share")) for r in data[:24]]}]
	},
		"type": "line",
		"title": _("Partner Recovery Trend"),
		"height": 260
	}
	return columns, data, None, chart
