# Copyright (c) 2026, Omnexa and contributors
# License: MIT

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CompanyPartnerLegalSetup(Document):
	def validate(self):
		self._validate_funding_partner()
		self._validate_partner_accounts_company()

	def _validate_funding_partner(self) -> None:
		funders = [row for row in self.partners or [] if row.is_funding_partner]
		if len(funders) != 1:
			frappe.throw(_("Exactly one partner must be marked as Funding Partner."))

	def _validate_partner_accounts_company(self) -> None:
		for row in self.partners or []:
			for field in ("partner_current_account", "due_from_partner_account"):
				acc = row.get(field)
				if not acc:
					continue
				acc_company = frappe.db.get_value("GL Account", acc, "company")
				if acc_company and acc_company != self.company:
					frappe.throw(
						_("Row {0}: account {1} must belong to company {2}.").format(
							row.idx, acc, self.company
						)
					)


def get_funding_partner(doc: CompanyPartnerLegalSetup | frappe._dict) -> frappe._dict | None:
	for row in doc.partners or []:
		if row.is_funding_partner:
			return row
	return None


def get_liable_partners(doc: CompanyPartnerLegalSetup | frappe._dict) -> list[frappe._dict]:
	return [row for row in (doc.partners or []) if not row.is_funding_partner]


def get_primary_liable_partner(doc: CompanyPartnerLegalSetup | frappe._dict) -> frappe._dict | None:
	liable = get_liable_partners(doc)
	if not liable:
		return None
	with_due = [row for row in liable if row.due_from_partner_account]
	if with_due:
		return sorted(with_due, key=lambda r: flt(r.ownership_percent), reverse=True)[0]
	return sorted(liable, key=lambda r: flt(r.ownership_percent), reverse=True)[0]


@frappe.whitelist()
def get_setup_for_company(company: str) -> dict:
	"""Return partner legal setup + resolved report filter defaults."""
	if not frappe.db.exists("Company Partner Legal Setup", company):
		return {"found": False, "company": company
	}
	doc = frappe.get_doc("Company Partner Legal Setup", company)
	funder = get_funding_partner(doc)
	liable = get_primary_liable_partner(doc)
	return {
		"found": True,
		"company": doc.company,
		"branch": doc.branch,
		"default_from_date": str(doc.default_from_date) if doc.default_from_date else None,
		"default_to_date": str(doc.default_to_date) if doc.default_to_date else None,
		"legal_case_reference": doc.legal_case_reference,
		"partners": [
			{
				"partner_name": row.partner_name,
				"partner_name_ar": row.partner_name_ar,
				"ownership_percent": flt(row.ownership_percent),
				"is_funding_partner": row.is_funding_partner,
				"partner_current_account": row.partner_current_account,
				"due_from_partner_account": row.due_from_partner_account
	}
			for row in doc.partners or []
		],
		"funding_partner": funder.partner_name if funder else None,
		"liable_partner": liable.partner_name if liable else None,
		"liable_ownership_percent": flt(liable.ownership_percent) if liable else 0
	}
