# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Idempotent Frappe Workflow for Purchase Order / Receipt / Purchase Invoice."""

import frappe

STATE_DRAFT = "Omnexa Procure Chain Draft"
STATE_SUBMITTED = "Omnexa Procure Chain Submitted"
STATE_CANCELLED = "Omnexa Procure Chain Cancelled"

ACTION_SUBMIT = "Submit"
ACTION_CANCEL = "Cancel"

WORKFLOW_BY_DOCTYPE = {
	"Purchase Order": "Omnexa Chain - Purchase Order",
	"Purchase Receipt": "Omnexa Chain - Purchase Receipt",
	"Purchase Invoice": "Omnexa Chain - Purchase Invoice",
	"Purchase Request": "Omnexa Chain - Purchase Request",
	"Budget": "Omnexa Chain - Budget",
}


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


def _build_workflow_doc(doctype: str, workflow_name: str, locked_role: str):
	roles = _transition_roles()
	wf = frappe.new_doc("Workflow")
	wf.workflow_name = workflow_name
	wf.document_type = doctype
	wf.is_active = 1
	wf.workflow_state_field = "workflow_state"

	for state, doc_status, allow_edit in (
		(STATE_DRAFT, "0", "All"),
		(STATE_SUBMITTED, "1", locked_role),
		(STATE_CANCELLED, "2", locked_role),
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
		wf.append(
			"transitions",
			{
				"state": STATE_DRAFT,
				"action": ACTION_SUBMIT,
				"next_state": STATE_SUBMITTED,
				"allowed": role,
				"allow_self_approval": 1,
			},
		)
		wf.append(
			"transitions",
			{
				"state": STATE_SUBMITTED,
				"action": ACTION_CANCEL,
				"next_state": STATE_CANCELLED,
				"allowed": role,
				"allow_self_approval": 1,
			},
		)

	return wf


def _repair_workflow_allow_edit(workflow_name: str, locked_role: str) -> None:
	name = frappe.db.get_value("Workflow", {"workflow_name": workflow_name}, "name")
	if not name:
		return
	wf = frappe.get_doc("Workflow", name)
	changed = False
	for row in wf.states:
		if row.state in (STATE_SUBMITTED, STATE_CANCELLED) and row.allow_edit == "All":
			row.allow_edit = locked_role
			changed = True
	if changed:
		wf.save(ignore_permissions=True)
		frappe.clear_cache(doctype=wf.document_type)


def ensure_procurement_chain_workflows() -> None:
	if frappe.flags.in_install:
		return

	for name in (STATE_DRAFT, STATE_SUBMITTED, STATE_CANCELLED):
		_ensure_workflow_state(name)
	_ensure_workflow_action(ACTION_SUBMIT)
	_ensure_workflow_action(ACTION_CANCEL)

	locked_role = "System Manager" if frappe.db.exists("Role", "System Manager") else "All"

	for doctype, workflow_name in WORKFLOW_BY_DOCTYPE.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		if frappe.db.exists("Workflow", {"workflow_name": workflow_name}):
			_repair_workflow_allow_edit(workflow_name, locked_role)
			continue
		wf = _build_workflow_doc(doctype, workflow_name, locked_role)
		wf.insert(ignore_permissions=True)
		frappe.clear_cache(doctype=doctype)
