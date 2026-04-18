# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, random_string, today

from omnexa_accounting.omnexa_accounting.report.budget_vs_actual.budget_vs_actual import execute as bva_exec


class TestBudgetPurchaseRequest(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No company")

	def _expense_gl(self):
		num = f"8{random_string(6)}"
		g = frappe.new_doc("GL Account")
		g.company = self.company
		g.account_number = num
		g.account_name = f"Test Expense {num}"
		g.is_group = 0
		g.account_type = "Expense"
		g.pl_bucket = "Operating Expense"
		g.insert(ignore_permissions=True)
		self.addCleanup(lambda n=g.name: frappe.delete_doc("GL Account", n, force=1, ignore_permissions=True))
		return g.name

	def _supplier(self):
		s = frappe.new_doc("Supplier")
		s.company = self.company
		s.supplier_name = f"Sup-{random_string(5)}"
		s.insert(ignore_permissions=True)
		self.addCleanup(lambda n=s.name: frappe.delete_doc("Supplier", n, force=1, ignore_permissions=True))
		return s.name

	def test_budget_vs_actual_runs_after_submit(self):
		acc = self._expense_gl()
		bud = frappe.new_doc("Budget")
		bud.company = self.company
		bud.from_date = add_months(today(), -1)
		bud.to_date = today()
		bud.append("budget_lines", {"gl_account": acc, "budget_amount": 1000})
		bud.insert(ignore_permissions=True)
		bud.submit()
		self.addCleanup(
			lambda: self._cancel_and_delete("Budget", bud.name),
		)
		out = bva_exec({"budget": bud.name})
		self.assertTrue(out[0])
		self.assertEqual(len(out[1]), 1)
		self.assertEqual(out[1][0]["gl_account"], acc)

	def test_po_accepts_submitted_purchase_request(self):
		pr = frappe.new_doc("Purchase Request")
		pr.company = self.company
		pr.required_by = today()
		pr.append("items", {"item_code": f"IT-{random_string(4)}", "qty": 2})
		pr.insert(ignore_permissions=True)
		pr.submit()
		self.addCleanup(lambda: self._cancel_and_delete("Purchase Request", pr.name))

		po = frappe.new_doc("Purchase Order")
		po.company = self.company
		po.supplier = self._supplier()
		po.posting_date = today()
		po.purchase_request = pr.name
		po.append("items", {"item_code": "LINE-1", "qty": 1, "rate": 10})
		po.insert(ignore_permissions=True)
		po.submit()
		self.addCleanup(lambda: self._cancel_and_delete("Purchase Order", po.name))

	def test_po_rejects_draft_purchase_request(self):
		pr = frappe.new_doc("Purchase Request")
		pr.company = self.company
		pr.required_by = today()
		pr.append("items", {"item_code": f"IT-{random_string(4)}", "qty": 1})
		pr.insert(ignore_permissions=True)
		self.addCleanup(lambda: frappe.delete_doc("Purchase Request", pr.name, force=1, ignore_permissions=True))

		po = frappe.new_doc("Purchase Order")
		po.company = self.company
		po.supplier = self._supplier()
		po.posting_date = today()
		po.purchase_request = pr.name
		po.append("items", {"item_code": "LINE-1", "qty": 1, "rate": 10})
		with self.assertRaises(frappe.ValidationError):
			po.insert(ignore_permissions=True)

	def _cancel_and_delete(self, doctype: str, name: str):
		if not frappe.db.exists(doctype, name):
			return
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
