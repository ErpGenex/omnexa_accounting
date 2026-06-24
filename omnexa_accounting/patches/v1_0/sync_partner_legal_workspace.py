# Copyright (c) 2026, Omnexa
import frappe


def execute():
	"""Expose partner legal reports on Accounting workspace."""
	if not frappe.db.exists("Workspace", "Accounting"):
		return
	from omnexa_accounting.workspace.acct_workspace import sync_acct_workspace_menu

	sync_acct_workspace_menu(save=True, rebuild=True)
