# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Lightweight SOP-aligned desk signals (extend with email / Notification DocType as needed)."""

import frappe
from frappe import _


def on_purchase_order_submit(doc, method=None):
	if method != "on_submit":
		return
	try:
		frappe.publish_realtime(
			"omnexa_sop_alert",
			{
				"doctype": doc.doctype,
				"name": doc.name,
				"title": _("Purchase Order submitted"),
				"supplier": getattr(doc, "supplier", None),
			},
			user=doc.owner,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa: sop_hooks on_purchase_order_submit")
