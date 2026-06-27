# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Resolve company Tax Rule for invoice compliance and amount calculation."""

from __future__ import annotations

import frappe
from frappe.utils import getdate, today


def resolve_default_tax_rule(
	company: str,
	posting_date=None,
	tax_category: str | None = None,
) -> str | None:
	"""Pick an active Tax Rule for the company on posting_date (standard VAT preferred)."""
	if not company or not frappe.db.exists("DocType", "Tax Rule"):
		return None
	posting_date = getdate(posting_date or today())
	base_filters = {
		"company": company,
		"valid_from": ["<=", posting_date],
		"valid_to": [">=", posting_date],
	}
	if tax_category:
		base_filters["tax_category"] = tax_category

	for tax_type in ("standard", "zero", "exempt", "out_of_scope"):
		name = frappe.db.get_value(
			"Tax Rule",
			{**base_filters, "tax_type": tax_type},
			"name",
			order_by="rate desc, modified desc",
		)
		if name:
			return name

	if tax_category:
		return resolve_default_tax_rule(company, posting_date, tax_category=None)
	return None


def _default_sales_tax_category() -> str | None:
	try:
		from omnexa_core.omnexa_core.doctype.omnexa_sales_settings.omnexa_sales_settings import (
			get_sales_settings,
		)

		cat = (get_sales_settings().get("default_sales_tax_category") or "").strip()
		return cat or None
	except Exception:
		return None


def apply_invoice_tax_rule_defaults(doc) -> bool:
	"""Set header (and line) tax_rule when missing. Returns True if a rule was applied."""
	if not doc.get("company"):
		return False
	if doc.meta.has_field("due_date") and doc.get("posting_date") and not doc.get("due_date"):
		doc.due_date = doc.posting_date
	if doc.meta.has_field("tax_category") and not doc.get("tax_category"):
		cat = _default_sales_tax_category()
		if cat and frappe.db.exists("Tax Category", cat):
			doc.tax_category = cat
	if doc.meta.has_field("default_tax_rule") and doc.get("default_tax_rule"):
		return False
	if any((row.get("tax_rule") or "").strip() for row in doc.get("items") or []):
		return False
	if doc.meta.has_field("tax_rate") and frappe.utils.flt(getattr(doc, "tax_rate", 0)):
		return False

	tax_category = doc.get("tax_category") if doc.meta.has_field("tax_category") else None
	rule = resolve_default_tax_rule(doc.company, doc.get("posting_date"), tax_category)
	if not rule:
		return False

	if doc.meta.has_field("default_tax_rule"):
		doc.default_tax_rule = rule

	child_table = doc.meta.get_field("items")
	if child_table:
		try:
			item_meta = frappe.get_meta(child_table.options)
		except Exception:
			item_meta = None
		if item_meta and item_meta.has_field("tax_rule"):
			for row in doc.get("items") or []:
				if not row.get("tax_rule"):
					row.tax_rule = rule
	return True
