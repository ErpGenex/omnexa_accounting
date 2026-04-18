# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, today

from omnexa_accounting.omnexa_accounting.report.cash_activity_summary.cash_activity_summary import execute as cash_exec
from omnexa_accounting.omnexa_accounting.report.payables_aging.payables_aging import execute as pay_exec
from omnexa_accounting.omnexa_accounting.report.receivables_aging.receivables_aging import execute as ar_exec
from omnexa_accounting.omnexa_accounting.report.budget_vs_actual.budget_vs_actual import execute as bva_exec
from omnexa_accounting.omnexa_accounting.report.cash_flow_statement_indirect.cash_flow_statement_indirect import (
	execute as cf_ind_exec,
)
from omnexa_accounting.omnexa_accounting.report.inventory_valuation_gl.inventory_valuation_gl import (
	execute as ivg_exec,
)
from omnexa_accounting.omnexa_accounting.report.cash_flow_simplified.cash_flow_simplified import execute as cfs_exec
from omnexa_accounting.omnexa_accounting.report.cash_flow_statement_structured.cash_flow_statement_structured import (
	execute as cfs_struct_exec,
)
from omnexa_accounting.omnexa_accounting.report.consolidated_trial_balance.consolidated_trial_balance import (
	execute as ctb_exec,
)
from omnexa_accounting.omnexa_accounting.report.inventory_valuation_summary.inventory_valuation_summary import (
	execute as ivs_exec,
)
from omnexa_accounting.omnexa_accounting.report.open_purchase_order_lines.open_purchase_order_lines import execute as opol_exec
from omnexa_accounting.omnexa_accounting.report.purchase_delivery_performance.purchase_delivery_performance import (
	execute as pdp_exec,
)
from omnexa_accounting.omnexa_accounting.report.low_stock.low_stock import execute as low_stock_exec
from omnexa_accounting.omnexa_accounting.report.sales_by_country.sales_by_country import execute as sbc_exec
from omnexa_accounting.omnexa_accounting.report.sales_by_customer.sales_by_customer import execute as sb_customer_exec
from omnexa_accounting.omnexa_accounting.report.sales_by_item.sales_by_item import execute as sbi_exec


class TestExtendedKpiReports(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No company")

	def test_receivables_aging_runs(self):
		out = ar_exec({"company": self.company, "as_of_date": today()})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_payables_aging_runs(self):
		out = pay_exec({"company": self.company, "as_of_date": today()})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_cash_activity_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cash_exec({"company": self.company, "from_date": fd, "to_date": td})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertEqual(len(data), 3)

	def test_sales_by_item_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = sbi_exec({"company": self.company, "from_date": fd, "to_date": td})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_sales_by_country_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = sbc_exec({"company": self.company, "from_date": fd, "to_date": td})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_sales_by_customer_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = sb_customer_exec({"company": self.company, "from_date": fd, "to_date": td})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_low_stock_runs(self):
		out = low_stock_exec({"company": self.company, "below_qty": 0})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_open_po_lines_runs(self):
		out = opol_exec({"company": self.company, "as_of_date": today()})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_cash_flow_simplified_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cfs_exec({"company": self.company, "from_date": fd, "to_date": td})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertEqual(len(data), 5)

	def test_cash_flow_statement_structured_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cfs_struct_exec({"company": self.company, "from_date": fd, "to_date": td})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertEqual(len(data), 7)

	def test_purchase_delivery_performance_runs(self):
		out = pdp_exec({"company": self.company})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_inventory_valuation_summary_runs(self):
		out = ivs_exec({"company": self.company})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_consolidated_trial_balance_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = ctb_exec(
			{"companies": self.company, "from_date": fd, "to_date": td},
		)
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_budget_vs_actual_runs_if_budget_exists(self):
		budget = frappe.db.get_value("Budget", {"docstatus": 1}, "name")
		if not budget:
			self.skipTest("No submitted budget")
		out = bva_exec({"budget": budget})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_cash_flow_indirect_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cf_ind_exec({"company": self.company, "from_date": fd, "to_date": td})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertGreaterEqual(len(data), 3)

	def test_inventory_valuation_gl_runs(self):
		out = ivg_exec({"company": self.company, "as_of_date": today()})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)
