# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class StockAdjustmentReason(Document):
	def validate(self):
		if not (self.reason_name or "").strip():
			frappe.throw(_("Reason Name is required."), title=_("Stock Adjustment Reason"))

