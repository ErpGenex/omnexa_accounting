# Copyright (c) 2026, Omnexa and contributors
# License: MIT

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from omnexa_accounting.utils.vat_accounts import resolve_vat_accounts


class TestVatAccounts(FrappeTestCase):
	def test_resolve_vat_accounts_structure(self):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("No company on site")
		out = resolve_vat_accounts(company)
		self.assertEqual(out["company"], company)
		self.assertIn("input_source", out)
		self.assertIn("output_source", out)
