from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company") or not filters.get("bank_account"):
		frappe.throw(_("Company and Bank Account filters are required."), title=_("Filters"))
	rows = frappe.call(
		"omnexa_core.omnexa_core.finance.api.suggest_bank_reconciliation_matches",
		company=filters.company,
		bank_account=filters.bank_account,
		statement_date=filters.get("statement_date"),
		tolerance_days=filters.get("tolerance_days") or 7,
		limit=filters.get("limit") or 200,
	) or []

	columns = [
		{"label": _("Payment Entry"), "fieldname": "name", "fieldtype": "Link", "options": "Payment Entry", "width": 170
	},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110
	},
		{"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Data", "width": 100
	},
		{"label": _("Party"), "fieldname": "party", "fieldtype": "Dynamic Link", "options": "party_type", "width": 180
	},
		{"label": _("Paid Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120
	},
		{"label": _("Mode of Payment"), "fieldname": "mode_of_payment", "fieldtype": "Link", "options": "Mode of Payment", "width": 130
	},
		{"label": _("Remittance Ref"), "fieldname": "remittance_reference", "fieldtype": "Data", "width": 140
	},
		{"label": _("Remittance Date"), "fieldname": "remittance_date", "fieldtype": "Date", "width": 120
	},
		{"label": _("Bank Ref"), "fieldname": "remittance_bank_reference", "fieldtype": "Data", "width": 150
	},
	]
	return columns, rows

