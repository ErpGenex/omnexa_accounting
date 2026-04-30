# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from omnexa_accounting.utils.branch import validate_branch_company


class SupplierContract(Document):
	def validate(self):
		validate_branch_company(self)
		if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be before Valid From."), title=_("Supplier Contract"))
		if not self.items:
			frappe.throw(_("Supplier Contract requires at least one item row."), title=_("Items"))

