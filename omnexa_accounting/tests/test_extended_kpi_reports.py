# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, today

from omnexa_accounting.omnexa_accounting.report.access_control_summary.access_control_summary import (
	execute as acs_exec,
)
from omnexa_accounting.omnexa_accounting.report.cash_activity_summary.cash_activity_summary import execute as cash_exec
from omnexa_accounting.omnexa_accounting.report.configuration_change_summary.configuration_change_summary import (
	execute as ccs_exec,
)
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
from omnexa_accounting.omnexa_accounting.report.expiry_report.expiry_report import execute as expiry_exec
from omnexa_accounting.omnexa_accounting.report.inventory_valuation_summary.inventory_valuation_summary import (
	execute as ivs_exec,
)
from omnexa_accounting.omnexa_accounting.report.open_purchase_order_lines.open_purchase_order_lines import execute as opol_exec
from omnexa_accounting.omnexa_accounting.report.purchase_delivery_performance.purchase_delivery_performance import (
	execute as pdp_exec,
)
from omnexa_accounting.omnexa_accounting.report.governance_audit_trail.governance_audit_trail import (
	execute as audit_trail_exec,
)
from omnexa_accounting.omnexa_accounting.report.user_activity_summary.user_activity_summary import (
	execute as user_activity_summary_exec,
)
from omnexa_accounting.omnexa_accounting.report.low_stock.low_stock import execute as low_stock_exec
from omnexa_accounting.omnexa_accounting.report.purchase_cost_analysis.purchase_cost_analysis import (
	execute as pca_exec,
)
from omnexa_accounting.omnexa_accounting.report.revenue_analysis.revenue_analysis import execute as rev_exec
from omnexa_accounting.omnexa_accounting.report.sales_performance.sales_performance import (
	execute as sp_exec,
)
from omnexa_accounting.omnexa_accounting.report.stock_summary.stock_summary import execute as stock_sum_exec
from omnexa_accounting.omnexa_accounting.report.workflow_execution_summary.workflow_execution_summary import (
	execute as wes_exec,
)
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
		out = ar_exec({"company": self.company, "as_of_date": today()
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_payables_aging_runs(self):
		out = pay_exec({"company": self.company, "as_of_date": today()
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_cash_activity_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cash_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertEqual(len(data), 3)

	def test_sales_by_item_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = sbi_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_sales_by_country_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = sbc_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_sales_by_customer_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = sb_customer_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_low_stock_runs(self):
		out = low_stock_exec({"company": self.company, "below_qty": 0
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_open_po_lines_runs(self):
		out = opol_exec({"company": self.company, "as_of_date": today()
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_cash_flow_simplified_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cfs_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertEqual(len(data), 5)

	def test_cash_flow_statement_structured_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cfs_struct_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertEqual(len(data), 8)

	def test_purchase_delivery_performance_runs(self):
		out = pdp_exec({"company": self.company
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_inventory_valuation_summary_runs(self):
		out = ivs_exec({"company": self.company
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_consolidated_trial_balance_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = ctb_exec(
			{"companies": self.company, "from_date": fd, "to_date": td
	},
		)
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_budget_vs_actual_runs_if_budget_exists(self):
		budget = frappe.db.get_value("Budget", {"docstatus": 1
	}, "name")
		if not budget:
			self.skipTest("No submitted budget")
		out = bva_exec({"budget": budget
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_cash_flow_indirect_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = cf_ind_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		cols, data, *_ = out
		self.assertTrue(cols)
		self.assertGreaterEqual(len(data), 3)

	def test_inventory_valuation_gl_runs(self):
		out = ivg_exec({"company": self.company, "as_of_date": today()
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_revenue_analysis_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = rev_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_sales_performance_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = sp_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_purchase_cost_analysis_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = pca_exec({"company": self.company, "from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_stock_summary_runs(self):
		out = stock_sum_exec({"company": self.company
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_user_activity_summary_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = user_activity_summary_exec({"from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_governance_audit_trail_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = audit_trail_exec({"from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_expiry_report_runs(self):
		out = expiry_exec({"company": self.company
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_access_control_summary_runs(self):
		out = acs_exec({})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_workflow_execution_summary_runs(self):
		out = wes_exec({})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)

	def test_configuration_change_summary_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = ccs_exec({"from_date": fd, "to_date": td
	})
		self.assertTrue(out[0])
		self.assertIsInstance(out[1], list)
