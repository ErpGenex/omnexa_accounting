# Copyright (c) 2026, Omnexa
import frappe


def execute():
	"""Register partner legal print center page and sync Accounting workspace."""
	from omnexa_accounting.workspace.acct_workspace import sync_acct_workspace_menu

	if frappe.db.exists("Workspace", "Accounting"):
		sync_acct_workspace_menu(save=True, rebuild=True)
