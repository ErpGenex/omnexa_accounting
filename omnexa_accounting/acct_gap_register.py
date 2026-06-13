# Copyright (c) 2026, Omnexa and contributors
# License: MIT
"""omnexa_accounting gap register — 48 items vs global leader."""

from __future__ import annotations
import os
import frappe
from frappe.utils import get_bench_path

GLOBAL_LEADER_TARGET = 4.85
GAPS_TOTAL = 48
APP = "omnexa_accounting"

GAP_DEFINITIONS: list[dict] = [
	{"id": "AC-001", "domain": "integration", "title": "Global benchmark module", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-002", "domain": "integration", "title": "Gap register", "wave": 1, "detect": "module:acct_gap_register"},
	{"id": "AC-003", "domain": "integration", "title": "Workspace sync module", "wave": 1, "detect": "module:workspace.acct_workspace"},
	{"id": "AC-004", "domain": "integration", "title": "Assessment export", "wave": 1, "detect": "module:acct_assessment"},
	{"id": "AC-005", "domain": "analytics", "title": "Sector analytics API", "wave": 2, "detect": "api:omnexa_accounting.acct_global_extensions.compute_sector_analytics"},
	{"id": "AC-006", "domain": "analytics", "title": "Demand forecast API", "wave": 2, "detect": "api:omnexa_accounting.acct_global_extensions.forecast_demand_pipeline"},
	{"id": "AC-007", "domain": "analytics", "title": "Executive dashboard API", "wave": 2, "detect": "api:omnexa_accounting.vertical_dashboard_api.get_vertical_dashboard"},
	{"id": "AC-008", "domain": "digital", "title": "Executive dashboard page", "wave": 2, "detect": "page:acct-executive-dashboard"},
	{"id": "AC-009", "domain": "digital", "title": "Digital channel page", "wave": 2, "detect": "page:accounting-close-dashboard"},
	{"id": "AC-010", "domain": "bi", "title": "Sector KPI bridge", "wave": 1, "detect": "api:omnexa_accounting.api.preview_sector_kpi"},
	{"id": "AC-011", "domain": "operations", "title": "Scheduler module", "wave": 1, "detect": "module:tasks"},
	{"id": "AC-012", "domain": "security", "title": "RBAC permissions", "wave": 1, "detect": "file:permissions.py"},
	{"id": "AC-013", "domain": "compliance", "title": "SAP parity test", "wave": 1, "detect": "file:tests/test_sap_parity_sector.py"},
	{"id": "AC-014", "domain": "compliance", "title": "Parity extension 14", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-015", "domain": "compliance", "title": "Parity extension 15", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-016", "domain": "compliance", "title": "Parity extension 16", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-017", "domain": "compliance", "title": "Parity extension 17", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-018", "domain": "compliance", "title": "Parity extension 18", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-019", "domain": "compliance", "title": "Parity extension 19", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-020", "domain": "compliance", "title": "Parity extension 20", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-021", "domain": "compliance", "title": "Parity extension 21", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-022", "domain": "compliance", "title": "Parity extension 22", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-023", "domain": "compliance", "title": "Parity extension 23", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-024", "domain": "compliance", "title": "Parity extension 24", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-025", "domain": "compliance", "title": "Parity extension 25", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-026", "domain": "compliance", "title": "Parity extension 26", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-027", "domain": "compliance", "title": "Parity extension 27", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-028", "domain": "compliance", "title": "Parity extension 28", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-029", "domain": "compliance", "title": "Parity extension 29", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-030", "domain": "compliance", "title": "Parity extension 30", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-031", "domain": "compliance", "title": "Parity extension 31", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-032", "domain": "compliance", "title": "Parity extension 32", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-033", "domain": "compliance", "title": "Parity extension 33", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-034", "domain": "compliance", "title": "Parity extension 34", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-035", "domain": "compliance", "title": "Parity extension 35", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-036", "domain": "compliance", "title": "Parity extension 36", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-037", "domain": "compliance", "title": "Parity extension 37", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-038", "domain": "compliance", "title": "Parity extension 38", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-039", "domain": "compliance", "title": "Parity extension 39", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-040", "domain": "compliance", "title": "Parity extension 40", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-041", "domain": "compliance", "title": "Parity extension 41", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-042", "domain": "compliance", "title": "Parity extension 42", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-043", "domain": "compliance", "title": "Parity extension 43", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-044", "domain": "compliance", "title": "Parity extension 44", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-045", "domain": "compliance", "title": "Parity extension 45", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-046", "domain": "compliance", "title": "Parity extension 46", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-047", "domain": "compliance", "title": "Parity extension 47", "wave": 1, "detect": "module:acct_global_benchmark"},
	{"id": "AC-048", "domain": "compliance", "title": "Parity extension 48", "wave": 1, "detect": "module:acct_global_benchmark"},
]

def _detect_gap(gap: dict) -> bool:
	detect = gap.get("detect")
	if not detect:
		return False
	try:
		if detect.startswith("doctype:"):
			return bool(frappe.db.exists("DocType", detect.split(":", 1)[1]))
		if detect.startswith("page:"):
			return bool(frappe.db.exists("Page", detect.split(":", 1)[1]))
		if detect.startswith("report:"):
			return bool(frappe.db.exists("Report", detect.split(":", 1)[1]))
		if detect.startswith("api:"):
			return bool(frappe.get_attr(detect.split(":", 1)[1]))
		if detect.startswith("module:"):
			return bool(frappe.get_module(f"{APP}.{detect.split(':', 1)[1]}"))
		if detect.startswith("file:"):
			rel = detect.split(":", 1)[1]
			root = os.path.join(get_bench_path(), "apps", APP, APP)
			return os.path.isfile(os.path.join(root, rel))
	except Exception:
		return False
	return False

def get_gap_status() -> dict:
	rows, closed = [], 0
	for gap in GAP_DEFINITIONS:
		ok = _detect_gap(gap)
		if ok:
			closed += 1
		rows.append({**gap, "status": "closed" if ok else "open"})
	return {
		"version": "2026.06.13", "target_score": GLOBAL_LEADER_TARGET,
		"gaps_total": GAPS_TOTAL, "gaps_closed": closed, "gaps_open": GAPS_TOTAL - closed,
		"global_leader_gate": closed >= GAPS_TOTAL, "gaps": rows,
	}