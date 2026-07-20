# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, today

from omnexa_accounting.omnexa_accounting.report.financial_kpi_summary.financial_kpi_summary import (
	execute as execute_financial_kpi,
)
from omnexa_accounting.omnexa_accounting.report.receivables_and_dso.receivables_and_dso import (
	execute as execute_receivables_dso,
)


class TestFinancialKpiReports(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No company")

	def test_receivables_and_dso_runs(self):
		out = execute_receivables_dso(
			{"company": self.company, "as_of_date": today(), "period_days": 90
	}
		)
		columns, data, *_rest = out
		self.assertTrue(columns)
		self.assertIsInstance(data, list)

	def test_financial_kpi_summary_runs(self):
		td = today()
		fd = add_months(td, -1)
		out = execute_financial_kpi({"company": self.company, "from_date": fd, "to_date": td
	})
		columns, data, *_rest = out
		self.assertTrue(columns)
		self.assertEqual(len(data), 11)
