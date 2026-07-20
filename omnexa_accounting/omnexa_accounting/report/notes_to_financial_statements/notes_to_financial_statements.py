# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""IAS 1 — structured notes pack (MVP) for disclosure workflow."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company = filters.get("company")
	fiscal_year = filters.get("fiscal_year")
	if not company:
		frappe.throw(_("Company is required"))
	if not fiscal_year:
		frappe.throw(_("Fiscal Year is required"))

	fy = frappe.get_doc("Fiscal Year", fiscal_year)
	company_doc = frappe.get_doc("Company", company)
	currency = company_doc.default_currency or ""

	columns = [
		{"label": _("Note"), "fieldname": "note_no", "fieldtype": "Data", "width": 70
	},
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 220
	},
		{"label": _("Disclosure"), "fieldname": "disclosure", "fieldtype": "Text", "width": 420
	},
		{"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 160
	},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120
	},
	]

	data = [
		{
			"note_no": "1",
			"section": _("Reporting entity"),
			"disclosure": _("Financial statements for {0} — fiscal year {1}.").format(company, fiscal_year),
			"reference": company
	},
		{
			"note_no": "2",
			"section": _("Basis of preparation"),
			"disclosure": _(
				"Prepared under the cost model with accrual accounting. "
				"Functional currency: {0}. Period: {1} to {2}."
			).format(currency, getdate(fy.year_start_date), getdate(fy.year_end_date)),
			"reference": "IAS 1"
	},
		{
			"note_no": "3",
			"section": _("Significant accounting policies"),
			"disclosure": _("See IFRS policy pack / company accounting policies for recognition and measurement."),
			"reference": "IAS 1.117"
	},
		{
			"note_no": "4",
			"section": _("Property, plant and equipment"),
			"disclosure": _("Refer to Fixed Assets register, depreciation schedule, and NBV by category reports."),
			"reference": "IAS 16"
	},
		{
			"note_no": "5",
			"section": _("Trade receivables and credit risk"),
			"disclosure": _("Refer to Receivables Aging and Receivables and DSO reports."),
			"reference": "IFRS 7"
	},
		{
			"note_no": "6",
			"section": _("Trade payables"),
			"disclosure": _("Refer to Payables Aging report."),
			"reference": "IAS 1"
	},
		{
			"note_no": "7",
			"section": _("Revenue"),
			"disclosure": _("Refer to Sales Register and Revenue Analysis reports."),
			"reference": "IFRS 15"
	},
		{
			"note_no": "8",
			"section": _("Subsequent events"),
			"disclosure": _("Management to document events after year-end before issuance."),
			"reference": "IAS 10"
	},
	]
	for row in data:
		row["amount"] = 0

	return columns, data
