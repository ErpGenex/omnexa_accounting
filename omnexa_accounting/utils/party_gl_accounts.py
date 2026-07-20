# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe

from omnexa_core.omnexa_core.feature_flags import is_feature_enabled


def _sanitize_code(value: str) -> str:
	return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def _make_party_gl_account_number(kind: str, party_code: str, party_name: str) -> str:
	"""
	Build a stable account_number for sub-ledger leaf accounts.
	Format: AR-<CODE> / AP-<CODE>, with fallback hash-like suffix from name.
	"""
	base = _sanitize_code(party_code)[:24]
	if not base:
		base = _sanitize_code(party_name)[:16]
	if not base:
		base = frappe.generate_hash(length=10).upper()
	return f"{kind}-{base}"


def _find_existing_party_gl(company: str, account_number: str) -> str | None:
	return frappe.db.get_value(
		"GL Account",
		{"company": company, "account_number": account_number},
		"name",
	)


def _create_party_gl_leaf(
	*,
	company: str,
	branch: str | None,
	parent_account: str,
	account_number: str,
	account_name: str,
	account_type: str,
	working_capital_bucket: str,
) -> str:
	doc = frappe.new_doc("GL Account")
	doc.company = company
	if branch:
		doc.branch = branch
	doc.parent_account = parent_account
	doc.account_number = account_number
	doc.account_name = account_name
	doc.account_type = account_type
	doc.is_group = 0
	doc.working_capital_bucket = working_capital_bucket
	doc.insert(ignore_permissions=True)
	return doc.name


def _link_party_account_if_field_exists(doc, fieldname: str, gl_name: str) -> None:
	if doc.meta.has_field(fieldname):
		doc.set(fieldname, gl_name)


def ensure_customer_receivable_account(doc, method=None):
	"""
	Auto-create a dedicated receivable GL for customer (optional, feature-flagged).
	"""
	if not is_feature_enabled("enterprise_auto_party_gl_accounts", default=False):
		return
	if not doc.company:
		return
	if not frappe.db.exists("DocType", "GL Account"):
		return

	parent_gl = frappe.db.get_value("Company", doc.company, "default_receivable_gl")
	if not parent_gl:
		return

	acc_no = _make_party_gl_account_number("AR", doc.get("customer_code") or "", doc.get("customer_name") or "")
	existing = _find_existing_party_gl(doc.company, acc_no)
	if existing:
		_link_party_account_if_field_exists(doc, "receivable_account", existing)
		return

	leaf_name = _create_party_gl_leaf(
		company=doc.company,
		branch=None,
		parent_account=parent_gl,
		account_number=acc_no,
		account_name=f"AR - {doc.get('customer_name') or doc.name}",
		account_type="Asset",
		working_capital_bucket="Trade Receivables",
	)
	_link_party_account_if_field_exists(doc, "receivable_account", leaf_name)


def ensure_supplier_payable_account(doc, method=None):
	"""
	Auto-create a dedicated payable GL for supplier (optional, feature-flagged).
	"""
	if not is_feature_enabled("enterprise_auto_party_gl_accounts", default=False):
		return
	if not doc.company:
		return
	if not frappe.db.exists("DocType", "GL Account"):
		return

	parent_gl = frappe.db.get_value("Company", doc.company, "default_trade_payable_gl")
	if not parent_gl:
		return

	acc_no = _make_party_gl_account_number("AP", doc.get("supplier_code") or "", doc.get("supplier_name") or "")
	existing = _find_existing_party_gl(doc.company, acc_no)
	if existing:
		_link_party_account_if_field_exists(doc, "payable_account", existing)
		return

	leaf_name = _create_party_gl_leaf(
		company=doc.company,
		branch=None,
		parent_account=parent_gl,
		account_number=acc_no,
		account_name=f"AP - {doc.get('supplier_name') or doc.name}",
		account_type="Liability",
		working_capital_bucket="Trade Payables",
	)
	_link_party_account_if_field_exists(doc, "payable_account", leaf_name)

