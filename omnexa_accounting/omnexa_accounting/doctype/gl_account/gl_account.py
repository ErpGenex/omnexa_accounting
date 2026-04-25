# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet

from omnexa_core.omnexa_core.feature_flags import is_feature_enabled


_INCOME_BUCKETS = frozenset(("", "Revenue", "Other Income"))
_EXPENSE_BUCKETS = frozenset(("", "COGS", "Operating Expense", "Other Expense"))
_CASH_FLOW_SECTIONS = frozenset(
	("", "Exclude", "Operating Activities", "Investing Activities", "Financing Activities")
)
_WC_BUCKETS = frozenset(
	("", "Exclude", "Trade Receivables", "Trade Payables", "Inventory", "Other Working Capital")
)

class GLAccount(NestedSet):
	def validate(self):
		self._sync_account_label()
		self._sync_advanced_mode_display_code()
		self._validate_branch_company_link()
		self._validate_pl_bucket()
		self._validate_cash_flow_section()
		self._validate_working_capital_bucket()
		self._validate_stock_valuation_flag()
		filters = {"company": self.company, "account_number": self.account_number}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.get_all("GL Account", filters=filters, limit=1):
			frappe.throw(
				_("Account Number {0} already exists for company {1}").format(
					self.account_number, self.company
				),
				title=_("Duplicate"),
			)

	def _sync_account_label(self):
		number = (self.account_number or "").strip()
		name = (self.account_name or "").strip()
		self.account_label = name or self.name
		if number and name:
			self.tree_label = f"{name} - {number}"
		else:
			self.tree_label = name or number or self.name

	def _sync_advanced_mode_display_code(self):
		"""Advanced-mode display only: CMP-branch-account_number. Never used as logic source."""
		if not is_feature_enabled("enterprise_coa_advanced_mode", default=False):
			return
		if not self.company or not self.account_number:
			return

		co_abbr = frappe.db.get_value("Company", self.company, "abbr") or ""
		br_code = ""
		if self.branch:
			br_code = frappe.db.get_value("Branch", self.branch, "branch_code") or ""
		self.company_code = (co_abbr or "").strip()
		self.branch_code = (br_code or "").strip()
		if self.company_code and self.branch_code:
			self.display_code = f"{self.company_code}-{self.branch_code}-{self.account_number}"
		elif self.company_code:
			self.display_code = f"{self.company_code}-{self.account_number}"
		else:
			self.display_code = self.account_number

	def _validate_branch_company_link(self):
		if not self.branch:
			return
		branch_company = frappe.db.get_value("Branch", self.branch, "company")
		if branch_company and self.company and branch_company != self.company:
			frappe.throw(
				_("Branch {0} does not belong to Company {1}.").format(self.branch, self.company),
				title=_("Branch"),
			)

	def _validate_pl_bucket(self):
		b = (self.pl_bucket or "").strip()
		if self.account_type == "Income":
			if b not in _INCOME_BUCKETS:
				frappe.throw(
					_("P&L Bucket for Income must be empty, Revenue, or Other Income."),
					title=_("P&L Bucket"),
				)
		elif self.account_type == "Expense":
			if b not in _EXPENSE_BUCKETS:
				frappe.throw(
					_("P&L Bucket for Expense must be empty, COGS, Operating Expense, or Other Expense."),
					title=_("P&L Bucket"),
				)
		elif b:
			frappe.throw(_("Set P&L Bucket only for Income or Expense accounts."), title=_("P&L Bucket"))

	def _validate_cash_flow_section(self):
		s = (self.cash_flow_section or "").strip()
		if s not in _CASH_FLOW_SECTIONS:
			frappe.throw(
				_("Cash Flow Section must be empty, Exclude, Operating Activities, Investing Activities, or Financing Activities."),
				title=_("Cash Flow Section"),
			)

	def _validate_working_capital_bucket(self):
		b = (self.working_capital_bucket or "").strip()
		if b not in _WC_BUCKETS:
			frappe.throw(_("Invalid Working Capital Bucket."), title=_("Working Capital"))
		if not b or b == "Exclude":
			return
		at = (self.account_type or "").strip()
		if b == "Trade Payables" and at != "Liability":
			frappe.throw(_("Trade Payables bucket requires Liability account type."), title=_("Working Capital"))
		if b in ("Trade Receivables", "Inventory") and at != "Asset":
			frappe.throw(
				_("{0} bucket requires Asset account type.").format(b),
				title=_("Working Capital"),
			)

	def _validate_stock_valuation_flag(self):
		if not self.is_stock_valuation:
			return
		if self.is_group:
			frappe.throw(_("Stock Valuation GL cannot be set on group accounts."), title=_("GL Account"))
		if (self.account_type or "").strip() != "Asset":
			frappe.throw(_("Stock Valuation GL must be an Asset account."), title=_("GL Account"))
