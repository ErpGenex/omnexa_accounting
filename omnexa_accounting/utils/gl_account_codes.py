# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""
Fallback auto-numbering for ``GL Account.account_number`` when CoA masks
do not apply (e.g. missing Account Class) or leave the number blank.
"""

from __future__ import annotations

import re

import frappe
from frappe import _

CODE_PREFIX = "ACCT-"
_CODE_RE = re.compile(r"^ACCT-(\d+)$", re.IGNORECASE)


def _max_assigned_suffix(company: str | None) -> int:
	rows = frappe.db.sql(
		"""
		SELECT account_number
		FROM `tabGL Account`
		WHERE company <=> %s
		  AND account_number IS NOT NULL
		  AND account_number != ''
		""",
		(company,),
	)
	mx = 0
	for (code,) in rows or []:
		if not code:
			continue
		m = _CODE_RE.match(str(code).strip())
		if m:
			try:
				mx = max(mx, int(m.group(1)))
			except ValueError:
				continue
	return mx


def assign_fallback_gl_account_number(doc) -> None:
	"""Set ``account_number`` to ``ACCT-######`` when still blank (per company)."""
	if (doc.get("account_number") or "").strip():
		return
	company = doc.get("company")
	if not company:
		return
	n = _max_assigned_suffix(company) + 1
	for _ in range(200):
		candidate = f"{CODE_PREFIX}{n:06d}"
		filters = {"company": company, "account_number": candidate}
		existing = frappe.db.get_value("GL Account", filters, "name")
		if not existing or existing == doc.get("name"):
			doc.account_number = candidate
			return
		n += 1
	doc.account_number = f"{CODE_PREFIX}{frappe.generate_hash(length=6).upper()}"


def _sync_label_fields(account_name: str | None, account_number: str) -> tuple[str, str]:
	name = (account_name or "").strip()
	number = (account_number or "").strip()
	account_label = name or _("Unnamed Account")
	if name and number:
		tree_label = f"{name} - {number}"
	else:
		tree_label = name or number or _("Unnamed Account")
	return account_label, tree_label


def backfill_missing_gl_account_fallback_numbers(limit: int = 10000) -> dict:
	"""Fill empty ``account_number`` for GL rows that have a company (uses ``ACCT-`` series)."""
	if not frappe.db.exists("DocType", "GL Account"):
		return {"ok": False, "skipped": True}
	updated = 0
	while updated < limit:
		rows = frappe.db.sql(
			"""
			SELECT name, company, account_name
			FROM `tabGL Account`
			WHERE company IS NOT NULL AND company != ''
			  AND (account_number IS NULL OR account_number = '')
			ORDER BY creation ASC
			LIMIT 200
			""",
			as_dict=True,
		)
		if not rows:
			break
		for row in rows:
			name = row.name
			company = row.company
			n = _max_assigned_suffix(company) + 1
			candidate = None
			for _ in range(200):
				candidate = f"{CODE_PREFIX}{n:06d}"
				existing = frappe.db.get_value(
					"GL Account",
					{"company": company, "account_number": candidate},
					"name",
				)
				if not existing or existing == name:
					break
				n += 1
			account_label, tree_label = _sync_label_fields(row.account_name, candidate)
			frappe.db.set_value(
				"GL Account",
				name,
				{
					"account_number": candidate,
					"account_label": account_label,
					"tree_label": tree_label,
				},
				update_modified=False,
			)
			updated += 1
			if updated >= limit:
				break
		frappe.db.commit()

	remaining = frappe.db.sql(
		"""
		SELECT COUNT(*) FROM `tabGL Account`
		WHERE company IS NOT NULL AND company != ''
		  AND (account_number IS NULL OR account_number = '')
		"""
	)[0][0]
	return {"ok": True, "updated": updated, "remaining_without_number": int(remaining or 0)}
