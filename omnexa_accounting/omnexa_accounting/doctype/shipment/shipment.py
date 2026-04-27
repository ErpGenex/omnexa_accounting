# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Shipment(Document):
	def validate(self):
		if self.invoice_doctype not in ("Sales Invoice", "Purchase Invoice"):
			frappe.throw(_("Shipment can only be linked to Sales or Purchase Invoice."))
		if self.invoice_doctype and self.invoice_name and not frappe.db.exists(
			self.invoice_doctype, self.invoice_name
		):
			frappe.throw(_("Referenced invoice does not exist."))
		if self.carrier and not frappe.db.exists("Shipment Carrier", self.carrier):
			frappe.throw(_("Shipment Carrier does not exist."))
		if self.company and self.carrier:
			carrier_company = frappe.db.get_value("Shipment Carrier", self.carrier, "company")
			if carrier_company and carrier_company != self.company:
				frappe.throw(_("Shipment Carrier belongs to a different company."))

