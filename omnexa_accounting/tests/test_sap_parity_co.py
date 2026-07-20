# Copyright (c) 2026, ErpGenEx
from frappe.tests.utils import FrappeTestCase

from omnexa_accounting.co_parity import preview_co_allocation


class TestSapParityCo(FrappeTestCase):
	def test_co_allocation_shares(self):
		out = preview_co_allocation(
			[
				{"cost_center": "CC-A", "amount": 600},
				{"cost_center": "CC-B", "amount": 400},
			]
		)
		self.assertEqual(out["total_amount"], 1000)
		self.assertEqual(out["shares"]["CC-A"], 0.6)
