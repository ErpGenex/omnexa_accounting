# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Allocate cumulative GL balance on each **Inventory Control GL** across items by stock qty share."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("company"):
		frappe.throw(_("Company is required."), title=_("Filters"))
	if not filters.get("as_of_date"):
		frappe.throw(_("As Of Date is required."), title=_("Filters"))

	items = frappe.db.sql(
		"""
		SELECT name, item_code, item_name, inventory_control_account, COALESCE(current_stock_qty, 0) AS current_stock_qty
		FROM `tabItem`
		WHERE IFNULL(disabled, 0) = 0
			AND IFNULL(inventory_control_account, '') != ''
			AND (company = %(company)s OR IFNULL(company, '') = '')
		""",
		{"company": filters.company},
		as_dict=True,
	)
	if not items:
		return _cols(), [], _("No items with Inventory Control GL set."), None, None, False

	accounts = list({i.inventory_control_account for i in items})
	params = {"company": filters.company, "as_of": filters.as_of_date, "accounts": tuple(accounts)}
	balances = dict(
		frappe.db.sql(
			"""
			SELECT jea.account, SUM(jea.debit - jea.credit)
			FROM `tabJournal Entry` je
			INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
			WHERE je.docstatus = 1
				AND je.company = %(company)s
				AND je.posting_date <= %(as_of)s
				AND jea.account IN %(accounts)s
			GROUP BY jea.account
			""",
			params,
		)
	)

	by_account = {}
	for it in items:
		acc = it.inventory_control_account
		by_account.setdefault(acc, []).append(it)

	data = []
	for acc, group in by_account.items():
		gl_bal = flt(balances.get(acc))
		total_qty = sum(flt(i.current_stock_qty) for i in group) or 0.0
		for it in group:
			qty = flt(it.current_stock_qty)
			share = (qty / total_qty) if total_qty else 0.0
			val = gl_bal * share
			data.append(
				{
					"gl_account": acc,
					"item": it.name,
					"item_code": it.item_code,
					"item_name": it.item_name or "",
					"qty": qty,
					"allocated_value": flt(val, 2),
				}
			)

	data.sort(key=lambda r: (r["gl_account"], r["item_code"] or ""))

	msg = _(
		"GL balance is cumulative debit−credit on the control account up to As Of Date; value is split across items on that account by **Current Stock Qty** share. "
		"Requires consistent mapping; not a substitute for perpetual inventory subledger."
	)
	return _cols(), data, msg, None, None, False


def _cols():
	return [
		{"label": _("Control GL"), "fieldname": "gl_account", "fieldtype": "Link", "options": "GL Account", "width": 160},
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 160},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Data", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("Allocated GL value"), "fieldname": "allocated_value", "fieldtype": "Currency", "width": 150},
	]
