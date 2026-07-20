# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FinancePostingRule(Document):
	def validate(self):
		if not (self.rule_name or "").strip():
			frappe.throw(_("Rule Name is required."), title=_("Finance Posting Rule"))
		if flt(self.max_amount) and flt(self.max_amount) < flt(self.min_amount):
			frappe.throw(_("Max Amount cannot be less than Min Amount."), title=_("Finance Posting Rule"))

