app_name = "omnexa_accounting"
app_title = "ErpGenEx — Accounting"
app_publisher = "ErpGenEx"
app_description = "Double-entry accounting for ErpGenEx (omnexa_accounting)"
app_email = "dev@erpgenex.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["omnexa_core"]

add_to_apps_screen = [
	{
		"name": "omnexa_accounting",
		"logo": "/assets/omnexa_accounting/logo.png",
		"title": "FinTruth",
		"route": "/app/acct-executive-dashboard",
		"has_permission": "omnexa_core.omnexa_core.finance_demo.finance_app_permission.has_app_permission",
	}
]


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/omnexa_accounting/css/omnexa_accounting.css"
app_include_js = [
	"/assets/omnexa_accounting/js/link_formatters.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/omnexa_accounting/css/omnexa_accounting.css"
# web_include_js = "/assets/omnexa_accounting/js/omnexa_accounting.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "omnexa_accounting/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Company": "public/js/company_production_demo.js",
	"Branch": "public/js/branch_financial_defaults.js",
	"Customer": "public/js/customer_form.js",
	"Warehouse": "public/js/warehouse_form.js",
	"Item": "public/js/item_card.js",
	"GL Account": "public/js/gl_account_form.js",
	"Sales Order": "public/js/sales_order.js",
	"Sales Invoice": "public/js/sales_invoice.js",
	"Sales Quotation": "public/js/sales_quotation.js",
	"Purchase Order": "public/js/purchase_order.js",
	"Purchase Request": "public/js/purchase_request.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Bank Statement Import": "public/js/bank_statement_import.js",
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Stock Transfer Request": "public/js/stock_transfer_request.js",
	"Delivery Note": "public/js/delivery_note.js",
	"Shipment": "public/js/shipment.js",
	"Payment Entry": "public/js/payment_entry.js",
	"Stock Entry": "public/js/stock_entry.js",
	"COA Template": "public/js/coa_template.js",
	"CoA Settings": "public/js/coa_settings.js",
}
doctype_list_js = {
	"GL Account": "public/js/gl_account_list.js",
	"Customer": "public/js/customer_list.js",
	"Warehouse": "public/js/warehouse_list.js",
	"Sales Invoice": "public/js/sales_invoice_list.js",
}
doctype_tree_js = {
	"GL Account": "public/js/gl_account_tree.js",
}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "omnexa_accounting/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "omnexa_accounting.utils.jinja_methods",
# 	"filters": "omnexa_accounting.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "omnexa_accounting.install.enforce_supported_frappe_version"
after_install = "omnexa_accounting.install.after_install"
before_migrate = "omnexa_accounting.install.enforce_supported_frappe_version"
after_migrate = "omnexa_accounting.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "omnexa_accounting.uninstall.before_uninstall"
# after_uninstall = "omnexa_accounting.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "omnexa_accounting.utils.before_app_install"
# after_app_install = "omnexa_accounting.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "omnexa_accounting.utils.before_app_uninstall"
# after_app_uninstall = "omnexa_accounting.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "omnexa_accounting.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
permission_query_conditions = {
	"Sales Invoice": "omnexa_accounting.permissions.sales_invoice_query_conditions",
	"Purchase Invoice": "omnexa_accounting.permissions.purchase_invoice_query_conditions",
	"Payment Entry": "omnexa_accounting.permissions.payment_entry_query_conditions",
	"Journal Entry": "omnexa_accounting.permissions.journal_entry_query_conditions",
	"Bank Reconciliation": "omnexa_accounting.permissions.bank_reconciliation_query_conditions",
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
	"Company": {
		"validate": "omnexa_accounting.utils.company_financial_defaults.run_company_financial_validations",
		"on_update": "omnexa_accounting.utils.company_financial_defaults.on_company_update_sync_globals",
	},
	"Branch": {
		"validate": "omnexa_accounting.utils.company_financial_defaults.run_branch_financial_validations",
	},
	"Sales Order": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_accounting.permissions.enforce_branch_access_for_doc",
	},
	"Purchase Order": {
		"on_submit": "omnexa_accounting.automation.sop_hooks.on_purchase_order_submit",
	},
	"Sales Quotation": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": [
			"omnexa_accounting.permissions.enforce_branch_access_for_doc",
			"omnexa_accounting.utils.global_erp_strict_validations.validate_sales_quotation",
		],
	},
	"Sales Invoice": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": [
			"omnexa_accounting.permissions.enforce_branch_access_for_doc",
			"omnexa_accounting.utils.global_erp_strict_validations.validate_sales_invoice",
		],
		"on_submit": "omnexa_accounting.utils.customer_balances.on_sales_invoice_submit",
		"on_cancel": "omnexa_accounting.utils.customer_balances.on_sales_invoice_cancel",
	},
	"Purchase Invoice": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": [
			"omnexa_accounting.permissions.enforce_branch_access_for_doc",
			"omnexa_accounting.utils.global_erp_strict_validations.validate_purchase_invoice",
		],
	},
	"Item": {
		"before_validate": "omnexa_accounting.utils.enterprise_hooks.ensure_item_code",
	},
	"Customer": {
		"before_validate": "omnexa_accounting.utils.enterprise_hooks.ensure_customer_code",
		"validate": "omnexa_accounting.utils.party_gl_accounts.ensure_customer_receivable_account",
	},
	"Supplier": {
		"before_validate": "omnexa_accounting.utils.enterprise_hooks.ensure_supplier_code",
		"validate": "omnexa_accounting.utils.party_gl_accounts.ensure_supplier_payable_account",
	},
	"Employee": {
		"before_validate": "omnexa_accounting.utils.enterprise_hooks.ensure_employee_code",
	},
	"Purchase Receipt": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_accounting.permissions.enforce_branch_access_for_doc",
	},
	"Delivery Note": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_accounting.permissions.enforce_branch_access_for_doc",
	},
	"Payment Entry": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_accounting.permissions.enforce_branch_access_for_doc",
		"on_submit": "omnexa_accounting.utils.customer_balances.on_payment_entry_submit",
		"on_cancel": "omnexa_accounting.utils.customer_balances.on_payment_entry_cancel",
	},
	"Journal Entry": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_accounting.permissions.enforce_branch_access_for_doc",
		"on_submit": "omnexa_accounting.utils.gl_account_balances.on_journal_entry_submit",
		"on_cancel": "omnexa_accounting.utils.gl_account_balances.on_journal_entry_cancel",
	},
	"Bank Reconciliation": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_accounting.permissions.enforce_branch_access_for_doc",
	},
	"Pipeline Lead": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context"
	},
	"Pipeline Opportunity": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context"
	},
	"CRM Activity": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context",
		"validate": "omnexa_accounting.permissions.enforce_branch_access_for_doc"
	},
	"CRM Campaign": {
		"before_validate": "omnexa_accounting.permissions.populate_company_branch_from_user_context"
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"omnexa_accounting.tasks.all"
# 	],
# 	"daily": [
# 		"omnexa_accounting.tasks.daily"
# 	],
# 	"hourly": [
# 		"omnexa_accounting.tasks.hourly"
# 	],
# 	"weekly": [
# 		"omnexa_accounting.tasks.weekly"
# 	],
# 	"monthly": [
# 		"omnexa_accounting.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "omnexa_accounting.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "omnexa_accounting.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "omnexa_accounting.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

ignore_links_on_delete = [
	"COA Reset Audit Log",
	"Production Seed Log",
	"Experience Tenant Theme",
	"Catalog Item",
	"Web Order",
	"Payment Intent",
	"Booking",
	"Bookable Resource",
]

# Request Events
# ----------------
# before_request = ["omnexa_accounting.utils.before_request"]
# after_request = ["omnexa_accounting.utils.after_request"]

# Job Events
# ----------
# before_job = ["omnexa_accounting.utils.before_job"]
# after_job = ["omnexa_accounting.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"omnexa_accounting.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

