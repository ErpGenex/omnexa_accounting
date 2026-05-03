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
	ensure_invoice_tax_shipping_stock_fields()
	ensure_shipment_fields()
	ensure_invoice_shipping_and_totals_layout()
	ensure_invoice_project_link_field_types()
	ensure_invoice_collapsible_sections()
	ensure_gl_account_balance_field_and_list_layout()
	ensure_inventory_accounting_fields()
	ensure_inventory_accounting_defaults()
	ensure_customer_balance_field_and_list_layout()
	ensure_warehouse_stock_snapshot_fields_and_layout()
	ensure_coa_settings_defaults()
	ensure_pos_basics()
	ensure_customer_codes_backfilled()
	ensure_supplier_codes_backfilled()
	ensure_item_codes_backfilled()
	ensure_gl_account_fallback_numbers_backfilled()
	ensure_employee_codes_backfilled()
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
	ensure_invoice_tax_shipping_stock_fields()
	ensure_shipment_fields()
	ensure_invoice_shipping_and_totals_layout()
	ensure_invoice_project_link_field_types()
	ensure_invoice_collapsible_sections()
	ensure_gl_account_balance_field_and_list_layout()
	ensure_inventory_accounting_fields()
	ensure_inventory_accounting_defaults()
	ensure_customer_balance_field_and_list_layout()
	ensure_warehouse_stock_snapshot_fields_and_layout()
	ensure_coa_settings_defaults()
	ensure_pos_basics()
	ensure_customer_codes_backfilled()
	ensure_supplier_codes_backfilled()
	ensure_item_codes_backfilled()
	ensure_gl_account_fallback_numbers_backfilled()
	ensure_employee_codes_backfilled()
	_run_post_install_auto_bootstrap()


def ensure_customer_codes_backfilled():
	"""Fill missing Customer.customer_code for legacy rows (auto series per company)."""
	try:
		from omnexa_accounting.utils.customer_codes import backfill_missing_customer_codes

		backfill_missing_customer_codes()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure_customer_codes_backfilled")


def ensure_supplier_codes_backfilled():
	try:
		from omnexa_accounting.utils.supplier_codes import backfill_missing_supplier_codes

		backfill_missing_supplier_codes()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure_supplier_codes_backfilled")


def ensure_item_codes_backfilled():
	try:
		from omnexa_accounting.utils.item_codes import backfill_missing_item_codes

		backfill_missing_item_codes()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure_item_codes_backfilled")


def ensure_gl_account_fallback_numbers_backfilled():
	try:
		from omnexa_accounting.utils.gl_account_codes import backfill_missing_gl_account_fallback_numbers

		backfill_missing_gl_account_fallback_numbers()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure_gl_account_fallback_numbers_backfilled")


def ensure_employee_codes_backfilled():
	try:
		from omnexa_accounting.utils.employee_codes import backfill_missing_employee_codes

		backfill_missing_employee_codes()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure_employee_codes_backfilled")


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


def ensure_coa_settings_defaults():
	"""Ensure one CoA Settings row per company (backward-safe defaults)."""
	try:
		companies = frappe.get_all("Company", fields=["name"], limit_page_length=100000)
		for c in companies:
			if frappe.db.exists("CoA Settings", {"company": c.name}):
				continue
			doc = frappe.get_doc(
				{
					"doctype": "CoA Settings",
					"company": c.name,
					"enable_numbering_engine": 1,
					"default_consolidation_view": 0,
					"manual_number_override_roles": "System Manager\nAccounts Manager",
					"asset_mask": "1xxx",
					"liability_mask": "2xxx",
					"equity_mask": "3xxx",
					"revenue_mask": "4xxx",
					"expense_mask": "5xxx",
					"require_group_reporting_tag_for_intercompany": 1,
					"enforce_account_currency_match": 1,
					"allow_direct_posting_default": 1,
				}
			)
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure CoA Settings defaults")


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


