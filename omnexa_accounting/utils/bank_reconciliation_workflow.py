# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Frappe Workflow for Bank Reconciliation (non-submittable doc — all states stay docstatus 0)."""

import frappe

STATE_DRAFT = "Omnexa Bank Rec Draft"
STATE_REVIEW = "Omnexa Bank Rec In Review"
STATE_CLOSED = "Omnexa Bank Rec Closed"

ACTION_SUBMIT = "Submit"
ACTION_CANCEL = "Cancel"

WORKFLOW_NAME = "Omnexa Chain - Bank Reconciliation"


def _ensure_workflow_state(workflow_state_name: str) -> None:
	if frappe.db.exists("Workflow State", workflow_state_name):
		return
	doc = frappe.new_doc("Workflow State")
	doc.workflow_state_name = workflow_state_name
	doc.insert(ignore_permissions=True)


def _ensure_workflow_action(action_name: str) -> None:
	if frappe.db.exists("Workflow Action Master", action_name):
		return
	doc = frappe.new_doc("Workflow Action Master")
	doc.workflow_action_name = action_name
	doc.insert(ignore_permissions=True)


def _transition_roles() -> list[str]:
	roles = []
	for role in ("System Manager", "Accounts Manager", "Accounts User"):
		if frappe.db.exists("Role", role):
			roles.append(role)
	return roles or ["System Manager"]


def _build_bank_reconciliation_workflow(locked_role: str):
	roles = _transition_roles()
	wf = frappe.new_doc("Workflow")
	wf.workflow_name = WORKFLOW_NAME
	wf.document_type = "Bank Reconciliation"
	wf.is_active = 1
	wf.workflow_state_field = "workflow_state"
	wf.send_email_alert = 0

	for state, doc_status, allow_edit in (
		(STATE_DRAFT, "0", "All"),
		(STATE_REVIEW, "0", "All"),
		(STATE_CLOSED, "0", locked_role),
	):
		wf.append(
			"states",
			{
				"state": state,
				"doc_status": doc_status,
				"allow_edit": allow_edit,
			},
		)

	for role in roles:
		for trans in (
			{"state": STATE_DRAFT, "action": ACTION_SUBMIT, "next_state": STATE_REVIEW},
			{"state": STATE_REVIEW, "action": ACTION_SUBMIT, "next_state": STATE_CLOSED},
			{"state": STATE_REVIEW, "action": ACTION_CANCEL, "next_state": STATE_DRAFT},
		):
			wf.append(
				"transitions",
				{
					**trans,
					"allowed": role,
					"allow_self_approval": 1,
				},
			)

	return wf


def ensure_bank_reconciliation_workflow() -> None:
	if frappe.flags.in_install:
		return
	if not frappe.db.exists("DocType", "Bank Reconciliation"):
		return

	for name in (STATE_DRAFT, STATE_REVIEW, STATE_CLOSED):
		_ensure_workflow_state(name)
	_ensure_workflow_action(ACTION_SUBMIT)
	_ensure_workflow_action(ACTION_CANCEL)

	locked_role = "System Manager" if frappe.db.exists("Role", "System Manager") else "All"

	if frappe.db.exists("Workflow", {"workflow_name": WORKFLOW_NAME}):
		return

	wf = _build_bank_reconciliation_workflow(locked_role)
	wf.insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Bank Reconciliation")
	frappe.db.sql(
		"""
		UPDATE `tabBank Reconciliation`
		SET workflow_state = %s
		WHERE IFNULL(workflow_state, '') = ''
		""",
		(STATE_DRAFT,),
	)
