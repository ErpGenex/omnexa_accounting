# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe


def execute():
	"""Backfill GL labels: Account Label=name, Tree Label=name-number (no hash id fallback)."""
	if not frappe.db.exists("DocType", "GL Account"):
		return

	has_account_label = frappe.db.has_column("GL Account", "account_label")
	has_tree_label = frappe.db.has_column("GL Account", "tree_label")
	if not has_account_label and not has_tree_label:
		return

	rows = frappe.get_all(
		"GL Account",
		fields=["name", "account_name", "account_number", "account_label", "tree_label"],
		limit_page_length=100000,
	)
	for row in rows:
		account_name = (row.account_name or "").strip()
		account_number = (row.account_number or "").strip()
		target_account_label = account_name or account_number or "Unnamed Account"
		target_tree_label = (
			f"{account_name} - {account_number}"
			if account_name and account_number
			else (account_name or account_number or "Unnamed Account")
		)

		values = {}
		if has_account_label and (row.account_label or "") != target_account_label:
			values["account_label"] = target_account_label
		if has_tree_label and (row.tree_label or "") != target_tree_label:
			values["tree_label"] = target_tree_label
		if values:
			frappe.db.set_value("GL Account", row.name, values, update_modified=False)
