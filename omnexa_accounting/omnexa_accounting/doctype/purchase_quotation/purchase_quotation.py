# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from omnexa_accounting.utils.branch import validate_branch_company


class PurchaseQuotation(Document):
	def validate(self):
		validate_branch_company(self)
		if self.valid_till and self.quotation_date and getdate(self.valid_till) < getdate(self.quotation_date):
			frappe.throw(_("Valid Till cannot be before Quotation Date."), title=_("Purchase Quotation"))
		if not self.items:
			frappe.throw(_("Purchase Quotation requires at least one item row."), title=_("Items"))
		total_qty = 0.0
		total_amount = 0.0
		for row in self.items or []:
			if flt(row.qty) <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx), title=_("Items"))
			if flt(row.rate) < 0:
				frappe.throw(_("Row {0}: Rate cannot be negative.").format(row.idx), title=_("Items"))
			disc = flt(row.get("discount_percentage")) if hasattr(row, "get") else 0.0
			disc = max(0.0, min(100.0, disc))
			row.amount = flt(row.qty) * flt(row.rate) * (1.0 - (disc / 100.0))
			total_qty += flt(row.qty)
			total_amount += flt(row.amount)
		self.total_qty = total_qty
		self.grand_total = total_amount

