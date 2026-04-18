# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Shared net / tax / grand totals for sales quotations and sales orders (same rules as Sales Invoice lines)."""

import frappe
from frappe import _
from frappe.utils import flt, getdate


def apply_line_item_amounts_and_totals(doc, items_attr: str = "items", posting_date_field: str = "transaction_date") -> None:
	"""Set row.amount and doc.net_total, tax_total, grand_total from items + tax rules."""
	net = 0.0
	tax = 0.0
	posting_date = getdate(getattr(doc, posting_date_field, None) or getdate())
	for row in getattr(doc, items_attr) or []:
		if not row.item and (not row.item_code or not str(row.item_code).strip()):
			frappe.throw(_("Row {0}: Set Item or Item Code.").format(row.idx), title=_("Items"))
		line_net = flt(row.qty) * flt(row.rate)
		row.amount = line_net
		net += line_net
		rule_name = row.tax_rule or getattr(doc, "default_tax_rule", None)
		if rule_name:
			rule = frappe.get_doc("Tax Rule", rule_name)
			if getdate(posting_date) < getdate(rule.valid_from) or getdate(posting_date) > getdate(rule.valid_to):
				frappe.throw(
					_("Row {0}: Tax Rule {1} is not valid on transaction date.").format(row.idx, rule_name),
					title=_("Tax"),
				)
			if rule.tax_type == "standard" and flt(rule.rate):
				tax += line_net * flt(rule.rate) / 100.0
	doc.net_total = net
	doc.tax_total = tax
	doc.grand_total = net + tax
