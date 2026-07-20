# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Auto-assign ``Item.item_code`` when missing (per company, unique)."""

from __future__ import annotations

import re

import frappe

CODE_PREFIX = "ITEM-"
_CODE_RE = re.compile(r"^ITEM-(\d+)$", re.IGNORECASE)


def _max_assigned_suffix(company: str | None) -> int:
	rows = frappe.db.sql(
		"""
		SELECT item_code
		FROM `tabItem`
		WHERE company <=> %s
		  AND item_code IS NOT NULL
		  AND item_code != ''
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


def assign_item_code_if_missing(doc) -> None:
	if (doc.get("item_code") or "").strip():
		return
	company = doc.get("company")
	n = _max_assigned_suffix(company) + 1
	for _ in range(200):
		candidate = f"{CODE_PREFIX}{n:06d}"
		exists = frappe.db.get_value(
			"Item",
			{"company": company, "item_code": candidate
	},
			"name",
		)
		if not exists or exists == doc.get("name"):
			doc.item_code = candidate
			return
		n += 1
	doc.item_code = f"{CODE_PREFIX}{frappe.generate_hash(length=6).upper()}"


def backfill_missing_item_codes(limit: int = 10000) -> dict:
	if not frappe.db.exists("DocType", "Item"):
		return {"ok": False, "skipped": True
	}
	updated = 0
	while updated < limit:
		rows = frappe.db.sql(
			"""
			SELECT name, company
			FROM `tabItem`
			WHERE item_code IS NULL OR item_code = ''
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
				exists = frappe.db.get_value(
					"Item",
					{"company": company, "item_code": candidate
	},
					"name",
				)
				if not exists or exists == name:
					break
				n += 1
			frappe.db.set_value("Item", name, "item_code", candidate, update_modified=False)
			updated += 1
			if updated >= limit:
				break
		frappe.db.commit()

	remaining = frappe.db.sql(
		"""
		SELECT COUNT(*) FROM `tabItem`
		WHERE item_code IS NULL OR item_code = ''
		"""
	)[0][0]
	return {"ok": True, "updated": updated, "remaining_without_code": int(remaining or 0)
	}
