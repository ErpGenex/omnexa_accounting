# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe


def execute():
	if not frappe.db.exists("DocType", "CoA Settings"):
		return
	companies = frappe.get_all("Company", pluck="name")
	for company in companies:
		if frappe.db.exists("CoA Settings", {"company": company
	}):
			continue
		frappe.get_doc(
			{
				"doctype": "CoA Settings",
				"company": company,
				"enable_numbering_engine": 1,
				"default_consolidation_view": 0,
				"manual_number_override_roles": "System Manager\nAccounts Manager",
				"asset_mask": "1xxx",
				"liability_mask": "2xxx",
				"equity_mask": "3xxx",
				"revenue_mask": "4xxx",
				"expense_mask": "5xxx",
				"require_group_reporting_tag_for_intercompany": 1,
				"enforce_account_currency_match": 1,
				"allow_direct_posting_default": 1
	}
		).insert(ignore_permissions=True)
