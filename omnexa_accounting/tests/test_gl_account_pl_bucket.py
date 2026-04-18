# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string


class TestGLAccountPLBucket(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No company")

	def test_pl_bucket_invalid_for_asset(self):
		doc = frappe.new_doc("GL Account")
		doc.company = self.company
		doc.account_number = f"T{random_string(6)}"
		doc.account_name = "Test Asset PL"
		doc.is_group = 0
		doc.account_type = "Asset"
		doc.pl_bucket = "COGS"
		with self.assertRaises(ValidationError):
			doc.insert(ignore_permissions=True)

	def test_income_bucket_accepts_revenue(self):
		doc = frappe.new_doc("GL Account")
		doc.company = self.company
		doc.account_number = f"T{random_string(6)}"
		doc.account_name = "Test Rev PL"
		doc.is_group = 0
		doc.account_type = "Income"
		doc.pl_bucket = "Revenue"
		doc.insert(ignore_permissions=True)
		self.addCleanup(lambda: frappe.delete_doc("GL Account", doc.name, force=1, ignore_permissions=True))
