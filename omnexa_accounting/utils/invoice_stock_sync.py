from __future__ import annotations

import frappe
from frappe.utils import flt


def _posting_ref(doctype: str, docname: str) -> str:
	return f"{doctype}:{docname}"


def _find_linked_stock_entry(doctype: str, docname: str, company: str, branch: str | None = None) -> str | None:
	filters = {"company": company, "reference": _posting_ref(doctype, docname)}
	if branch and frappe.get_meta("Stock Entry").has_field("branch"):
		filters["branch"] = branch
	return frappe.db.get_value("Stock Entry", filters, "name")


def post_sales_invoice_stock(sales_invoice) -> str | None:
	if not sales_invoice or int(sales_invoice.docstatus or 0) != 1:
		return None
	if not int(getattr(sales_invoice, "update_stock", 0) or 0):
		return None
	warehouse = getattr(sales_invoice, "set_warehouse", None)
	if not warehouse:
		return None
	existing = _find_linked_stock_entry("Sales Invoice", sales_invoice.name, sales_invoice.company, sales_invoice.branch)
	if existing:
		return existing

	items = []
	for row in sales_invoice.get("items") or []:
		if not row.item:
			continue
		if not frappe.db.get_value("Item", row.item, "is_stock_item"):
			continue
		qty = flt(row.qty)
		if qty <= 0:
			continue
		items.append({"item": row.item, "item_code": row.item_code, "s_warehouse": warehouse, "qty": qty, "rate": row.rate})
	if not items:
		return None

	se = frappe.new_doc("Stock Entry")
	se.company = sales_invoice.company
	if getattr(sales_invoice, "branch", None) and se.meta.has_field("branch"):
		se.branch = sales_invoice.branch
	se.purpose = "Material Issue"
	se.posting_date = sales_invoice.posting_date
	se.reference = _posting_ref("Sales Invoice", sales_invoice.name)
	se.from_warehouse = warehouse
	se.items = items
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name


def post_purchase_invoice_stock(purchase_invoice) -> str | None:
	if not purchase_invoice or int(purchase_invoice.docstatus or 0) != 1:
		return None
	if not int(getattr(purchase_invoice, "update_stock", 0) or 0):
		return None
	warehouse = getattr(purchase_invoice, "set_warehouse", None)
	if not warehouse:
		return None
	existing = _find_linked_stock_entry(
		"Purchase Invoice", purchase_invoice.name, purchase_invoice.company, purchase_invoice.branch
	)
	if existing:
		return existing

	items = []
	for row in purchase_invoice.get("items") or []:
		if not row.item:
			continue
		if not frappe.db.get_value("Item", row.item, "is_stock_item"):
			continue
		qty = flt(row.qty)
		if qty <= 0:
			continue
		items.append({"item": row.item, "item_code": row.item_code, "t_warehouse": warehouse, "qty": qty, "rate": row.rate})
	if not items:
		return None

	se = frappe.new_doc("Stock Entry")
	se.company = purchase_invoice.company
	if getattr(purchase_invoice, "branch", None) and se.meta.has_field("branch"):
		se.branch = purchase_invoice.branch
	se.purpose = "Material Receipt"
	se.posting_date = purchase_invoice.posting_date
	se.reference = _posting_ref("Purchase Invoice", purchase_invoice.name)
	se.to_warehouse = warehouse
	se.items = items
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name


def cancel_invoice_stock(doctype: str, docname: str, company: str, branch: str | None = None) -> str | None:
	stock_entry = _find_linked_stock_entry(doctype, docname, company, branch)
	if not stock_entry:
		return None
	doc = frappe.get_doc("Stock Entry", stock_entry)
	if int(doc.docstatus or 0) == 1:
		doc.cancel()
	return stock_entry

