from __future__ import annotations

import frappe

from omnexa_accounting.utils.coa_template_service import _clean_main_account_type, _clean_sub_account_type


def _normalize_doctype(doctype: str) -> int:
	if not frappe.db.exists("DocType", doctype):
		return 0
	changed = 0
	rows = frappe.get_all(
		doctype,
		fields=["name", "main_account_type", "sub_account_type"],
		limit_page_length=200000,
	)
	for row in rows:
		new_main = _clean_main_account_type(row.get("main_account_type"))
		new_sub = _clean_sub_account_type(row.get("sub_account_type"))
		payload = {}
		if (row.get("main_account_type") or "") != (new_main or ""):
			payload["main_account_type"] = new_main
		if (row.get("sub_account_type") or "") != (new_sub or ""):
			payload["sub_account_type"] = new_sub
		if not payload:
			continue
		frappe.db.set_value(doctype, row["name"], payload, update_modified=False)
		changed += 1
	return changed


def execute():
	total = 0
	total += _normalize_doctype("GL Account")
	total += _normalize_doctype("COA Template Line")
	if total:
		frappe.db.commit()

