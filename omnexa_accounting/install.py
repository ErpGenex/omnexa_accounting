# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe


SUPPORTED_FRAPPE_MAJOR = 15


def enforce_supported_frappe_version():
	"""Fail early when running on an unsupported Frappe major release."""
	version_text = (getattr(frappe, "__version__", "") or "").strip()
	if not version_text:
		return

	major_token = version_text.split(".", 1)[0]
	try:
		major = int(major_token)
	except ValueError:
		return

	if major != SUPPORTED_FRAPPE_MAJOR:
		frappe.throw(
			f"Unsupported Frappe version '{version_text}' for omnexa_accounting. "
			f"Supported range is >=15.0,<16.0.",
			frappe.ValidationError,
		)


def after_install():
	enforce_supported_frappe_version()
	ensure_accounting_roles()
	ensure_posting_link_fields()
	ensure_gl_account_balance_field_and_list_layout()
	ensure_inventory_accounting_fields()
	ensure_inventory_accounting_defaults()
	ensure_customer_balance_field_and_list_layout()
	ensure_warehouse_stock_snapshot_fields_and_layout()
	_run_post_install_auto_bootstrap()


def after_migrate():
	enforce_supported_frappe_version()
	ensure_accounting_roles()
	ensure_journal_entry_entry_type_not_duplicate_custom_field()
	ensure_sales_order_delivery_terms_not_duplicate_custom_field()
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
	ensure_report_names_are_python_importable()
	ensure_posting_link_fields()
	ensure_gl_account_balance_field_and_list_layout()
	ensure_inventory_accounting_fields()
	ensure_inventory_accounting_defaults()
	ensure_customer_balance_field_and_list_layout()
	ensure_warehouse_stock_snapshot_fields_and_layout()
	_run_post_install_auto_bootstrap()


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


def ensure_sales_order_delivery_terms_not_duplicate_custom_field():
	"""Remove legacy Custom Field that shadows Sales Order.delivery_terms as Data."""
	try:
		name = frappe.db.get_value("Custom Field", {"dt": "Sales Order", "fieldname": "delivery_terms"}, "name")
		if not name:
			return
		fieldtype = frappe.db.get_value("Custom Field", name, "fieldtype")
		if fieldtype == "Data":
			frappe.delete_doc("Custom Field", name, force=True)
			frappe.db.commit()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(), "Omnexa Accounting: remove duplicate Sales Order delivery_terms CF"
		)


def _run_post_install_auto_bootstrap():
	"""Best-effort automatic defaults setup for fresh installations."""
	try:
		from omnexa_accounting.utils.production_readiness import auto_bootstrap_defaults_after_install

		auto_bootstrap_defaults_after_install()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(), "Omnexa Accounting: post-install auto bootstrap failed"
		)


def ensure_report_names_are_python_importable():
	"""Avoid report names that break script report module imports.

	Frappe builds module paths from report name using a scrub that can leave characters
	like parentheses, causing ModuleNotFoundError.
	"""
	try:
		old = "Cash Flow Statement (Structured)"
		new = "Cash Flow Statement Structured"
		if frappe.db.exists("Report", old) and not frappe.db.exists("Report", new):
			frappe.rename_doc("Report", old, new, ignore_permissions=True, force=True)
			frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure report names importable")


