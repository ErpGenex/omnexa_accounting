# Copyright (c) 2026, Omnexa and contributors
# License: MIT

from frappe.tests.utils import FrappeTestCase

from omnexa_accounting.utils.global_erp_strict_validations import _company_chain_flags


class TestGlobalErpStrictValidations(FrappeTestCase):
	def test_strict_off_disables_all(self):
		flags = _company_chain_flags(None)
		self.assertFalse(flags["strict"])
		self.assertFalse(flags["require_delivery_note_stock"])
