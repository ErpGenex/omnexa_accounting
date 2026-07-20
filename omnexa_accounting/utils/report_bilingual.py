# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Bilingual (EN/AR) column helpers for accounting Script Reports."""

from __future__ import annotations

import frappe
from frappe import _

_gl_name_ar_column: bool | None = None


def has_gl_account_name_ar() -> bool:
	global _gl_name_ar_column
	if _gl_name_ar_column is None:
		_gl_name_ar_column = bool(frappe.db.has_column("GL Account", "account_name_ar"))
	return _gl_name_ar_column


def account_name_ar_column(*, width: int = 200) -> dict:
	return {
		"label": _("Account Name (Arabic)"),
		"fieldname": "account_name_ar",
		"fieldtype": "Data",
		"width": width
	}


def insert_account_name_ar_column(columns: list[dict], *, after: str = "account_name") -> list[dict]:
	if not has_gl_account_name_ar():
		return columns
	out = list(columns)
	idx = next((i + 1 for i, col in enumerate(out) if col.get("fieldname") == after), len(out))
	out.insert(idx, account_name_ar_column())
	return out


def gl_account_name_ar_select(alias: str = "ga") -> str:
	if has_gl_account_name_ar():
		return f"{alias}.account_name_ar"
	return "NULL AS account_name_ar"


def localize_column_labels(columns: list[dict]) -> list[dict]:
	"""Ensure column labels use _() for Desk/print translation."""
	out = []
	for col in columns:
		c = dict(col)
		label = c.get("label")
		if isinstance(label, str) and label and not label.startswith("_("):
			c["label"] = _(label)
		out.append(c)
	return out
