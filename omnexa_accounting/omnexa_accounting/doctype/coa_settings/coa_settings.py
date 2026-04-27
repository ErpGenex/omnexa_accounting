# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CoASettings(Document):
	def validate(self):
		self._validate_masks()

	def _validate_masks(self):
		for fieldname in ("asset_mask", "liability_mask", "equity_mask", "revenue_mask", "expense_mask"):
			mask = (self.get(fieldname) or "").strip()
			if not mask:
				frappe.throw(_("Account number mask is required: {0}").format(fieldname))
			if "x" not in mask and "X" not in mask:
				frappe.throw(_("Mask {0} must contain at least one x placeholder.").format(mask))
