from __future__ import annotations

import json

import frappe


@frappe.whitelist()
def preview_co_allocation(lines: str | None = None) -> dict:
	"""Wave F — CO cost center allocation preview (no JE)."""
	from omnexa_accounting.co_parity import preview_co_allocation as _preview

	raw = json.loads(lines) if isinstance(lines, str) else (lines or [])
	if not isinstance(raw, list):
		frappe.throw("lines must be a JSON array")
	return _preview(raw)


@frappe.whitelist()
def preview_sector_kpi(scenario: str | None = None, params: str | None = None) -> dict:
	"""SAP Wave C — sector KPI preview (omnexa_core bridge)."""
	from omnexa_core.omnexa_core.vertical_api import preview_sector_kpi as _core_preview

	return _core_preview("accounting", scenario=scenario, params=params)
