# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import re

import frappe


@frappe.whitelist()
def get_children(doctype, parent="", **filters):
	"""Tree provider for GL Account that shows Account Name as label/title."""
	meta = frappe.get_meta(doctype)
	parent_field = meta.get("nsm_parent_field") or "parent_gl_account"
	conditions = [[f"ifnull(`{parent_field}`,'')", "=", parent], ["docstatus", "<", 2]]
	display_mode = (filters.get("display_mode") or "Show All").strip()

	rows = frappe.get_list(
		doctype,
		fields=["name", "account_name", "account_number", "account_label", "tree_label", "is_group"],
		filters=conditions,
		order_by="account_number asc, account_name asc, name asc",
	)

	def _is_advanced_number(number: str) -> bool:
		# Advanced coding usually contains letters/hyphens (e.g. MH-HO-AS-...).
		# Standard coding is pure numeric with optional separators.
		clean = (number or "").strip()
		if not clean:
			return False
		return not bool(re.fullmatch(r"[0-9.\-/]+", clean))

	out = []
	for r in rows:
		account_name = (r.get("account_name") or r.get("account_label") or "").strip()
		account_number = (r.get("account_number") or "").strip()
		is_advanced = _is_advanced_number(account_number)

		if display_mode == "Standard Only" and is_advanced:
			continue
		if display_mode == "Advanced Only" and not is_advanced:
			continue

		if account_name and account_number:
			title = f"{account_name} - {account_number}"
		else:
			title = account_name or account_number or "Unnamed Account"
		out.append(
			{
				"value": r.get("name"),
				"label": title,
				"title": title,
				"expandable": int(r.get("is_group") or 0)
	}
		)
	return out

