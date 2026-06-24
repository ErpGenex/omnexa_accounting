# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Sync top accounting report JSON filters from omnexa_core specs."""


def execute():
	import json
	from pathlib import Path

	import frappe
	from frappe.modules.import_file import import_file_by_path

	from omnexa_core.omnexa_core.report_print.report_filter_specs import ACCOUNTING_REPORT_FILTERS

	base = Path(frappe.get_app_path("omnexa_accounting")) / "omnexa_accounting" / "report"
	updated = 0
	for report_name, filters in ACCOUNTING_REPORT_FILTERS.items():
		slug = frappe.scrub(report_name)
		json_path = base / slug / f"{slug}.json"
		if not json_path.exists():
			# alias folder for parentheses reports
			for alt in base.glob(f"*/{slug}.json"):
				json_path = alt
				break
		if not json_path.exists():
			continue
		doc = json.loads(json_path.read_text(encoding="utf-8"))
		if doc.get("filters") == filters:
			continue
		doc["filters"] = filters
		json_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
		import_file_by_path(str(json_path), force=True)
		updated += 1
	if updated:
		frappe.db.commit()
	return {"updated": updated}
