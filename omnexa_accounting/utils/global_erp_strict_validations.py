# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt
"""Optional chain validations aligned with Global ERP Workflow Engine Standard (per Company flag)."""

import frappe
from frappe import _


def _strict_enabled(company: str | None) -> bool:
	if not company:
		return False
	return bool(frappe.db.get_value("Company", company, "global_erp_strict_workflow"))


def validate_sales_quotation(doc, method=None):
	if not _strict_enabled(getattr(doc, "company", None)):
		return
	if not getattr(doc, "pipeline_opportunity", None):
		frappe.throw(
			_("Global ERP strict mode: link a Pipeline Opportunity before saving the quotation."),
			title=_("Validation"),
		)


def validate_sales_invoice(doc, method=None):
	if not _strict_enabled(getattr(doc, "company", None)):
		return
	if getattr(doc, "is_return", 0):
		return
	for row in doc.get("items") or []:
		if not row.item:
			continue
		if frappe.db.get_value("Item", row.item, "is_stock_item"):
			if not getattr(doc, "delivery_note", None):
				frappe.throw(
					_(
						"Global ERP strict mode: Delivery Note is required when invoicing stock items."
					),
					title=_("Validation"),
				)
			return


def validate_purchase_invoice(doc, method=None):
	if not _strict_enabled(getattr(doc, "company", None)):
		return
	if getattr(doc, "is_return", 0):
		return
	for row in doc.get("items") or []:
		if not row.item:
			continue
		if frappe.db.get_value("Item", row.item, "is_stock_item"):
			if not getattr(doc, "goods_receipt_reference", None):
				frappe.throw(
					_(
						"Global ERP strict mode: Goods Receipt Reference is required when purchase invoicing stock items."
					),
					title=_("Validation"),
				)
			return
