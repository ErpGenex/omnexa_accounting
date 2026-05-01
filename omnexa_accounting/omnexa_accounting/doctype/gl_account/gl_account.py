# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils import cint

from omnexa_core.omnexa_core.feature_flags import is_feature_enabled
from omnexa_accounting.utils.coa_settings import get_coa_settings, get_company_masks, get_manual_override_roles


_INCOME_BUCKETS = frozenset(("", "Revenue", "Other Income"))
_EXPENSE_BUCKETS = frozenset(("", "COGS", "Operating Expense", "Other Expense"))
_CASH_FLOW_SECTIONS = frozenset(
	("", "Exclude", "Operating Activities", "Investing Activities", "Financing Activities")
)
_WC_BUCKETS = frozenset(
	("", "Exclude", "Trade Receivables", "Trade Payables", "Inventory", "Other Working Capital", "Receivable", "Payable", "Other")
)
_ACCOUNT_CLASSES = frozenset(("Asset", "Liability", "Equity", "Revenue", "Expense"))


def _normalize_account_class(value: str | None) -> str:
	v = (value or "").strip()
	if v == "Income":
		return "Revenue"
	return v


def _next_number_from_mask(mask: str, company: str) -> str:
	mask = (mask or "").strip()
	if not mask:
		return ""
	x_count = mask.count("x")
	if x_count <= 0:
		return mask
	prefix = mask.split("x", 1)[0]
	length = len(mask)
	rows = frappe.get_all(
		"GL Account",
		filters={"company": company},
		fields=["account_number"],
		limit_page_length=200000,
	)
	max_suffix = 0
	for row in rows:
		number = (row.get("account_number") or "").strip()
		if len(number) != length or not number.startswith(prefix):
			continue
		suffix = number[len(prefix) :]
		if suffix.isdigit():
			max_suffix = max(max_suffix, int(suffix))
	next_suffix = str(max_suffix + 1).zfill(x_count)
	return f"{prefix}{next_suffix}"


