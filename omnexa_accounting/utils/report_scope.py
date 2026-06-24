# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Shared company/branch/date scope for accounting Script Reports."""

from __future__ import annotations

import frappe
from frappe import _

from omnexa_core.omnexa_core.branch_access import get_allowed_branches


def normalize_filters(filters=None) -> frappe._dict:
	return frappe._dict(filters or {})


def require_company(filters: frappe._dict) -> None:
	if not filters.get("company"):
		frappe.throw(_("Company filter is required."), title=_("Filters"))


def journal_entry_conditions(filters: frappe._dict, *, alias: str = "je") -> tuple[list[str], frappe._dict]:
	"""SQL fragments for Journal Entry scoped reports."""
	require_company(filters)
	conditions = [f"{alias}.company = %(company)s", f"{alias}.docstatus = 1"]
	if filters.get("branch"):
		conditions.append(f"{alias}.branch = %(branch)s")
	if filters.get("from_date") and filters.get("to_date"):
		conditions.append(f"{alias}.posting_date between %(from_date)s and %(to_date)s")
	elif filters.get("to_date"):
		conditions.append(f"{alias}.posting_date <= %(to_date)s")
	allowed = get_allowed_branches(company=filters.company)
	if allowed is not None:
		if not allowed:
			conditions.append("1=0")
		else:
			filters.allowed_branches = tuple(allowed)
			conditions.append(f"{alias}.branch in %(allowed_branches)s")
	return conditions, filters


def filters_summary(filters: frappe._dict) -> str:
	parts = []
	if filters.get("company"):
		parts.append(f"{_('Company')}: {filters.company}")
	if filters.get("branch"):
		parts.append(f"{_('Branch')}: {filters.branch}")
	if filters.get("from_date"):
		parts.append(f"{_('From')}: {filters.from_date}")
	if filters.get("to_date"):
		parts.append(f"{_('To')}: {filters.to_date}")
	return " · ".join(parts)
