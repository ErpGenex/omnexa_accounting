# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string


class TestGLAccountEnterprise(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not self.company:
			self.skipTest("No company")

	def _new_account(self, **kwargs):
		doc = frappe.new_doc("GL Account")
		doc.company = self.company
		doc.account_name = kwargs.pop("account_name", f"Test {random_string(6)}")
		doc.account_class = kwargs.pop("account_class", "Asset")
		doc.account_type = kwargs.pop("account_type", doc.account_class)
		doc.is_group = kwargs.pop("is_group", 0)
		for k, v in kwargs.items():
			setattr(doc, k, v)
		doc.insert(ignore_permissions=True)
		self.addCleanup(lambda: frappe.delete_doc("GL Account", doc.name, force=1, ignore_permissions=True))
		return doc

	def test_auto_number_generation(self):
		doc = self._new_account(account_name="Auto Num Account")
		self.assertTrue(doc.account_number)

	def test_invalid_parent_class_blocked(self):
		parent = self._new_account(account_name="Parent Liability", account_class="Liability", is_group=1, posting_type="Header")
		with self.assertRaises(ValidationError):
			self._new_account(
				account_name="Child Asset Under Liability",
				account_class="Asset",
				parent_account=parent.name,
				posting_type="Posting",
			)

	def test_control_account_requires_reconcilable(self):
		with self.assertRaises(ValidationError):
			self._new_account(account_name="Control Without Recon", posting_type="Control Account", is_reconcilable=0)
