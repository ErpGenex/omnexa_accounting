# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class SupplierCategory(Document):
	def validate(self):
		name = (self.category_name or "").strip()
		if not name:
			frappe.throw(_("Category Name is required."), title=_("Supplier Category"))
		if (self.category_type or "").strip() not in {"Local", "International", "Contract", "One-time"}:
			frappe.throw(_("Invalid Category Type."), title=_("Supplier Category"))

