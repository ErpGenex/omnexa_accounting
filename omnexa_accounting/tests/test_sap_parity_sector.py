# Copyright (c) 2026, ErpGenEx
from frappe.tests.utils import FrappeTestCase

from omnexa_accounting.co_parity import preview_co_allocation


class TestSapParityAccounting(FrappeTestCase):
	def test_accounting_co_allocation_preview(self):
		out = preview_co_allocation(
			[
				{"cost_center": "CC-A", "amount": 700
	},
				{"cost_center": "CC-B", "amount": 300
	},
			]
		)
		self.assertEqual(out["total_amount"], 1000)
		self.assertAlmostEqual(out["shares"]["CC-A"], 0.7)
