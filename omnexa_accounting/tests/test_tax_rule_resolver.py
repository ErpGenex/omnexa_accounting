# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, today

from omnexa_accounting.utils.tax_rule_resolver import apply_invoice_tax_rule_defaults, resolve_default_tax_rule


class TestTaxRuleResolver(FrappeTestCase):
	def test_resolve_and_apply(self):
		co = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
		if not co or not frappe.db.exists("DocType", "Tax Rule"):
			return
		tax_gl = frappe.db.get_value(
			"GL Account", {"company": co, "is_group": 0}, "name", order_by="creation asc"
		)
		if not tax_gl:
			return
		existing = resolve_default_tax_rule(co, today())
		if existing:
			rule_name = existing
			cleanup = False
		else:
			rule = frappe.get_doc(
				{
					"doctype": "Tax Rule",
					"title": f"Test VAT Resolver {frappe.generate_hash(length=6)}",
					"company": co,
					"valid_from": add_to_date(today(), days=-30),
					"valid_to": add_to_date(today(), days=365),
					"tax_type": "standard",
					"rate": 14,
					"account_head": tax_gl,
				}
			).insert(ignore_permissions=True)
			rule_name = rule.name
			cleanup = True
		try:
			found = resolve_default_tax_rule(co, today())
			self.assertTrue(found)
			doc = frappe._dict(
				doctype="Sales Invoice",
				company=co,
				posting_date=today(),
				items=[frappe._dict(idx=1, qty=1, rate=100)],
			)
			doc.meta = frappe.get_meta("Sales Invoice")
			self.assertTrue(apply_invoice_tax_rule_defaults(doc))
			self.assertEqual(doc.default_tax_rule, rule_name)
		finally:
			if cleanup:
				frappe.delete_doc("Tax Rule", rule_name, force=1, ignore_permissions=True)
