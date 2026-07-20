# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from omnexa_accounting.utils.supplier_codes import assign_supplier_code_if_missing


class Supplier(Document):
	def before_validate(self):
		assign_supplier_code_if_missing(self)

	def validate(self):
		if cint(self.credit_days) < 0:
			frappe.throw(_("Credit Days cannot be negative."), title=_("Payment Terms"))
		existing = frappe.db.get_value(
			"Supplier",
			{"company": self.company, "supplier_name": self.supplier_name
	},
			"name",
		)
		if existing and (not self.name or existing != self.name):
			frappe.throw(
				_("Supplier Name must be unique per company."),
				title=_("Duplicate"),
			)
		if self.supplier_code:
			existing_code = frappe.db.get_value(
				"Supplier",
				{"company": self.company, "supplier_code": self.supplier_code
	},
				"name",
			)
			if existing_code and existing_code != self.name:
				frappe.throw(
					_("Supplier Code must be unique per company."),
					title=_("Duplicate"),
				)