def ensure_pos_basics():
	"""Enable POS workflow using Sales Invoice when POS Invoice doctype is unavailable."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		create_custom_fields(
			{
				"Sales Invoice": [
					{
						"fieldname": "pos_section",
						"label": "Point of Sale",
						"fieldtype": "Section Break",
						"insert_after": "customer",
						"collapsible": 1,
					},
					{
						"fieldname": "is_pos",
						"label": "Is POS",
						"fieldtype": "Check",
						"insert_after": "pos_section",
						"default": "0",
					},
					{
						"fieldname": "pos_profile",
						"label": "POS Profile",
						"fieldtype": "Link",
						"options": "POS Profile",
						"insert_after": "is_pos",
						"depends_on": "eval:doc.is_pos==1",
					},
				]
			},
			ignore_validate=True,
		)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure POS basics")


def ensure_invoice_tax_shipping_stock_fields():
	"""Expose tax category, shipping, and update-stock controls on invoices."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		create_custom_fields(
			{
				"Sales Invoice": [
					{
						"fieldname": "tax_shipping_section",
						"label": "Tax and Shipping",
						"fieldtype": "Section Break",
						"insert_after": "conversion_rate",
						"collapsible": 1,
					},
					{
						"fieldname": "tax_category",
						"label": "Tax Category",
						"fieldtype": "Link",
						"options": "Tax Category",
						"insert_after": "tax_shipping_section",
					},
					{
						"fieldname": "tax_rate",
						"label": "Tax Rate (%)",
						"fieldtype": "Percent",
						"insert_after": "tax_category",
						"default": "0",
					},
					{
						"fieldname": "tax_amount_manual",
						"label": "Tax Amount",
						"fieldtype": "Currency",
						"insert_after": "tax_rate",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "shipment_reference",
						"label": "Shipment Reference",
						"fieldtype": "Data",
						"insert_after": "tax_amount_manual",
					},
					{
						"fieldname": "project_reference",
						"label": "Project Reference",
						"fieldtype": "Data",
						"insert_after": "project_contract",
					},
					{
						"fieldname": "project_task_reference",
						"label": "Project Task Reference",
						"fieldtype": "Data",
						"insert_after": "pm_wbs_task",
					},
					{
						"fieldname": "shipping_cost",
						"label": "Shipping Cost",
						"fieldtype": "Currency",
						"insert_after": "shipment_reference",
						"default": "0",
					},
					{
						"fieldname": "tax_breakdown_summary",
						"label": "Tax Breakdown",
						"fieldtype": "Small Text",
						"insert_after": "tax_amount_manual",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "payment_mode",
						"label": "Payment Mode",
						"fieldtype": "Select",
						"options": "\nCash\nCredit\nInstallment",
						"insert_after": "due_date",
						"default": "Credit",
					},
					{
						"fieldname": "items_subtotal",
						"label": "Items Subtotal",
						"fieldtype": "Currency",
						"insert_after": "items",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "total_items",
						"label": "Total Items",
						"fieldtype": "Int",
						"insert_after": "items",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "total_qty",
						"label": "Total Qty",
						"fieldtype": "Float",
						"insert_after": "total_items",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "update_stock",
						"label": "Update Stock",
						"fieldtype": "Check",
						"insert_after": "items",
						"default": "0",
					},
					{
						"fieldname": "set_warehouse",
						"label": "Set Warehouse",
						"fieldtype": "Link",
						"options": "Warehouse",
						"insert_after": "update_stock",
					},
					{
						"fieldname": "posting_stock_entry",
						"label": "Posting Stock Entry",
						"fieldtype": "Link",
						"options": "Stock Entry",
						"insert_after": "posting_journal_entry",
						"read_only": 1,
						"no_copy": 1,
						"allow_on_submit": 1,
					},
				],
				"Purchase Invoice": [
					{
						"fieldname": "tax_shipping_section",
						"label": "Tax and Shipping",
						"fieldtype": "Section Break",
						"insert_after": "conversion_rate",
						"collapsible": 1,
					},
					{
						"fieldname": "tax_category",
						"label": "Tax Category",
						"fieldtype": "Link",
						"options": "Tax Category",
						"insert_after": "tax_shipping_section",
					},
					{
						"fieldname": "tax_rate",
						"label": "Tax Rate (%)",
						"fieldtype": "Percent",
						"insert_after": "tax_category",
						"default": "0",
					},
					{
						"fieldname": "tax_amount_manual",
						"label": "Tax Amount",
						"fieldtype": "Currency",
						"insert_after": "tax_rate",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "shipment_reference",
						"label": "Shipment Reference",
						"fieldtype": "Data",
						"insert_after": "tax_amount_manual",
					},
					{
						"fieldname": "project_reference",
						"label": "Project Reference",
						"fieldtype": "Data",
						"insert_after": "project_contract",
					},
					{
						"fieldname": "project_task_reference",
						"label": "Project Task Reference",
						"fieldtype": "Data",
						"insert_after": "pm_wbs_task",
					},
					{
						"fieldname": "shipping_cost",
						"label": "Shipping Cost",
						"fieldtype": "Currency",
						"insert_after": "shipment_reference",
						"default": "0",
					},
					{
						"fieldname": "tax_breakdown_summary",
						"label": "Tax Breakdown",
						"fieldtype": "Small Text",
						"insert_after": "tax_amount_manual",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "payment_mode",
						"label": "Payment Mode",
						"fieldtype": "Select",
						"options": "\nCash\nCredit\nInstallment",
						"insert_after": "due_date",
						"default": "Credit",
					},
					{
						"fieldname": "items_subtotal",
						"label": "Items Subtotal",
						"fieldtype": "Currency",
						"insert_after": "items",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "total_items",
						"label": "Total Items",
						"fieldtype": "Int",
						"insert_after": "items",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "total_qty",
						"label": "Total Qty",
						"fieldtype": "Float",
						"insert_after": "total_items",
						"read_only": 1,
						"no_copy": 1,
					},
					{
						"fieldname": "update_stock",
						"label": "Update Stock",
						"fieldtype": "Check",
						"insert_after": "items",
						"default": "0",
					},
					{
						"fieldname": "set_warehouse",
						"label": "Set Warehouse",
						"fieldtype": "Link",
						"options": "Warehouse",
						"insert_after": "update_stock",
					},
					{
						"fieldname": "posting_stock_entry",
						"label": "Posting Stock Entry",
						"fieldtype": "Link",
						"options": "Stock Entry",
						"insert_after": "posting_journal_entry",
						"read_only": 1,
						"no_copy": 1,
						"allow_on_submit": 1,
					},
				],
			},
			ignore_validate=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure invoice tax/shipping/stock fields")


