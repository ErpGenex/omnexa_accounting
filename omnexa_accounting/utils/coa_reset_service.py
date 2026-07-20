# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from omnexa_accounting.utils.company_financial_defaults import (
	BRANCH_DEFAULT_GL_FIELDS,
	COMPANY_GL_CODE_BY_FIELD,
)


def _doctype_has_rows(doctype: str, filters: dict | None = None) -> bool:
	if not frappe.db.exists("DocType", doctype):
		return False
	return bool(frappe.db.exists(doctype, filters or {}))


def _ensure_admin_only() -> None:
	# Requirement: Admin only (strict).
	if frappe.session.user != "Administrator":
		frappe.throw(_("Only Administrator can run COA reset."), title=_("Reset COA"))


def _make_backup_file(company: str, branch: str | None, gl_rows: list[dict]) -> str:
	payload = {
		"company": company,
		"branch": branch,
		"doctype": "GL Account",
		"rows": gl_rows,
		"created_at": now_datetime().isoformat()
	}
	content = json.dumps(payload, ensure_ascii=False, indent=2)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"coa-backup-{company}{('-' + branch) if branch else ''}-{frappe.utils.now_datetime().strftime('%Y%m%d-%H%M%S')
	}.json",
			"content": content,
			"is_private": 1
	}
	)
	file_doc.insert(ignore_permissions=True)
	return file_doc.name


def _write_audit_log(
	*,
	company: str,
	branch: str | None,
	status: str,
	confirm_text: str,
	blocked_reason: str | None = None,
	backup_file: str | None = None,
	gl_before: int = 0,
	gl_deleted: int = 0,
) -> str:
	log = frappe.get_doc(
		{
			"doctype": "COA Reset Audit Log",
			"company": company,
			"branch": branch,
			"status": status,
			"performed_by": frappe.session.user,
			"performed_on": now_datetime(),
			"confirm_text": confirm_text,
			"blocked_reason": blocked_reason or "",
			"backup_file": backup_file,
			"gl_accounts_before": int(gl_before or 0),
			"gl_accounts_deleted": int(gl_deleted or 0)
	}
	)
	log.insert(ignore_permissions=True)
	return log.name


def _clear_company_gl_defaults(company: str, branch: str | None = None) -> None:
	"""Clear GL default links without bumping Company.modified (avoids desk timestamp conflicts)."""
	if not frappe.db.exists("Company", company):
		return
	co = frappe.get_doc("Company", company)
	for fieldname in COMPANY_GL_CODE_BY_FIELD:
		if co.meta.has_field(fieldname) and co.get(fieldname):
			frappe.db.set_value("Company", company, fieldname, None, update_modified=False)

	if branch and frappe.db.exists("Branch", branch):
		br = frappe.get_doc("Branch", branch)
		for fieldname in BRANCH_DEFAULT_GL_FIELDS:
			if br.meta.has_field(fieldname) and br.get(fieldname):
				frappe.db.set_value("Branch", branch, fieldname, None, update_modified=False)


@frappe.whitelist(methods=["POST"])
def reset_coa(
	company: str,
	confirm_text: str,
	branch: str | None = None,
	skip_ledger_checks: bool | int = False,
) -> dict:
	"""
	Secure COA reset.

	Hard stops:
	- If GL Entry exists and has rows (future-proof)
	- If Journal Entry exists and has rows

	Allowed only when:
	- Administrator
	- confirm_text == 'RESET COA'
	- Backup created
	- Audit log written
	"""
	frappe.only_for("System Manager")
	_ensure_admin_only()

	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Company is required."), title=_("Reset COA"))

	confirm_text = (confirm_text or "").strip()
	if confirm_text != "RESET COA":
		_write_audit_log(
			company=company,
			branch=branch,
			status="blocked",
			confirm_text=confirm_text,
			blocked_reason="Confirm text mismatch",
		)
		frappe.throw(_("Type RESET COA to confirm."), title=_("Reset COA"))

	# Hard-stops: Journals and GL entries (skipped during full company wipe after ledger purge).
	if not cint(skip_ledger_checks):
		if _doctype_has_rows("Journal Entry", {"company": company
	}):
			_write_audit_log(
				company=company,
				branch=branch,
				status="blocked",
				confirm_text=confirm_text,
				blocked_reason="Journal Entries exist",
			)
			frappe.throw(_("Reset blocked: Journal Entries exist."), title=_("Reset COA"))

		if _doctype_has_rows("GL Entry", {"company": company
	}):
			_write_audit_log(
				company=company,
				branch=branch,
				status="blocked",
				confirm_text=confirm_text,
				blocked_reason="GL Entries exist",
			)
			frappe.throw(_("Reset blocked: GL Entries exist."), title=_("Reset COA"))

	if not frappe.db.exists("DocType", "GL Account"):
		_write_audit_log(
			company=company,
			branch=branch,
			status="blocked",
			confirm_text=confirm_text,
			blocked_reason="GL Account DocType missing",
		)
		frappe.throw(_("GL Account doctype is not installed."), title=_("Reset COA"))

	filters = {"company": company
	}
	if branch:
		filters["branch"] = branch

	gl_rows = frappe.get_all(
		"GL Account",
		filters=filters,
		fields=[
			"name",
			"company",
			"branch",
			"account_number",
			"account_name",
			"account_type",
			"is_group",
			"parent_account",
			"pl_bucket",
			"cash_flow_section",
			"working_capital_bucket",
			"is_stock_valuation",
			"lft",
			"rgt",
		],
		limit_page_length=100000,
	)

	backup_file = _make_backup_file(company, branch, gl_rows)
	gl_before = len(gl_rows)

	try:
		# Clear defaults first to avoid dangling links.
		_clear_company_gl_defaults(company, branch=branch)

		# Delete GL accounts scoped to company (and branch if provided).
		frappe.db.delete("GL Account", filters)
		frappe.db.commit()
	except Exception as e:
		_write_audit_log(
			company=company,
			branch=branch,
			status="failed",
			confirm_text=confirm_text,
			blocked_reason=str(e),
			backup_file=backup_file,
			gl_before=gl_before,
			gl_deleted=0,
		)
		raise

	# Count remaining after delete.
	remaining = frappe.db.count("GL Account", filters)
	gl_deleted = max(gl_before - int(remaining or 0), 0)
	log_name = _write_audit_log(
		company=company,
		branch=branch,
		status="completed",
		confirm_text=confirm_text,
		backup_file=backup_file,
		gl_before=gl_before,
		gl_deleted=gl_deleted,
	)
	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"backup_file": backup_file,
		"audit_log": log_name,
		"gl_accounts_before": gl_before,
		"gl_accounts_deleted": gl_deleted
	}

