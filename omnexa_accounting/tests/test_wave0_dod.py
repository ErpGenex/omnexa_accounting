# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Wave 0 Definition-of-Done smoke — omnexa_accounting."""

import time

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from omnexa_accounting.omnexa_accounting.report.trial_balance.trial_balance import execute as trial_balance_exec
from omnexa_accounting.utils.ledger_workflow import ensure_ledger_workflows
from omnexa_core.omnexa_core.branch_access import permission_query_conditions_for_branch_field
from omnexa_core.tests.test_helpers import clear_privileged_view_context


class TestWave0DoDAccounting(FrappeTestCase):
	def setUp(self):
		super().setUp()
		clear_privileged_view_context()
		ensure_ledger_workflows()
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No company")

	def _gl(self, number: str, name: str):
		if frappe.db.exists("GL Account", {"company": self.company, "account_number": number}):
			return frappe.db.get_value("GL Account", {"company": self.company, "account_number": number}, "name")
		d = frappe.new_doc("GL Account")
		d.company = self.company
		d.account_number = number
		d.account_name = name
		d.is_group = 0
		d.account_class = "Asset"
		d.account_type = "Asset"
		d.insert(ignore_permissions=True)
		return d.name

	def test_journal_entry_balanced_submit(self):
		leaf = self._gl(f"W0{frappe.generate_hash(length=4)}", "W0 Cash")
		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.posting_date = today()
		je.append("accounts", {"account": leaf, "debit": 50, "credit": 0})
		je.append("accounts", {"account": leaf, "debit": 0, "credit": 50})
		je.insert(ignore_permissions=True)
		je.submit()
		self.assertEqual(je.docstatus, 1)

	def test_sales_invoice_submit_and_trial_balance(self):
		if not frappe.db.exists("DocType", "Sales Invoice"):
			self.skipTest("Sales Invoice missing")
		cust = frappe.new_doc("Customer")
		cust.company = self.company
		cust.customer_name = f"W0 Cust {frappe.generate_hash(length=4)}"
		cust.insert(ignore_permissions=True)
		rev = self._gl(f"R{frappe.generate_hash(length=4)}", "W0 Revenue")
		frappe.db.set_value("GL Account", rev, "account_class", "Revenue")
		frappe.db.set_value("GL Account", rev, "account_type", "Revenue")
		si = frappe.new_doc("Sales Invoice")
		si.company = self.company
		si.customer = cust.name
		si.posting_date = today()
		si.append("items", {"item_code": "line", "qty": 1, "rate": 100, "income_account": rev})
		si.insert(ignore_permissions=True)
		si.submit()

		start = time.perf_counter()
		out = trial_balance_exec({"company": self.company, "from_date": today(), "to_date": today()})
		elapsed = time.perf_counter() - start
		self.assertTrue(out[0])
		self.assertLess(elapsed, 5.0, f"Trial Balance p95 gate: {elapsed:.2f}s")

	def test_branch_permission_query_on_journal_entry(self):
		frappe.set_user("Administrator")
		cond = permission_query_conditions_for_branch_field("Journal Entry")
		self.assertEqual(cond, "")

	def test_financial_report_xlsx_module(self):
		from omnexa_accounting.utils import financial_report_xlsx

		self.assertTrue(callable(getattr(financial_report_xlsx, "build_financial_report_xlsx", None)))
