# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe.model.workflow import get_workflow_name
from frappe.tests.utils import FrappeTestCase

from omnexa_accounting.utils.sales_workflow import (
	WORKFLOW_BY_DOCTYPE,
	ensure_sales_chain_workflows,
)


class TestSalesWorkflow(FrappeTestCase):
	def test_ensure_sales_chain_workflows_idempotent(self):
		ensure_sales_chain_workflows()
		ensure_sales_chain_workflows()
		for doctype, wf_name in WORKFLOW_BY_DOCTYPE.items():
			if not frappe.db.exists("DocType", doctype):
				continue
			self.assertEqual(get_workflow_name(doctype), wf_name)
