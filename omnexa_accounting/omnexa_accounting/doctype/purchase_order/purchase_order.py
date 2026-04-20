# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_accounting.utils.branch import validate_branch_company


class PurchaseOrder(Document):
	def _sync_and_validate_line_items(self):
		"""Align with Purchase Invoice Item: Item link + Item Code column; sync code from Item when set."""
		for row in self.items or []:
			if not row.item and (not row.item_code or not str(row.item_code).strip()):
				frappe.throw(
					_("Row {0}: Set Item or Item Code.").format(row.idx),
					title=_("Items"),
				)
			if not row.item:
				continue
			it = frappe.get_cached_doc("Item", row.item)
			if it.company != self.company:
				frappe.throw(
					_("Row {0}: Item belongs to a different company.").format(row.idx),
					title=_("Item"),
				)
			if it.disabled:
				frappe.throw(_("Row {0}: Item is disabled.").format(row.idx), title=_("Item"))
			if not it.is_purchase_item:
				frappe.throw(
					_("Row {0}: Item cannot be purchased (Is Purchase Item is off).").format(row.idx),
					title=_("Item"),
				)
			if not row.item_code:
				row.item_code = it.item_code
			elif row.item_code != it.item_code:
				frappe.throw(
					_("Row {0}: Item Code must match the selected Item.").format(row.idx),
					title=_("Item"),
				)

	def validate(self):
		validate_branch_company(self)
		if self.get("purchase_request"):
			pr = frappe.db.get_value(
				"Purchase Request",
				self.purchase_request,
				["company", "docstatus"],
				as_dict=True,
			)
			if not pr:
				frappe.throw(_("Invalid Purchase Request."), title=_("Purchase Request"))
			if pr.company and self.company and pr.company != self.company:
				frappe.throw(_("Purchase Request must belong to the same company."), title=_("Purchase Request"))
			if pr.docstatus != 1:
				frappe.throw(_("Purchase Request must be submitted."), title=_("Purchase Request"))
		if not self.items:
			frappe.throw(_("Purchase Order requires at least one item."), title=_("Items"))
		self._sync_and_validate_line_items()
		total_qty = 0
		total_amount = 0
		for row in self.items:
			if flt(row.qty) <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx), title=_("Items"))
			if flt(row.rate) < 0:
				frappe.throw(_("Row {0}: Rate cannot be negative.").format(row.idx), title=_("Items"))
			row.amount = flt(row.qty) * flt(row.rate)
			total_qty += flt(row.qty)
			total_amount += flt(row.amount)
		self.total_qty = total_qty
		self.grand_total = total_amount
