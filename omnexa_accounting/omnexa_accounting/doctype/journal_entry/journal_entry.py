# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from omnexa_accounting.utils.branch import validate_branch_company
from omnexa_accounting.utils.coa_settings import get_coa_settings
from omnexa_accounting.utils.enterprise_codes import ensure_simple_doc_name
from omnexa_accounting.utils.posting import assert_posting_date_open


class JournalEntry(Document):
	def autoname(self):
		ensure_simple_doc_name(self, prefix="JV-", digits=5, flag_name="enterprise_document_numbering")

	def validate(self):
		if self.is_new() and self.amended_from and self.meta.has_field("workflow_state"):
			self.workflow_state = None

		if self.docstatus == 0:
			validate_branch_company(self)
			self._validate_accounts()

	def on_submit(self):
		self._validate_balanced()
		self._validate_accounts()
		assert_posting_date_open(self.company, self.posting_date, is_opening=bool(self.is_opening))

	def _validate_balanced(self):
		total_debit = sum(flt(r.debit) for r in self.accounts or [])
		total_credit = sum(flt(r.credit) for r in self.accounts or [])
		if flt(total_debit - total_credit, 2) != 0:
			frappe.throw(_("Total Debit must equal Total Credit."), title=_("Unbalanced"))

	def _validate_accounts(self):
		settings = get_coa_settings(self.company)
		company_currency = (
			frappe.db.get_value("Company", self.company, "default_currency")
			or frappe.db.get_value("Company", self.company, "currency")
			or ""
		).strip()
		for row in self.accounts or []:
			if not row.account:
				continue
			acc = frappe.db.get_value(
				"GL Account",
				row.account,
				["is_group", "company", "allow_direct_posting", "requires_cost_center", "requires_project", "is_frozen"],
				as_dict=True,
			)
			if not acc:
				frappe.throw(_("Row {0}: Invalid GL Account.").format(row.idx), title=_("Invalid Account"))
			if acc.is_group:
				frappe.throw(
					_("Row {0}: GL Account must be a leaf account.").format(row.idx),
					title=_("Invalid Account"),
				)
			if acc.company != self.company:
				frappe.throw(
					_("Row {0}: Account belongs to a different company.").format(row.idx),
					title=_("Company"),
				)
			if not int(acc.allow_direct_posting or 0):
				frappe.throw(
					_("Row {0}: Direct posting is not allowed for account {1}.").format(row.idx, row.account),
					title=_("Posting Control"),
				)
			if int(acc.requires_cost_center or 0) and not (row.cost_center or "").strip():
				frappe.throw(
					_("Row {0}: Cost Center is required for account {1}.").format(row.idx, row.account),
					title=_("Posting Control"),
				)
			if int(acc.requires_project or 0) and not (row.project or "").strip():
				frappe.throw(
					_("Row {0}: Project is required for account {1}.").format(row.idx, row.account),
					title=_("Posting Control"),
				)
			if int(acc.is_frozen or 0):
				frappe.throw(
					_("Row {0}: Account {1} is frozen and cannot accept new postings.").format(row.idx, row.account),
					title=_("Posting Control"),
				)
			if int(settings.enforce_account_currency_match or 0):
				acc_currency = (frappe.db.get_value("GL Account", row.account, "account_currency") or "").strip()
				if acc_currency and company_currency and acc_currency != company_currency:
					frappe.throw(
						_(
							"Row {0}: Account {1} currency {2} mismatches company currency {3}."
						).format(row.idx, row.account, acc_currency, company_currency),
						title=_("Currency Mismatch"),
					)
