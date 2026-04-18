# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string, today


class TestSalesChain(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No company")

	def _ensure_uom(self):
		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert(ignore_permissions=True)

	def _item(self, prefix: str):
		self._ensure_uom()
		code = f"{prefix}-{random_string(4)}"
		it = frappe.new_doc("Item")
		it.item_code = code
		it.item_name = code
		it.company = self.company
		it.stock_uom = "Nos"
		it.insert(ignore_permissions=True)
		return it

	def _customer(self, prefix: str):
		name = f"{prefix}-{random_string(4)}"
		c = frappe.new_doc("Customer")
		c.company = self.company
		c.customer_name = name
		c.insert(ignore_permissions=True)
		return c

	def _leaf_gl(self, label: str):
		num = f"61{random_string(5)}"
		g = frappe.new_doc("GL Account")
		g.company = self.company
		g.account_number = num
		g.account_name = label
		g.is_group = 0
		g.insert(ignore_permissions=True)
		return g.name

	def _currency(self):
		return frappe.db.get_value("Company", self.company, "default_currency") or "EGP"

	def _warehouse(self, prefix: str):
		code = f"{prefix}{random_string(3)}"
		w = frappe.new_doc("Warehouse")
		w.company = self.company
		w.warehouse_name = f"WH-{code}"
		w.warehouse_code = code
		w.insert(ignore_permissions=True)
		return w.name

	def test_quotation_order_delivery_invoice_chain(self):
		cust = self._customer("Chain")
		it = self._item("CHAIN")
		leaf = self._leaf_gl("Rev Chain")
		cur = self._currency()
		sq = frappe.new_doc("Sales Quotation")
		sq.company = self.company
		sq.customer = cust.name
		sq.transaction_date = today()
		sq.currency = cur
		sq.append("items", {"item": it.name, "qty": 2, "rate": 5, "income_account": leaf})
		sq.insert(ignore_permissions=True)
		sq.submit()
		so = frappe.new_doc("Sales Order")
		so.company = self.company
		so.customer = cust.name
		so.sales_quotation = sq.name
		so.transaction_date = today()
		so.currency = cur
		so.append("items", {"item": it.name, "qty": 2, "rate": 5, "income_account": leaf})
		so.insert(ignore_permissions=True)
		so.submit()
		sq.reload()
		self.assertEqual(sq.order_status, "Ordered")
		wh = self._warehouse("CH")
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.customer = cust.name
		dn.sales_order = so.name
		dn.warehouse = wh
		dn.transaction_date = today()
		dn.append("items", {"item": it.name, "qty": 2, "rate": 5})
		dn.insert(ignore_permissions=True)
		dn.submit()
		si = frappe.new_doc("Sales Invoice")
		si.company = self.company
		si.customer = cust.name
		si.posting_date = today()
		si.currency = cur
		si.sales_quotation = sq.name
		si.sales_order = so.name
		si.delivery_note = dn.name
		si.append("items", {"item": it.name, "qty": 2, "rate": 5, "income_account": leaf})
		si.insert(ignore_permissions=True)
		si.submit()

	def test_invoice_autofills_sales_order_from_delivery_note(self):
		cust = self._customer("Auto")
		it = self._item("AUTO")
		leaf = self._leaf_gl("Rev Auto")
		cur = self._currency()
		so = frappe.new_doc("Sales Order")
		so.company = self.company
		so.customer = cust.name
		so.transaction_date = today()
		so.currency = cur
		so.append("items", {"item": it.name, "qty": 1, "rate": 10, "income_account": leaf})
		so.insert(ignore_permissions=True)
		so.submit()
		wh = self._warehouse("AU")
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.customer = cust.name
		dn.sales_order = so.name
		dn.warehouse = wh
		dn.transaction_date = today()
		dn.append("items", {"item": it.name, "qty": 1, "rate": 10})
		dn.insert(ignore_permissions=True)
		dn.submit()
		si = frappe.new_doc("Sales Invoice")
		si.company = self.company
		si.customer = cust.name
		si.posting_date = today()
		si.currency = cur
		si.delivery_note = dn.name
		si.append("items", {"item": it.name, "qty": 1, "rate": 10, "income_account": leaf})
		si.insert(ignore_permissions=True)
		self.assertEqual(si.sales_order, so.name)

	def test_delivery_note_blocks_qty_over_sales_order(self):
		cust = self._customer("Over")
		it = self._item("OVER")
		leaf = self._leaf_gl("Rev Over")
		cur = self._currency()
		so = frappe.new_doc("Sales Order")
		so.company = self.company
		so.customer = cust.name
		so.transaction_date = today()
		so.currency = cur
		so.append("items", {"item": it.name, "qty": 2, "rate": 1, "income_account": leaf})
		so.insert(ignore_permissions=True)
		so.submit()
		wh = self._warehouse("OV")
		dn1 = frappe.new_doc("Delivery Note")
		dn1.company = self.company
		dn1.customer = cust.name
		dn1.sales_order = so.name
		dn1.warehouse = wh
		dn1.transaction_date = today()
		dn1.append("items", {"item": it.name, "qty": 2, "rate": 1})
		dn1.insert(ignore_permissions=True)
		dn1.submit()
		dn2 = frappe.new_doc("Delivery Note")
		dn2.company = self.company
		dn2.customer = cust.name
		dn2.sales_order = so.name
		dn2.warehouse = wh
		dn2.transaction_date = today()
		dn2.append("items", {"item": it.name, "qty": 1, "rate": 1})
		with self.assertRaises(ValidationError):
			dn2.insert(ignore_permissions=True)
