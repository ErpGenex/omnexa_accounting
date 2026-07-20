import frappe
from frappe import _
from frappe.utils import flt

from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."), title=_("Filters"))

	columns = [
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 220
	},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "GL Account", "width": 180
	},
		{"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 220
	},
		{"label": _("Opening Balance"), "fieldname": "opening_balance", "fieldtype": "Currency", "width": 140
	},
		{"label": _("Movements in Period"), "fieldname": "period_movement", "fieldtype": "Currency", "width": 160
	},
		{"label": _("Closing Balance"), "fieldname": "closing_balance", "fieldtype": "Currency", "width": 140
	},
	]
	data = _build_rows(filters)
	return columns, data


def _build_rows(filters):
	conditions = [
		"je.company = %(company)s",
		"je.docstatus = 1",
		"ga.account_type = 'Equity'",
	]
	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			return []
		filters.allowed_branches = tuple(allowed)
		conditions.append("je.branch in %(allowed_branches)s")

	rows = frappe.db.sql(
		f"""
		SELECT
			jea.account,
			ga.account_name,
			SUM(CASE WHEN je.posting_date < %(from_date)s THEN jea.credit - jea.debit ELSE 0 END) AS opening_balance,
			SUM(CASE WHEN je.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN jea.credit - jea.debit ELSE 0 END) AS period_movement
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		INNER JOIN `tabGL Account` ga ON ga.name = jea.account
		WHERE {" AND ".join(conditions)}
		GROUP BY jea.account, ga.account_name
		ORDER BY ga.account_number, ga.account_name
		""",
		filters,
		as_dict=True,
	)

	data = [
		{
			"section": _("Opening Equity"),
			"account_name": _("Statement of Changes in Equity"),
			"bold": 1,
			"year_header": 1
	}
	]
	total_opening = total_movement = total_closing = 0.0

	for row in rows:
		opening = flt(row.opening_balance)
		movement = flt(row.period_movement)
		closing = opening + movement
		total_opening += opening
		total_movement += movement
		total_closing += closing
		data.append(
			{
				"section": _("Equity Account"),
				"account": row.account,
				"account_name": row.account_name,
				"opening_balance": opening,
				"period_movement": movement,
				"closing_balance": closing
	}
		)

	data.extend(
		[
			{
				"section": _("Total Equity"),
				"account_name": _("Total Opening Equity"),
				"opening_balance": total_opening,
				"bold": 1,
				"is_total_row": 1
	},
			{
				"section": _("Total Equity"),
				"account_name": _("Total Movements in Period"),
				"period_movement": total_movement,
				"bold": 1,
				"is_total_row": 1
	},
			{
				"section": _("Total Equity"),
				"account_name": _("Total Closing Equity"),
				"closing_balance": total_closing,
				"bold": 1,
				"is_total_row": 1
	},
		]
	)
	return data