class GLAccount(NestedSet):
	def validate(self):
		self._normalize_class_fields()
		self._apply_auto_numbering()
		self._enforce_manual_override_permission()
		self._sync_account_label()
		self._sync_advanced_mode_display_code()
		self._validate_branch_company_link()
		self._validate_parent_class_hierarchy()
		self._validate_posting_type_consistency()
		self._validate_financial_controls()
		self._validate_pl_bucket()
		self._apply_cash_flow_defaults()
		self._apply_working_capital_defaults()
		self._validate_cash_flow_section()
		self._validate_working_capital_bucket()
		self._validate_stock_valuation_flag()
		self._validate_frozen_guardrails()
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

	def _normalize_class_fields(self):
		self.account_class = _normalize_account_class(self.account_class or self.account_type)
		self.account_type = _normalize_account_class(self.account_type or self.account_class)
		if self.account_class and self.account_class not in _ACCOUNT_CLASSES:
			frappe.throw(_("Account Class must be Asset, Liability, Equity, Revenue, or Expense."))
		if self.account_type and self.account_type not in _ACCOUNT_CLASSES:
			frappe.throw(_("Account Type must be Asset, Liability, Equity, Revenue, or Expense."))
		if self.account_class and self.account_type and self.account_class != self.account_type:
			# Keep backward compatibility: class is the governing dimension.
			self.account_type = self.account_class

	def _apply_auto_numbering(self):
		if self.account_number:
			return
		if not self.company or not self.account_class:
			return
		mask = get_company_masks(self.company).get(self.account_class)
		self.account_number = _next_number_from_mask(mask, self.company) if mask else self.account_number

	def _enforce_manual_override_permission(self):
		if not cint(getattr(self, "manual_number_override", 0)):
			return
		roles = set(frappe.get_roles(frappe.session.user))
		allowed_roles = get_manual_override_roles(self.company)
		if not (allowed_roles & roles):
			frappe.throw(_("Manual number override requires Accounts Manager or System Manager role."))

	def _sync_account_label(self):
		number = (self.account_number or "").strip()
		name = (self.account_name or "").strip()
		self.account_label = name or _("Unnamed Account")
		if name and number:
			self.tree_label = f"{name} - {number}"
		else:
			self.tree_label = name or number or _("Unnamed Account")

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

	def _validate_parent_class_hierarchy(self):
		if not self.parent_account:
			return
		parent = frappe.db.get_value(
			"GL Account", self.parent_account, ["account_class", "account_type", "is_group"], as_dict=True
		)
		if not parent:
			return
		parent_class = _normalize_account_class((parent.account_class or parent.account_type or "").strip())
		if parent_class and self.account_class and parent_class != self.account_class:
			frappe.throw(
				_("Invalid hierarchy: child Account Class {0} must match parent Account Class {1}.").format(
					self.account_class, parent_class
				),
				title=_("Account Hierarchy"),
			)
		if not cint(parent.is_group):
			frappe.throw(_("Parent Account must be a Header/Group account."), title=_("Account Hierarchy"))

	def _validate_posting_type_consistency(self):
		pt = (self.posting_type or "Posting").strip()
		if pt == "Header":
			self.is_group = 1
			self.allow_direct_posting = 0
		elif pt in ("Posting", "Control Account"):
			self.is_group = 0
		if cint(self.is_group) and pt != "Header":
			self.posting_type = "Header"
			self.allow_direct_posting = 0

	def _validate_financial_controls(self):
		settings = get_coa_settings(self.company)
		if cint(self.is_bank_account) and cint(self.is_cash_account):
			frappe.throw(_("An account cannot be both Bank and Cash at the same time."))
		if (self.posting_type or "").strip() == "Control Account" and not cint(self.is_reconcilable):
			frappe.throw(_("Control Account must be marked as Reconcilable."))
		if self.account_currency and not frappe.db.exists("Currency", self.account_currency):
			frappe.throw(_("Account Currency is invalid."))
		if cint(self.intercompany_account) and cint(settings.require_group_reporting_tag_for_intercompany or 0):
			if not (self.group_reporting_tag or "").strip():
				frappe.throw(_("Intercompany accounts require Group Reporting Tag by policy."))

	def _validate_pl_bucket(self):
		b = (self.pl_bucket or "").strip()
		account_type = _normalize_account_class(self.account_type)
		if account_type == "Revenue":
			if b not in _INCOME_BUCKETS:
				frappe.throw(
					_("P&L Bucket for Income must be empty, Revenue, or Other Income."),
					title=_("P&L Bucket"),
				)
		elif account_type == "Expense":
			if b not in _EXPENSE_BUCKETS:
				frappe.throw(
					_("P&L Bucket for Expense must be empty, COGS, Operating Expense, or Other Expense."),
					title=_("P&L Bucket"),
				)
		elif b:
			frappe.throw(_("Set P&L Bucket only for Income or Expense accounts."), title=_("P&L Bucket"))

	def _apply_cash_flow_defaults(self):
		if (self.cash_flow_section or "").strip():
			return
		name = (self.account_name or "").lower()
		if cint(self.is_bank_account) or cint(self.is_cash_account):
			self.cash_flow_section = "Operating Activities"
			return
		if "fixed asset" in name or "property" in name or "equipment" in name:
			self.cash_flow_section = "Investing Activities"

	def _apply_working_capital_defaults(self):
		if (self.working_capital_bucket or "").strip():
			return
		name = (self.account_name or "").lower()
		if "receivable" in name:
			self.working_capital_bucket = "Receivable"
		elif "payable" in name:
			self.working_capital_bucket = "Payable"
		elif "inventory" in name or "stock" in name:
			self.working_capital_bucket = "Inventory"
		else:
			self.working_capital_bucket = "Other"

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
		if b in ("Receivable", "Inventory") and at != "Asset":
			frappe.throw(_("{0} bucket requires Asset account type.").format(b), title=_("Working Capital"))
		if b == "Payable" and at != "Liability":
			frappe.throw(_("Payable bucket requires Liability account type."), title=_("Working Capital"))

	def _validate_stock_valuation_flag(self):
		if not self.is_stock_valuation:
			return
		if self.is_group:
			frappe.throw(_("Stock Valuation GL cannot be set on group accounts."), title=_("GL Account"))
		if (self.account_type or "").strip() != "Asset":
			frappe.throw(_("Stock Valuation GL must be an Asset account."), title=_("GL Account"))

	def _validate_frozen_guardrails(self):
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before or not cint(before.is_frozen):
			return
		protected_fields = (
			"account_number",
			"account_name",
			"account_class",
			"account_type",
			"posting_type",
			"parent_account",
			"company",
			"branch",
		)
		for fieldname in protected_fields:
			if (before.get(fieldname) or "") != (self.get(fieldname) or ""):
				frappe.throw(_("Frozen account cannot change core structure fields."), title=_("Is Frozen"))


@frappe.whitelist()
def create_gl_account(payload: dict):
	"""API endpoint for controlled GL account creation."""
	if not isinstance(payload, dict):
		frappe.throw(_("payload must be a JSON object"))
	doc = frappe.get_doc({"doctype": "GL Account", **payload})
	doc.insert(ignore_permissions=True)
	return {"ok": True, "name": doc.name, "account_number": doc.account_number}
