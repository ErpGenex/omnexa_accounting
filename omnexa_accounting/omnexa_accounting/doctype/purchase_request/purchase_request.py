# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_accounting.utils.branch import validate_branch_company


class PurchaseRequest(Document):
	def validate(self):
		validate_branch_company(self)
		if not self.items:
			frappe.throw(_("Add at least one line item."), title=_("Items"))
		total = 0
		for row in self.items:
			if flt(row.qty) <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx), title=_("Items"))
			total += flt(row.qty)
		self.total_qty = total
