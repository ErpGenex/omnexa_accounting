from __future__ import annotations

import frappe
from frappe.utils import flt


def recompute_customer_balance_snapshot(customers: list[str] | None = None) -> int:
	"""Snapshot customer outstanding from submitted Sales Invoices."""
	if not frappe.db.exists("DocType", "Customer"):
		return 0
	meta = frappe.get_meta("Customer")
	if not meta.has_field("balance_snapshot"):
		return 0

	params = {}
	where = "WHERE si.docstatus = 1"
	if customers:
		params["customers"] = tuple(set(customers))
		where += " AND si.customer IN %(customers)s"

	rows = frappe.db.sql(
		f"""
		SELECT si.customer, COALESCE(SUM(si.outstanding_amount),0) AS outstanding
		FROM `tabSales Invoice` si
		{where}
		GROUP BY si.customer
		""",
		params,
		as_dict=True,
	)
	out_map = {r.customer: flt(r.outstanding) for r in rows}

	target = customers or frappe.get_all("Customer", pluck="name")
	updated = 0
	for customer in target:
		frappe.db.set_value("Customer", customer, "balance_snapshot", flt(out_map.get(customer)), update_modified=False)
		updated += 1
	frappe.db.commit()
	return updated


def on_sales_invoice_submit(doc, method=None):
	if getattr(doc, "customer", None):
		recompute_customer_balance_snapshot([doc.customer])


def on_sales_invoice_cancel(doc, method=None):
	if getattr(doc, "customer", None):
		recompute_customer_balance_snapshot([doc.customer])


def on_payment_entry_submit(doc, method=None):
	_refresh_customers_from_payment_entry(doc)


def on_payment_entry_cancel(doc, method=None):
	_refresh_customers_from_payment_entry(doc)


def _refresh_customers_from_payment_entry(doc):
	customers = set()
	if getattr(doc, "party_type", None) == "Customer" and getattr(doc, "party", None):
		customers.add(doc.party)
	for row in doc.get("references") or []:
		if row.reference_doctype == "Sales Invoice" and row.reference_name:
			cust = frappe.db.get_value("Sales Invoice", row.reference_name, "customer")
			if cust:
				customers.add(cust)
	if customers:
		recompute_customer_balance_snapshot(list(customers))

