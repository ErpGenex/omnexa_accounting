# Copyright (c) 2026, Omnexa and contributors
"""Backfill account_name_ar from English name when empty (initial bilingual seed)."""


def execute():
	import frappe

	if not frappe.db.has_column("GL Account", "account_name_ar"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabGL Account`
		SET account_name_ar = account_name
		WHERE IFNULL(account_name_ar, '') = '' AND IFNULL(account_name, '') != ''
		"""
	)
	frappe.db.commit()
