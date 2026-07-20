from __future__ import annotations

import frappe
from frappe import _

from omnexa_core.omnexa_core.utils.report_charts import auto_chart_for_columns
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = ["1=1"]
	params = {}
	if filters.get("company"):
		conditions.append("ba.company = %(company)s")
		params["company"] = filters.company

	data = frappe.db.sql(
		f"""
		SELECT
			ba.name AS bank_account,
			ba.account_title,
			ba.company,
			ba.bank_name,
			ba.account_number,
			ba.currency,
			SUM(CASE WHEN pe.docstatus=1 THEN pe.paid_amount ELSE 0 END) AS posted_movements
		FROM `tabBank Account` ba
		LEFT JOIN `tabPayment Entry` pe
			ON pe.bank_account = ba.name
		WHERE {" AND ".join(conditions)}
		GROUP BY ba.name, ba.account_title, ba.company, ba.bank_name, ba.account_number, ba.currency
		ORDER BY ba.company, ba.bank_name, ba.account_title
		""",
		params,
		as_dict=True,
	)
	for r in data:
		r["posted_movements"] = flt(r.get("posted_movements"))

	columns = [
		{"label": _("Bank Account"), "fieldname": "bank_account", "fieldtype": "Link", "options": "Bank Account", "width": 180
	},
		{"label": _("Account Title"), "fieldname": "account_title", "fieldtype": "Data", "width": 180
	},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140
	},
		{"label": _("Bank Name"), "fieldname": "bank_name", "fieldtype": "Data", "width": 150
	},
		{"label": _("Account Number"), "fieldname": "account_number", "fieldtype": "Data", "width": 140
	},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 90
	},
		{"label": _("Posted Movements"), "fieldname": "posted_movements", "fieldtype": "Currency", "width": 130
	},
	]
	chart = auto_chart_for_columns(data, columns)
	return columns, data, None, chart