def ensure_posting_link_fields():
	"""Add link fields used by UI to open posting entries."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		custom_fields = {
			"Sales Invoice": [
				{
					"fieldname": "posting_journal_entry",
					"label": "Posting Journal Entry",
					"fieldtype": "Link",
					"options": "Journal Entry",
					"insert_after": "grand_total",
					"read_only": 1,
					"no_copy": 1,
					"allow_on_submit": 1,
				},
			],
			"Purchase Invoice": [
				{
					"fieldname": "posting_journal_entry",
					"label": "Posting Journal Entry",
					"fieldtype": "Link",
					"options": "Journal Entry",
					"insert_after": "grand_total",
					"read_only": 1,
					"no_copy": 1,
					"allow_on_submit": 1,
				},
			],
		}
		create_custom_fields(custom_fields, ignore_validate=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure posting link fields")


def ensure_gl_account_balance_field_and_list_layout():
	"""Ensure GL Account list has separate number/name/balance columns."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
		from frappe.desk.doctype.list_view_settings.list_view_settings import save_listview_settings

		create_custom_fields(
			{
				"GL Account": [
					{
						"fieldname": "balance_snapshot",
						"label": "Balance",
						"fieldtype": "Currency",
						"in_list_view": 1,
						"insert_after": "account_number",
						"read_only": 1,
						"no_copy": 1,
						"allow_on_submit": 1,
					}
				]
			},
			ignore_validate=True,
		)

		save_listview_settings(
			"GL Account",
			{
				"total_fields": "8",
				"fields": frappe.as_json(
					[
						{"fieldname": "account_name", "label": "Account Name"},
						{"fieldname": "account_number", "label": "Account Number"},
						{"fieldname": "balance_snapshot", "label": "Balance"},
						{"fieldname": "company", "label": "Company"},
						{"fieldname": "branch", "label": "Branch"},
					]
				),
			},
			[],
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure GL account balance/list layout")


def ensure_inventory_accounting_fields():
	"""Global inventory accounting controls on Warehouse."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		create_custom_fields(
			{
				"Warehouse": [
					{
						"fieldname": "inventory_gl_account",
						"label": "Inventory GL Account",
						"fieldtype": "Link",
						"options": "GL Account",
						"insert_after": "company",
					},
					{
						"fieldname": "stock_adjustment_gl_account",
						"label": "Stock Adjustment GL Account",
						"fieldtype": "Link",
						"options": "GL Account",
						"insert_after": "inventory_gl_account",
					},
				]
			},
			ignore_validate=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure inventory accounting fields")


def ensure_inventory_accounting_defaults():
	"""Backfill warehouse accounting fields from company defaults."""
	try:
		if not frappe.db.exists("DocType", "Warehouse"):
			return
		wmeta = frappe.get_meta("Warehouse")
		if not (wmeta.has_field("inventory_gl_account") and wmeta.has_field("stock_adjustment_gl_account")):
			return

		for wh in frappe.get_all("Warehouse", fields=["name", "company", "inventory_gl_account", "stock_adjustment_gl_account"]):
			inv = wh.inventory_gl_account or frappe.db.get_value("Company", wh.company, "default_inventory_gl")
			adj = wh.stock_adjustment_gl_account or frappe.db.get_value("Company", wh.company, "default_opex_gl")
			frappe.db.set_value("Warehouse", wh.name, "inventory_gl_account", inv, update_modified=False)
			frappe.db.set_value("Warehouse", wh.name, "stock_adjustment_gl_account", adj, update_modified=False)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure inventory accounting defaults")


def ensure_customer_balance_field_and_list_layout():
	"""Show customer balance in list and keep list columns consistent."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
		from frappe.desk.doctype.list_view_settings.list_view_settings import save_listview_settings

		create_custom_fields(
			{
				"Customer": [
					{
						"fieldname": "balance_snapshot",
						"label": "Balance",
						"fieldtype": "Currency",
						"in_list_view": 1,
						"insert_after": "status",
						"read_only": 1,
						"no_copy": 1,
					}
				]
			},
			ignore_validate=True,
		)

		save_listview_settings(
			"Customer",
			{
				"total_fields": "8",
				"fields": frappe.as_json(
					[
						{"fieldname": "customer_name", "label": "Customer Name"},
						{"fieldname": "status", "label": "Status"},
						{"fieldname": "company", "label": "Company"},
						{"fieldname": "balance_snapshot", "label": "Balance"},
					]
				),
			},
			[],
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure customer balance/list layout")


def ensure_warehouse_stock_snapshot_fields_and_layout():
	"""Expose warehouse stock qty/value in list as separate columns."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
		from frappe.desk.doctype.list_view_settings.list_view_settings import save_listview_settings

		create_custom_fields(
			{
				"Warehouse": [
					{
						"fieldname": "stock_qty_snapshot",
						"label": "Stock Qty",
						"fieldtype": "Float",
						"in_list_view": 1,
						"insert_after": "company",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "stock_value_snapshot",
						"label": "Stock Value",
						"fieldtype": "Currency",
						"in_list_view": 1,
						"insert_after": "stock_qty_snapshot",
						"read_only": 1,
						"no_copy": 1,
					},
				]
			},
			ignore_validate=True,
		)

		save_listview_settings(
			"Warehouse",
			{
				"total_fields": "8",
				"fields": frappe.as_json(
					[
						{"fieldname": "warehouse_name", "label": "Warehouse Name"},
						{"fieldname": "company", "label": "Company"},
						{"fieldname": "stock_qty_snapshot", "label": "Stock Qty"},
						{"fieldname": "stock_value_snapshot", "label": "Stock Value"},
					]
				),
			},
			[],
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure warehouse stock snapshot/list layout")
