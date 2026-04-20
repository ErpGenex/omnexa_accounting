# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe


def after_install():
	ensure_accounting_roles()


def after_migrate():
	ensure_accounting_roles()
	ensure_journal_entry_entry_type_not_duplicate_custom_field()
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


def ensure_journal_entry_entry_type_not_duplicate_custom_field():
	"""`entry_type` is a core Journal Entry field; remove legacy Custom Field if present."""
	try:
		name = frappe.db.get_value(
			"Custom Field", {"dt": "Journal Entry", "fieldname": "entry_type"}, "name"
		)
		if name:
			frappe.delete_doc("Custom Field", name, force=True)
			frappe.db.commit()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(), "Omnexa Accounting: remove duplicate Journal Entry entry_type CF"
		)


def ensure_accounting_roles():
	for role_name in ("Accounts Manager", "Accounts User"):
		if frappe.db.exists("Role", role_name):
			continue
		doc = frappe.new_doc("Role")
		doc.role_name = role_name
		doc.desk_access = 1
		doc.is_custom = 1
		doc.insert(ignore_permissions=True)
