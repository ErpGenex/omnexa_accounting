# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe


def after_install():
	ensure_accounting_roles()


def after_migrate():
	ensure_accounting_roles()
	from omnexa_accounting.utils.bank_reconciliation_workflow import ensure_bank_reconciliation_workflow
	from omnexa_accounting.utils.demo_workspace_seed import ensure_demo_workspace_seed
	from omnexa_accounting.utils.inventory_workflow import ensure_inventory_workflows
	from omnexa_accounting.utils.ledger_workflow import ensure_ledger_workflows
	from omnexa_accounting.utils.procurement_workflow import ensure_procurement_chain_workflows
	from omnexa_accounting.utils.sales_workflow import ensure_sales_chain_workflows

	ensure_sales_chain_workflows()
	ensure_procurement_chain_workflows()
	ensure_ledger_workflows()
	ensure_inventory_workflows()
	ensure_bank_reconciliation_workflow()
	ensure_demo_workspace_seed()


def ensure_accounting_roles():
	for role_name in ("Accounts Manager", "Accounts User"):
		if frappe.db.exists("Role", role_name):
			continue
		doc = frappe.new_doc("Role")
		doc.role_name = role_name
		doc.desk_access = 1
		doc.is_custom = 1
		doc.insert(ignore_permissions=True)
