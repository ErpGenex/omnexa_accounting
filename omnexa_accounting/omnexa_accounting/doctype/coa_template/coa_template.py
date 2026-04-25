# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class COATemplate(Document):
	def validate(self):
		seen = set()
		for row in self.accounts or []:
			code = (row.account_number or "").strip()
			if not code:
				frappe.throw(_("COA Template Line: Account Number is required."), title=_("COA Template"))
			if code in seen:
				frappe.throw(_("Duplicate Account Number in template: {0}").format(code), title=_("COA Template"))
			seen.add(code)

