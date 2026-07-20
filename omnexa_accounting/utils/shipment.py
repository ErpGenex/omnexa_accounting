# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _


def _carrier_tracking_url(carrier: str, tracking_number: str) -> str:
	template = (frappe.db.get_value("Shipment Carrier", carrier, "tracking_url_template") or "").strip()
	if not template or not tracking_number:
		return ""
	return template.replace("{tracking_number}", tracking_number)


@frappe.whitelist()
def create_shipment_from_invoice(doctype: str, docname: str, carrier=None):
	if doctype not in ("Sales Invoice", "Purchase Invoice"):
		frappe.throw(_("Only Sales/Purchase invoices can create shipments."))
	if not frappe.db.exists(doctype, docname):
		frappe.throw(_("Invoice not found."))

	inv = frappe.get_doc(doctype, docname)
	if getattr(inv, "shipment_record", None) and frappe.db.exists("Shipment", inv.shipment_record):
		return {"shipment": inv.shipment_record, "already_exists": True
	}

	carrier_name = carrier or getattr(inv, "shipment_carrier", None)
	if not carrier_name:
		frappe.throw(_("Set Shipment Carrier on invoice first."))
	if not frappe.db.exists("Shipment Carrier", carrier_name):
		frappe.throw(_("Shipment Carrier not found."))

	shipment = frappe.new_doc("Shipment")
	shipment.company = inv.company
	shipment.branch = getattr(inv, "branch", None)
	shipment.invoice_doctype = doctype
	shipment.invoice_name = inv.name
	shipment.carrier = carrier_name
	shipment.shipping_cost = getattr(inv, "shipping_cost", 0) or 0
	shipment.status = "Booked"
	shipment.insert(ignore_permissions=True)

	if inv.meta.has_field("shipment_record"):
		inv.db_set("shipment_record", shipment.name, update_modified=False)
	if inv.meta.has_field("shipment_reference") and not getattr(inv, "shipment_reference", None):
		inv.db_set("shipment_reference", shipment.name, update_modified=False)

	return {"shipment": shipment.name, "already_exists": False
	}


@frappe.whitelist()
def update_shipment_tracking(shipment: str, tracking_number: str):
	if not frappe.db.exists("Shipment", shipment):
		frappe.throw(_("Shipment not found."))
	doc = frappe.get_doc("Shipment", shipment)
	doc.tracking_number = (tracking_number or "").strip()
	doc.tracking_url = _carrier_tracking_url(doc.carrier, doc.tracking_number)
	doc.save(ignore_permissions=True)

	if doc.invoice_doctype and doc.invoice_name and frappe.db.exists(doc.invoice_doctype, doc.invoice_name):
		inv = frappe.get_doc(doc.invoice_doctype, doc.invoice_name)
		if inv.meta.has_field("shipment_reference") and not getattr(inv, "shipment_reference", None):
			inv.db_set("shipment_reference", doc.name, update_modified=False)
		if inv.meta.has_field("shipment_record"):
			inv.db_set("shipment_record", doc.name, update_modified=False)

	return {"ok": True, "tracking_url": doc.tracking_url
	}

