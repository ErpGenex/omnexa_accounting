# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe


def execute():
	"""Backfill Account Label/Tree Label for existing GL Account rows."""
	if not frappe.db.exists("DocType", "GL Account"):
		return
	if not frappe.db.has_column("GL Account", "account_label"):
		return

	has_tree_label = frappe.db.has_column("GL Account", "tree_label")
	rows = frappe.get_all(
		"GL Account",
		fields=["name", "account_name", "account_number", "account_label", "tree_label"] if has_tree_label else ["name", "account_name", "account_number", "account_label"],
		limit_page_length=100000,
	)
	for row in rows:
		account_name = (row.account_name or "").strip() or row.name
		account_number = (row.account_number or "").strip()
		target_label = account_name
		target_tree = f"{account_name} - {account_number}" if account_number and account_name else (account_name or account_number or row.name)

		needs_update = False
		values = {}
		if (row.account_label or "") != target_label:
			values["account_label"] = target_label
			needs_update = True
		if has_tree_label and (getattr(row, "tree_label", "") or "") != target_tree:
			values["tree_label"] = target_tree
			needs_update = True
		if needs_update:
			frappe.db.set_value("GL Account", row.name, values, update_modified=False)

