# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from omnexa_accounting.utils.branch import validate_branch_company
from omnexa_accounting.utils.sales_line_items import validate_sales_line_items
from omnexa_accounting.utils.sales_totals import apply_line_item_amounts_and_totals


class SalesOrder(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Sales Order requires at least one item."), title=_("Items"))
		validate_branch_company(self)
		self._validate_customer_company()
		self._validate_sales_quotation_link()
		if self.expected_delivery_date and getdate(self.expected_delivery_date) < getdate(self.transaction_date):
			frappe.throw(_("Expected Delivery Date cannot be before Order Date."), title=_("Dates"))
		if self.default_tax_rule and frappe.db.get_value("Tax Rule", self.default_tax_rule, "company") != self.company:
			frappe.throw(_("Default Tax Rule must belong to the same company."), title=_("Tax"))
		validate_sales_line_items(self, self.company)
		apply_line_item_amounts_and_totals(self)

	def before_submit(self):
		self._validate_sales_quotation_link(strict=True)

	def on_submit(self):
		if self.sales_quotation:
			frappe.db.set_value(
				"Sales Quotation",
				self.sales_quotation,
				"order_status",
				"Ordered",
				update_modified=False,
			)

	def _validate_customer_company(self):
		if not self.customer:
			return
		c_company = frappe.db.get_value("Customer", self.customer, "company")
		if c_company != self.company:
			frappe.throw(_("Customer belongs to a different company."), title=_("Company"))

	def _validate_sales_quotation_link(self, strict: bool = False):
		if not self.sales_quotation:
			return
		sq = frappe.db.get_value(
			"Sales Quotation",
			self.sales_quotation,
			["company", "customer", "docstatus", "order_status"],
			as_dict=True,
		)
		if not sq:
			frappe.throw(_("Sales Quotation does not exist."), title=_("Sales Quotation"))
		if sq.company != self.company:
			frappe.throw(_("Sales Quotation belongs to a different company."), title=_("Company"))
		if sq.customer != self.customer:
			frappe.throw(_("Customer must match the selected Sales Quotation."), title=_("Customer"))
		if sq.order_status == "Lost":
			frappe.throw(_("Cannot use a Lost Sales Quotation."), title=_("Sales Quotation"))
		if strict and sq.docstatus != 1:
			frappe.throw(_("Sales Quotation must be submitted before Sales Order submit."), title=_("Sales Quotation"))