def ensure_shipment_fields():
	"""Expose shipment linkage fields on sales/purchase invoices."""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		create_custom_fields(
			{
				"Sales Invoice": [
					{
						"fieldname": "shipment_carrier",
						"label": "Shipment Carrier",
						"fieldtype": "Link",
						"options": "Shipment Carrier",
						"insert_after": "shipment_reference",
					},
					{
						"fieldname": "shipment_record",
						"label": "Shipment",
						"fieldtype": "Link",
						"options": "Shipment",
						"insert_after": "shipment_carrier",
						"read_only": 1,
						"allow_on_submit": 1,
						"no_copy": 1,
					},
				],
				"Purchase Invoice": [
					{
						"fieldname": "shipment_carrier",
						"label": "Shipment Carrier",
						"fieldtype": "Link",
						"options": "Shipment Carrier",
						"insert_after": "shipment_reference",
					},
					{
						"fieldname": "shipment_record",
						"label": "Shipment",
						"fieldtype": "Link",
						"options": "Shipment",
						"insert_after": "shipment_carrier",
						"read_only": 1,
						"allow_on_submit": 1,
						"no_copy": 1,
					},
				],
			},
			ignore_validate=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure shipment fields")


def ensure_invoice_shipping_and_totals_layout():
	"""Normalize shipment field type and totals block layout on invoice forms."""
	try:
		for dt in ("Sales Invoice", "Purchase Invoice"):
			# Shipment Reference must be a dropdown-like Link, not free text.
			frappe.make_property_setter(
				{
					"doctype": dt,
					"doctype_or_field": "DocField",
					"fieldname": "shipment_reference",
					"property": "fieldtype",
					"value": "Link",
					"property_type": "Data",
				},
				ignore_validate=True,
			)
			frappe.make_property_setter(
				{
					"doctype": dt,
					"doctype_or_field": "DocField",
					"fieldname": "shipment_reference",
					"property": "options",
					"value": "Shipment",
					"property_type": "Text",
				},
				ignore_validate=True,
			)

			# Force totals block order agreed with user.
			for fieldname, insert_after in (
				("items_subtotal", "net_total"),
				("shipping_cost", "items_subtotal"),
				("tax_breakdown_summary", "tax_total"),
			):
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": fieldname,
						"property": "insert_after",
						"value": insert_after,
						"property_type": "Data",
					},
					ignore_validate=True,
				)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure invoice shipping/totals layout")


def ensure_invoice_collapsible_sections():
	"""Make main invoice sections collapsible for better UX."""
	try:
		for dt in ("Sales Invoice", "Purchase Invoice"):
			for section in ("payment_section", "items_section", "totals_section", "base_totals_section"):
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": section,
						"property": "collapsible",
						"value": "1",
						"property_type": "Check",
					},
					ignore_validate=True,
				)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure invoice collapsible sections")


def ensure_invoice_project_link_field_types():
	"""Force invoice project fields to Link types when project doctypes exist."""
	try:
		project_dt = "Project Contract" if frappe.db.exists("DocType", "Project Contract") else None
		task_dt = "PM WBS Task" if frappe.db.exists("DocType", "PM WBS Task") else None
		if not (project_dt or task_dt):
			return

		for dt in ("Sales Invoice", "Purchase Invoice"):
			if project_dt:
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": "project_reference",
						"property": "fieldtype",
						"value": "Link",
						"property_type": "Data",
					},
					ignore_validate=True,
				)
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": "project_reference",
						"property": "options",
						"value": project_dt,
						"property_type": "Text",
					},
					ignore_validate=True,
				)
			if task_dt:
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": "project_task_reference",
						"property": "fieldtype",
						"value": "Link",
						"property_type": "Data",
					},
					ignore_validate=True,
				)
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": "project_task_reference",
						"property": "options",
						"value": task_dt,
						"property_type": "Text",
					},
					ignore_validate=True,
				)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa Accounting: ensure invoice project link field types")


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
