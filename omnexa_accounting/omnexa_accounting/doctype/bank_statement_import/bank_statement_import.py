# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from omnexa_accounting.utils.branch import validate_branch_company


class BankStatementImport(Document):
	def validate(self):
		validate_branch_company(self)
		if not self.lines:
			frappe.throw(_("At least one bank statement line is required."), title=_("Bank Statement"))
		ba_company = frappe.db.get_value("Bank Account", self.bank_account, "company")
		if ba_company and self.company and ba_company != self.company:
			frappe.throw(_("Bank Account belongs to a different company."), title=_("Company"))
		for row in self.lines:
			row.company = self.company

