# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.workflow import get_workflow_name
from frappe.tests.utils import FrappeTestCase

from omnexa_accounting.utils.inventory_workflow import (
	WORKFLOW_BY_DOCTYPE,
	ensure_inventory_workflows,
)


class TestInventoryWorkflow(FrappeTestCase):
	def test_ensure_inventory_workflows_idempotent(self):
		ensure_inventory_workflows()
		ensure_inventory_workflows()
		for doctype, wf_name in WORKFLOW_BY_DOCTYPE.items():
			if not frappe.db.exists("DocType", doctype):
				continue
			self.assertEqual(get_workflow_name(doctype), wf_name)
