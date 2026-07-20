# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from omnexa_accounting.utils.demo_workspace_seed import (
	DEFAULT_KEY_SEEDED,
	ensure_demo_workspace_seed,
)


class TestDemoWorkspaceSeed(FrappeTestCase):
	def test_seed_noops_without_feature_flag(self):
		old = frappe.local.conf.get("omnexa_feature_flags")
		frappe.local.conf["omnexa_feature_flags"] = {}
		try:
			ensure_demo_workspace_seed()
		finally:
			if old is None:
				frappe.local.conf.pop("omnexa_feature_flags", None)
			else:
				frappe.local.conf["omnexa_feature_flags"] = old

	def test_seed_skips_when_default_marked(self):
		old = frappe.local.conf.get("omnexa_feature_flags")
		frappe.local.conf["omnexa_feature_flags"] = {"demo_workspace_seed": True
	}
		prev = frappe.db.get_default(DEFAULT_KEY_SEEDED)
		try:
			frappe.db.set_default(DEFAULT_KEY_SEEDED, "1")
			ensure_demo_workspace_seed()
		finally:
			if prev is None:
				frappe.db.set_default(DEFAULT_KEY_SEEDED, None)
			else:
				frappe.db.set_default(DEFAULT_KEY_SEEDED, prev)
			if old is None:
				frappe.local.conf.pop("omnexa_feature_flags", None)
			else:
				frappe.local.conf["omnexa_feature_flags"] = old
