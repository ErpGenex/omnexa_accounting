# Copyright (c) 2026, ErpGenEx
"""Wave F — CO-PA / cost center allocation preview (SAP CO)."""

from __future__ import annotations

from typing import Any

from frappe.utils import flt


def preview_co_allocation(lines: list[dict[str, Any]]) -> dict[str, Any]:
	"""Preview split of amounts across cost centers (no GL posting)."""
	by_cc: dict[str, float] = {}
	total = 0.0
	for row in lines or []:
		if not isinstance(row, dict):
			continue
		cc = (row.get("cost_center") or "UNASSIGNED").strip()
		amt = flt(row.get("amount") or 0)
		by_cc[cc] = by_cc.get(cc, 0.0) + amt
		total += amt
	shares = {cc: round(amt / total, 4) if total else 0 for cc, amt in by_cc.items()}
	return {
		"total_amount": total,
		"cost_centers": by_cc,
		"shares": shares,
		"line_count": len(lines or []),
		"sap_module": "CO-PA"
	}
