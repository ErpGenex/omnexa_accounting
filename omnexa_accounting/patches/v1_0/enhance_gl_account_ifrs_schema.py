# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe


def _normalize_class(value: str | None) -> str:
	v = (value or "").strip()
	return "Revenue" if v == "Income" else v


def execute():
	"""Backfill new enterprise CoA fields without breaking existing data."""
	if not frappe.db.exists("DocType", "GL Account"):
		return

	rows = frappe.get_all(
		"GL Account",
		fields=[
			"name",
			"is_group",
			"account_name",
			"account_type",
			"account_class",
			"posting_type",
			"cash_flow_section",
			"working_capital_bucket",
		],
		limit_page_length=200000,
	)

	updated = 0
	for row in rows:
		account_class = _normalize_class(row.account_class or row.account_type)
		if account_class not in ("Asset", "Liability", "Equity", "Revenue", "Expense"):
			account_class = "Expense"

		posting_type = row.posting_type or ("Header" if int(row.is_group or 0) else "Posting")
		cash_flow_section = row.cash_flow_section or "Exclude"
		wc = row.working_capital_bucket or "Other"
		name_lower = (row.account_name or "").lower()
		if "receivable" in name_lower:
			wc = "Receivable"
		elif "payable" in name_lower:
			wc = "Payable"
		elif "inventory" in name_lower or "stock" in name_lower:
			wc = "Inventory"
		if cash_flow_section == "Exclude":
			if "bank" in name_lower or "cash" in name_lower:
				cash_flow_section = "Operating Activities"
			elif "fixed asset" in name_lower or "property" in name_lower or "equipment" in name_lower:
				cash_flow_section = "Investing Activities"

		values = {
			"account_class": account_class,
			"account_type": account_class,
			"posting_type": posting_type,
			"allow_direct_posting": 0 if posting_type == "Header" else 1,
			"cash_flow_section": cash_flow_section,
			"working_capital_bucket": wc,
		}
		frappe.db.set_value("GL Account", row.name, values, update_modified=False)
		updated += 1

	frappe.get_doc(
		{
			"doctype": "Error Log",
			"method": "omnexa_accounting.patches.v1_0.enhance_gl_account_ifrs_schema",
			"error": f"GL Account IFRS migration completed. Updated rows: {updated}",
		}
	).insert(ignore_permissions=True)
