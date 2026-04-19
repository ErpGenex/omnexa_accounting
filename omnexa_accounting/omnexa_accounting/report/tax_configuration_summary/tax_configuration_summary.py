# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 130},
		{"label": _("Code / name"), "fieldname": "code", "fieldtype": "Data", "width": 160},
		{"label": _("Title"), "fieldname": "title", "fieldtype": "Data", "width": 200},
		{"label": _("Treatment"), "fieldname": "treatment", "fieldtype": "Data", "width": 120},
		{"label": _("Rate %"), "fieldname": "rate", "fieldtype": "Float", "width": 90},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 160},
		{"label": _("Valid from"), "fieldname": "valid_from", "fieldtype": "Date", "width": 110},
		{"label": _("Valid to"), "fieldname": "valid_to", "fieldtype": "Date", "width": 110},
		{"label": _("Notes"), "fieldname": "notes", "fieldtype": "Data", "width": 220},
	]
	rows: list[dict] = []

	if frappe.db.exists("DocType", "Tax Category"):
		for r in frappe.get_all(
			"Tax Category",
			fields=[
				"name",
				"category_code",
				"title",
				"default_tax_treatment",
				"is_reverse_charge",
			],
			order_by="category_code asc",
		):
			note = ""
			if r.is_reverse_charge:
				note = _("Reverse charge")
			rows.append(
				{
					"section": _("Tax category"),
					"code": r.category_code,
					"title": r.title,
					"treatment": r.default_tax_treatment or "",
					"rate": None,
					"company": "",
					"valid_from": None,
					"valid_to": None,
					"notes": note,
				}
			)

	rule_filters: dict = {}
	if filters.get("company"):
		rule_filters["company"] = filters.company

	for r in frappe.get_all(
		"Tax Rule",
		filters=rule_filters or None,
		fields=[
			"name",
			"title",
			"company",
			"tax_type",
			"rate",
			"tax_category",
			"valid_from",
			"valid_to",
		],
		order_by="company asc, tax_type asc, valid_from asc",
	):
		rows.append(
			{
				"section": _("Tax rule"),
				"code": r.name,
				"title": r.title,
				"treatment": r.tax_type or "",
				"rate": r.rate,
				"company": r.company or "",
				"valid_from": r.valid_from,
				"valid_to": r.valid_to,
				"notes": r.tax_category or "",
			}
		)

	return columns, rows
