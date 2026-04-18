# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from collections import defaultdict
from typing import Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_accounting.utils.branch import validate_branch_company


def _sales_chain_line_key(item: Optional[str], item_code: Optional[str]) -> str:
	if item:
		return f"i:{item}"
	return f"c:{(item_code or '').strip()}"


class DeliveryNote(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Delivery Note requires at least one item."), title=_("Items"))
		validate_branch_company(self)
		self._validate_customer_company()
		self._validate_sales_order_and_warehouse()
		total_qty = 0.0
		total_amt = 0.0
		for row in self.items:
			if flt(row.qty) <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx), title=_("Items"))
			if flt(row.rate) < 0:
				frappe.throw(_("Row {0}: Rate cannot be negative.").format(row.idx), title=_("Items"))
			row.amount = flt(row.qty) * flt(row.rate)
			total_qty += flt(row.qty)
			total_amt += flt(row.amount)
			if row.item:
				it = frappe.get_cached_doc("Item", row.item)
				if it.company != self.company:
					frappe.throw(_("Row {0}: Item belongs to a different company.").format(row.idx), title=_("Item"))
				if not row.item_code:
					row.item_code = it.item_code
				elif row.item_code != it.item_code:
					frappe.throw(
						_("Row {0}: Item Code must match the selected Item.").format(row.idx),
						title=_("Item"),
					)
		self.total_qty = total_qty
		self.grand_total = total_amt
		self._validate_qty_against_sales_order()

	def before_submit(self):
		so = frappe.db.get_value(
			"Sales Order",
			self.sales_order,
			["docstatus", "customer", "company"],
			as_dict=True,
		)
		if not so or so.docstatus != 1:
			frappe.throw(_("Sales Order must exist and be submitted."), title=_("Sales Order"))
		if so.customer != self.customer or so.company != self.company:
			frappe.throw(_("Customer and Company must match the Sales Order."), title=_("Sales Order"))

	def _validate_customer_company(self):
		if not self.customer:
			return
		c_company = frappe.db.get_value("Customer", self.customer, "company")
		if c_company != self.company:
			frappe.throw(_("Customer belongs to a different company."), title=_("Company"))

	def _validate_sales_order_and_warehouse(self):
		if not self.sales_order:
			frappe.throw(_("Sales Order is required."), title=_("Sales Order"))
		so = frappe.db.get_value(
			"Sales Order",
			self.sales_order,
			["customer", "company"],
			as_dict=True,
		)
		if not so:
			frappe.throw(_("Sales Order does not exist."), title=_("Sales Order"))
		if so.customer != self.customer:
			frappe.throw(_("Customer must match the Sales Order."), title=_("Customer"))
		if so.company != self.company:
			frappe.throw(_("Company must match the Sales Order."), title=_("Company"))
		if not self.warehouse:
			frappe.throw(_("Target Warehouse is required."), title=_("Warehouse"))
		w_company = frappe.db.get_value("Warehouse", self.warehouse, "company")
		if w_company != self.company:
			frappe.throw(_("Warehouse belongs to a different company."), title=_("Warehouse"))

	def _validate_qty_against_sales_order(self):
		"""Cumulative delivered qty per item (or item code) cannot exceed Sales Order line qty."""
		if not self.sales_order:
			return
		so = frappe.get_doc("Sales Order", self.sales_order)
		ordered: dict[str, float] = defaultdict(float)
		for r in so.items or []:
			ordered[_sales_chain_line_key(getattr(r, "item", None), getattr(r, "item_code", None))] += flt(r.qty)

		conds = ["dn.sales_order = %(so)s", "dn.docstatus = 1"]
		params = {"so": self.sales_order}
		if getattr(self, "name", None):
			conds.append("dn.name != %(cur)s")
			params["cur"] = self.name
		delivered_other: dict[str, float] = defaultdict(float)
		rows = frappe.db.sql(
			f"""
			SELECT dni.item AS item, dni.item_code AS item_code, SUM(dni.qty) AS qty
			FROM `tabDelivery Note` dn
			INNER JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
			WHERE {" AND ".join(conds)}
			GROUP BY dni.item, dni.item_code
			""",
			params,
			as_dict=True,
		)
		for row in rows or []:
			delivered_other[_sales_chain_line_key(row.get("item"), row.get("item_code"))] += flt(row.qty)

		this_dn: dict[str, float] = defaultdict(float)
		for line in self.items or []:
			this_dn[_sales_chain_line_key(line.item, line.item_code)] += flt(line.qty)

		for key, add_qty in this_dn.items():
			limit = flt(ordered.get(key, 0))
			if limit <= 0:
				frappe.throw(
					_("Item on this delivery note does not match any line on the Sales Order ({0}).").format(key),
					title=_("Delivery Note"),
				)
			prev = flt(delivered_other.get(key, 0))
			if prev + add_qty - limit > 1e-6:
				frappe.throw(
					_("Delivered quantity exceeds remaining quantity on Sales Order for {0}.").format(key),
					title=_("Delivery Note"),
				)

