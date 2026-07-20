#!/usr/bin/env python3
"""Audit Script Report module paths and filter coverage."""
from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.core.doctype.report.report import get_report_module_dotted_path


def run(app: str = "omnexa_accounting") -> dict:
	base = Path(frappe.get_app_path(app)) / app / "report"
	out = {"mismatch": [], "import_errors": [], "no_filters": [], "stubs": []
	}
	for folder in sorted(p for p in base.iterdir() if p.is_dir()):
		jsons = list(folder.glob("*.json"))
		if not jsons:
			continue
		doc = json.loads(jsons[0].read_text(encoding="utf-8"))
		name = doc.get("report_name") or doc.get("name")
		expected = frappe.scrub(name)
		if expected != folder.name:
			out["mismatch"].append({"report": name, "folder": folder.name, "expected": expected
	})
		if not doc.get("filters"):
			out["no_filters"].append(name)
		try:
			path = get_report_module_dotted_path(doc.get("module") or "Omnexa Accounting", name)
			frappe.get_attr(path + ".execute")
		except Exception as exc:
			out["import_errors"].append({"report": name, "error": str(exc)[:200]
	})
		py = folder / f"{folder.name}.py"
		if py.exists() and "return _columns(), []" in py.read_text(encoding="utf-8"):
			out["stubs"].append(name)
	return out


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		import frappe as _f

		_f.init(site=site)
		_f.connect()
	print(json.dumps(run(), indent=2))
