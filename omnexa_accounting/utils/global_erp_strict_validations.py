# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt
"""Optional chain validations aligned with Global ERP Workflow Engine Standard (per Company flags)."""

import frappe
from frappe import _


def _company_chain_flags(company: str | None) -> dict:
	if not company:
		return {
			"strict": False,
			"require_sales_order": False,
			"require_delivery_note_stock": False,
			"require_goods_receipt_stock": False
	}
	row = frappe.db.get_value(
		"Company",
		company,
		[
			"global_erp_strict_workflow",
			"global_erp_require_sales_order_on_sales_invoice",
			"global_erp_require_delivery_note_on_stock_invoice",
		],
		as_dict=True,
	)
	if not row or not row.global_erp_strict_workflow:
		return {
			"strict": False,
			"require_sales_order": False,
			"require_delivery_note_stock": False,
			"require_goods_receipt_stock": False
	}
	return {
		"strict": True,
		"require_sales_order": bool(row.global_erp_require_sales_order_on_sales_invoice),
		"require_delivery_note_stock": bool(
			row.global_erp_require_delivery_note_on_stock_invoice
		),
		# Purchase side: still required when strict (no separate switch yet)
		"require_goods_receipt_stock": True
	}


def validate_sales_quotation(doc, method=None):
	flags = _company_chain_flags(getattr(doc, "company", None))
	if not flags["strict"]:
		return
	if not getattr(doc, "pipeline_opportunity", None):
		frappe.throw(
			_("Global ERP strict mode: link a Pipeline Opportunity before saving the quotation."),
			title=_("Validation"),
		)


def validate_sales_invoice(doc, method=None):
	flags = _company_chain_flags(getattr(doc, "company", None))
	if not flags["strict"]:
		return
	if getattr(doc, "is_return", 0):
		return

	if flags["require_sales_order"] and not getattr(doc, "sales_order", None):
		frappe.throw(
			_("Global ERP strict mode: Sales Order is required on this invoice."),
			title=_("Validation"),
		)

	if not flags["require_delivery_note_stock"]:
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
	flags = _company_chain_flags(getattr(doc, "company", None))
	if not flags["strict"] or not flags["require_goods_receipt_stock"]:
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
