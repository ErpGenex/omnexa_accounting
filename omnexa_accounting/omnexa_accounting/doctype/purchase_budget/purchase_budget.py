# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_accounting.utils.branch import validate_branch_company


class PurchaseBudget(Document):
	def validate(self):
		validate_branch_company(self)
		if not self.lines:
			frappe.throw(_("Purchase Budget requires at least one line."), title=_("Budget"))

