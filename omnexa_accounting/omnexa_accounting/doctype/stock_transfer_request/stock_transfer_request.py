# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_accounting.utils.branch import validate_branch_company


class StockTransferRequest(Document):
	def validate(self):
		validate_branch_company(self)
		if self.from_warehouse and self.to_warehouse and self.from_warehouse == self.to_warehouse:
			frappe.throw(_("From Warehouse and To Warehouse cannot be the same."), title=_("Transfer"))
		if not self.items:
			frappe.throw(_("At least one transfer row is required."), title=_("Transfer"))
		for row in self.items or []:
			if not row.item:
				frappe.throw(_("Row {0}: Item is required.").format(row.idx), title=_("Items"))
			if flt(row.qty) <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx), title=_("Items"))
			if not row.item_code:
				row.item_code = frappe.db.get_value("Item", row.item, "item_code")
			if not row.uom:
				row.uom = frappe.db.get_value("Item", row.item, "stock_uom")

	def on_submit(self):
		self.db_set("status", "Approved", update_modified=False)

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=False)

