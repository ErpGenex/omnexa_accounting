# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from omnexa_accounting.utils.branch import validate_branch_company
from omnexa_accounting.utils.sales_line_items import validate_sales_line_items
from omnexa_accounting.utils.sales_totals import apply_line_item_amounts_and_totals


class SalesQuotation(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Sales Quotation requires at least one item."), title=_("Items"))
		validate_branch_company(self)
		self._validate_customer_company()
		if self.valid_till and getdate(self.valid_till) < getdate(self.transaction_date):
			frappe.throw(_("Valid Till cannot be before Quotation Date."), title=_("Dates"))
		if self.default_tax_rule and frappe.db.get_value("Tax Rule", self.default_tax_rule, "company") != self.company:
			frappe.throw(_("Default Tax Rule must belong to the same company."), title=_("Tax"))
		validate_sales_line_items(self, self.company)
		apply_line_item_amounts_and_totals(self)

	def before_submit(self):
		if self.order_status == "Lost":
			frappe.throw(_("Cannot submit a quotation marked as Lost."), title=_("Status"))

	def _validate_customer_company(self):
		if not self.customer:
			return
		c_company = frappe.db.get_value("Customer", self.customer, "company")
		if c_company != self.company:
			frappe.throw(_("Customer belongs to a different company."), title=_("Company"))
