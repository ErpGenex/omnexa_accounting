# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.desk.search import validate_and_sanitize_search_inputs

from omnexa_core.omnexa_core.branch_access import enforce_branch_access, get_allowed_branches
from omnexa_core.omnexa_core.branch_access import get_default_branch, get_default_company
from omnexa_core.omnexa_core.user_context import apply_company_branch_defaults


def enforce_branch_access_for_doc(doc, method=None):
	enforce_branch_access(doc)


def populate_company_branch_from_user_context(doc, method=None):
	apply_company_branch_defaults(doc)


def _get_query_for_table(table: str, user=None):
	user = user or frappe.session.user
	allowed = get_allowed_branches(user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	quoted = ", ".join([frappe.db.escape(v) for v in allowed])
	return f"(`tab{table}`.branch in ({quoted}) or `tab{table}`.branch is null or `tab{table}`.branch = '')"


def sales_invoice_query_conditions(user=None):
	return _get_query_for_table("Sales Invoice", user)


def purchase_invoice_query_conditions(user=None):
	return _get_query_for_table("Purchase Invoice", user)


def payment_entry_query_conditions(user=None):
	return _get_query_for_table("Payment Entry", user)


def journal_entry_query_conditions(user=None):
	return _get_query_for_table("Journal Entry", user)


def bank_reconciliation_query_conditions(user=None):
	return _get_query_for_table("Bank Reconciliation", user)


@frappe.whitelist()
def get_logged_in_company_branch():
	company = get_default_company()
	branch = get_default_branch(company) if company else None
	return {"company": company, "branch": branch}


@frappe.whitelist()
@validate_and_sanitize_search_inputs
def delivery_terms_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		SELECT
			name,
			term_name,
			description
		FROM `tabDelivery Terms`
		WHERE docstatus < 2
		  AND (
			%(txt)s = ''
			OR name LIKE %(like_txt)s
			OR term_name LIKE %(like_txt)s
			OR IFNULL(description, '') LIKE %(like_txt)s
		  )
		ORDER BY term_name ASC
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"txt": txt or "",
			"like_txt": f"%{txt or ''}%",
			"start": start,
			"page_len": page_len,
		},
	)
