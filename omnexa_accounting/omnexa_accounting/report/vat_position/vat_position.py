# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from omnexa_accounting.utils.vat_accounts import resolve_vat_accounts
from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	resolved = resolve_vat_accounts(filters.company, branch=filters.get("branch"))
	input_acc = resolved.get("input_vat_gl")
	output_acc = resolved.get("output_vat_gl")

	columns = [
		{"label": _("VAT Side"), "fieldname": "vat_side", "fieldtype": "Data", "width": 160
	},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "GL Account", "width": 180
	},
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 220
	},
		{"label": _("Resolution"), "fieldname": "resolution", "fieldtype": "Data", "width": 180
	},
		{"label": _("Opening Balance"), "fieldname": "opening_balance", "fieldtype": "Currency", "width": 140
	},
		{"label": _("Period Movement"), "fieldname": "period_movement", "fieldtype": "Currency", "width": 140
	},
		{"label": _("Closing Balance"), "fieldname": "closing_balance", "fieldtype": "Currency", "width": 140
	},
	]
	data = _build_rows(filters, input_acc, output_acc, resolved)
	msg = _("Accounts resolved via Company defaults → CoA account_number → name patterns. Sources shown per row.")
	return columns, data, msg


def _build_rows(filters, input_acc, output_acc, resolved):
	rows = [
		{
			"vat_side": _("VAT Position"),
			"account_name": _("Input / Output VAT Position"),
			"bold": 1,
			"year_header": 1
	}
	]
	input_open, input_mov, input_close = _calc_account_balance(filters, input_acc)
	output_open, output_mov, output_close = _calc_account_balance(filters, output_acc)

	rows.append(
		{
			"vat_side": _("Input VAT"),
			"account": input_acc,
			"account_name": _("Input VAT Recoverable"),
			"resolution": resolved.get("input_source"),
			"opening_balance": input_open,
			"period_movement": input_mov,
			"closing_balance": input_close
	}
	)
	rows.append(
		{
			"vat_side": _("Output VAT"),
			"account": output_acc,
			"account_name": _("Output VAT Payable"),
			"resolution": resolved.get("output_source"),
			"opening_balance": output_open,
			"period_movement": output_mov,
			"closing_balance": output_close
	}
	)

	net_open = output_open - input_open
	net_mov = output_mov - input_mov
	net_close = output_close - input_close
	rows.append(
		{
			"vat_side": _("Net VAT"),
			"account_name": _("Net VAT (Payable + / Recoverable -)"),
			"opening_balance": net_open,
			"period_movement": net_mov,
			"closing_balance": net_close,
			"bold": 1,
			"is_total_row": 1
	}
	)
	return rows


def _calc_account_balance(filters, account: str | None):
	if not account:
		return 0.0, 0.0, 0.0
	conditions = [
		"je.company = %(company)s",
		"je.docstatus = 1",
		"jea.account = %(account)s",
	]
	params = frappe._dict(filters.copy())
	params.account = account
	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return 0.0, 0.0, 0.0
		params.allowed_branches = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")
	row = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN je.posting_date < %(from_date)s THEN jea.credit - jea.debit ELSE 0 END) AS opening_balance,
			SUM(CASE WHEN je.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN jea.credit - jea.debit ELSE 0 END) AS period_movement
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		WHERE {" AND ".join(conditions)}
		""",
		params,
		as_dict=True,
	)
	opening = flt((row[0] or {}).get("opening_balance"))
	period = flt((row[0] or {}).get("period_movement"))
	return opening, period, opening + period
