# Copyright (c) 2026, Omnexa
from __future__ import annotations

import frappe
from frappe.utils import getdate

from omnexa_accounting.utils.microlab_company_seed import (
	COMPANY_ABBR,
	END_DATE,
	PARTNER_FUNDED,
	PARTNER_SILENT,
	START_DATE,
)


def execute():
	"""Create Microlab Company Partner Legal Setup from seeded GL accounts."""
	if not frappe.db.exists("Company", COMPANY_ABBR):
		return

	company = COMPANY_ABBR
	branch = frappe.db.get_value("Branch", {"company": company}, "name")
	sayed_current = frappe.db.get_value("GL Account", {"company": company, "account_number": "3111"}, "name")
	elham_due = frappe.db.get_value("GL Account", {"company": company, "account_number": "1332"}, "name")

	if frappe.db.exists("Company Partner Legal Setup", company):
		doc = frappe.get_doc("Company Partner Legal Setup", company)
	else:
		doc = frappe.new_doc("Company Partner Legal Setup")
		doc.company = company

	doc.branch = branch
	doc.default_from_date = getdate(START_DATE)
	doc.default_to_date = getdate(END_DATE)
	doc.legal_case_reference = "قضية شركاء ميكرولاب"
	doc.notes = "أُنشئ تلقائياً من بذرة ميكرولاب — الشريك الممول يدفع المصروفات والشريك المدين يستحق حصة الملكية."
	doc.set("partners", [])
	doc.append(
		"partners",
		{
			"partner_name": PARTNER_FUNDED,
			"partner_name_ar": "سيد هاشم حسن",
			"ownership_percent": 80,
			"is_funding_partner": 1,
			"partner_current_account": sayed_current,
		},
	)
	doc.append(
		"partners",
		{
			"partner_name": PARTNER_SILENT,
			"partner_name_ar": "إلهام مصطفى محمد أحمد",
			"ownership_percent": 20,
			"is_funding_partner": 0,
			"due_from_partner_account": elham_due,
		},
	)
	doc.flags.ignore_permissions = True
	doc.save()
