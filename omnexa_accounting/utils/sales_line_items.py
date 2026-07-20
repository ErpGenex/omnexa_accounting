# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Validate sales line items (Item vs company, sales item flag) shared by quotation / order / invoice."""

import frappe
from frappe import _
from frappe.utils import flt


def validate_sales_line_items(doc, company: str, items_attr: str = "items") -> None:
	for row in getattr(doc, items_attr) or []:
		if flt(row.qty) <= 0:
			frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx), title=_("Items"))
		if flt(row.rate) < 0:
			frappe.throw(_("Row {0}: Rate cannot be negative.").format(row.idx), title=_("Items"))
		if not row.item:
			continue
		it = frappe.get_cached_doc("Item", row.item)
		if it.company != company:
			frappe.throw(_("Row {0}: Item belongs to a different company.").format(row.idx), title=_("Item"))
		if it.disabled:
			frappe.throw(_("Row {0}: Item is disabled.").format(row.idx), title=_("Item"))
		if not it.is_sales_item:
			frappe.throw(
				_("Row {0}: Item cannot be sold (Is Sales Item is off).").format(row.idx),
				title=_("Item"),
			)
		if not row.item_code:
			row.item_code = it.item_code
		elif row.item_code != it.item_code:
			frappe.throw(
				_("Row {0}: Item Code must match the selected Item.").format(row.idx),
				title=_("Item"),
			)
		if row.income_account and frappe.db.get_value("GL Account", row.income_account, "company") != company:
			frappe.throw(_("Row {0}: GL Account company mismatch.").format(row.idx), title=_("GL"))
		if row.cost_center:
			cc_co = frappe.db.get_value("Cost Center", row.cost_center, "company")
			if cc_co != company:
				frappe.throw(
					_("Row {0}: Cost Center belongs to a different company.").format(row.idx),
					title=_("Cost Center"),
				)
