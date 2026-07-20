from __future__ import annotations

import frappe
from frappe.utils import flt


def _sum_in_out_for_warehouse(warehouse: str) -> tuple[float, float]:
	row = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(CASE WHEN sei.t_warehouse = %(warehouse)s THEN sei.qty ELSE 0 END), 0) AS in_qty,
			COALESCE(SUM(CASE WHEN sei.s_warehouse = %(warehouse)s THEN sei.qty ELSE 0 END), 0) AS out_qty,
			COALESCE(SUM(CASE WHEN sei.t_warehouse = %(warehouse)s THEN IFNULL(sei.amount,0) ELSE 0 END), 0) AS in_val,
			COALESCE(SUM(CASE WHEN sei.s_warehouse = %(warehouse)s THEN IFNULL(sei.amount,0) ELSE 0 END), 0) AS out_val
		FROM `tabStock Entry Item` sei
		INNER JOIN `tabStock Entry` se ON se.name = sei.parent
		WHERE se.docstatus = 1
		  AND (sei.t_warehouse = %(warehouse)s OR sei.s_warehouse = %(warehouse)s)
		""",
		{"warehouse": warehouse
	},
		as_dict=True,
	)
	r = row[0] if row else {}
	qty = flt(r.get("in_qty")) - flt(r.get("out_qty"))
	val = flt(r.get("in_val")) - flt(r.get("out_val"))
	return qty, val


def recompute_warehouse_snapshot(warehouses: list[str] | None = None) -> int:
	"""Recompute stock qty/value snapshot on Warehouse from submitted Stock Entries."""
	if not frappe.db.exists("DocType", "Warehouse"):
		return 0
	meta = frappe.get_meta("Warehouse")
	if not (meta.has_field("stock_qty_snapshot") and meta.has_field("stock_value_snapshot")):
		return 0

	target = warehouses or frappe.get_all("Warehouse", pluck="name")
	updated = 0
	for wh in target:
		qty, val = _sum_in_out_for_warehouse(wh)
		frappe.db.set_value("Warehouse", wh, "stock_qty_snapshot", qty, update_modified=False)
		frappe.db.set_value("Warehouse", wh, "stock_value_snapshot", val, update_modified=False)
		updated += 1
	frappe.db.commit()
	return updated


def recompute_warehouse_snapshot_for_stock_entry(doc):
	warehouses = set()
	for row in doc.get("items") or []:
		if row.s_warehouse:
			warehouses.add(row.s_warehouse)
		if row.t_warehouse:
			warehouses.add(row.t_warehouse)
	if doc.get("from_warehouse"):
		warehouses.add(doc.from_warehouse)
	if doc.get("to_warehouse"):
		warehouses.add(doc.to_warehouse)
	if warehouses:
		recompute_warehouse_snapshot(list(warehouses))


@frappe.whitelist()
def get_warehouse_item_balances(warehouse: str, company: str | None = None) -> dict:
	"""Return item-wise balance for a warehouse (qty/value)."""
	if not warehouse:
		return {"ok": True, "rows": []
	}
	wh_company = frappe.db.get_value("Warehouse", warehouse, "company")
	if company and wh_company and company != wh_company:
		return {"ok": True, "rows": []
	}

	rows = frappe.db.sql(
		"""
		SELECT
			sei.item,
			MAX(sei.item_code) AS item_code,
			COALESCE(SUM(CASE WHEN sei.t_warehouse = %(warehouse)s THEN sei.qty ELSE 0 END), 0)
			  - COALESCE(SUM(CASE WHEN sei.s_warehouse = %(warehouse)s THEN sei.qty ELSE 0 END), 0) AS qty_balance,
			COALESCE(SUM(CASE WHEN sei.t_warehouse = %(warehouse)s THEN IFNULL(sei.amount,0) ELSE 0 END), 0)
			  - COALESCE(SUM(CASE WHEN sei.s_warehouse = %(warehouse)s THEN IFNULL(sei.amount,0) ELSE 0 END), 0) AS value_balance
		FROM `tabStock Entry Item` sei
		INNER JOIN `tabStock Entry` se ON se.name = sei.parent
		WHERE se.docstatus = 1
		  AND (sei.t_warehouse = %(warehouse)s OR sei.s_warehouse = %(warehouse)s)
		GROUP BY sei.item
		HAVING ABS(qty_balance) > 0.000001 OR ABS(value_balance) > 0.000001
		ORDER BY value_balance DESC, qty_balance DESC
		""",
		{"warehouse": warehouse
	},
		as_dict=True,
	)
	return {"ok": True, "rows": rows
	}

