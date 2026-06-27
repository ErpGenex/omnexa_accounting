# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate

from omnexa_core.omnexa_core.constants import (
	DOC_STATUS_ACCEPTED,
	DOC_STATUS_QUEUED,
	DOC_STATUS_REJECTED,
	DOC_STATUS_SENT,
	DOC_STATUS_SUBMITTED,
)
from omnexa_accounting.utils.branch import validate_branch_company
from omnexa_accounting.utils.tax_rule_resolver import apply_invoice_tax_rule_defaults
from omnexa_accounting.utils.currency import apply_multi_currency_to_invoice
from omnexa_accounting.utils.party import get_default_sales_invoice_due_days, get_effective_credit_days
from omnexa_accounting.utils.posting import assert_posting_date_open
from omnexa_accounting.utils.enterprise_codes import ensure_invoice_name


class SalesInvoice(Document):
	def autoname(self):
		ensure_invoice_name(self, prefix="SINV-", date_field="posting_date", digits=5)

	def validate(self):
		# Amend copies may carry cancelled workflow state; reset so Frappe workflow can start from draft.
		if self.is_new() and self.amended_from and self.meta.has_field("workflow_state"):
			self.workflow_state = None

		self._validate_sales_chain_refs()
		self._apply_due_date_from_party()
		self._validate_customer_company()
		validate_branch_company(self)
		self._validate_due_date()
		self._validate_return()
		self._sync_and_validate_line_items()
		apply_invoice_tax_rule_defaults(self)
		self._set_amounts()
		apply_multi_currency_to_invoice(self)
		self._validate_payment_schedule()
		self._validate_tax_rules()
		self._validate_project_links()
		self._validate_item_cost_centers()
		self._set_outstanding_amount()

	def _validate_sales_chain_refs(self):
		"""Optional links to quotation / order / delivery must match party and company."""
		if self.delivery_note and not self.sales_order:
			self.sales_order = frappe.db.get_value("Delivery Note", self.delivery_note, "sales_order")
		if self.sales_quotation:
			sq = frappe.db.get_value(
				"Sales Quotation",
				self.sales_quotation,
				["company", "customer", "docstatus"],
				as_dict=True,
			)
			if not sq:
				frappe.throw(_("Sales Quotation does not exist."), title=_("Sales chain"))
			if sq.company != self.company or sq.customer != self.customer:
				frappe.throw(
					_("Sales Quotation customer/company must match this invoice."),
					title=_("Sales chain"),
				)
			if sq.docstatus != 1:
				frappe.throw(_("Sales Quotation must be submitted."), title=_("Sales chain"))
		if self.sales_order:
			so = frappe.db.get_value(
				"Sales Order",
				self.sales_order,
				["company", "customer", "docstatus"],
				as_dict=True,
			)
			if not so:
				frappe.throw(_("Sales Order does not exist."), title=_("Sales chain"))
			if so.company != self.company or so.customer != self.customer:
				frappe.throw(
					_("Sales Order customer/company must match this invoice."),
					title=_("Sales chain"),
				)
			if so.docstatus != 1:
				frappe.throw(_("Sales Order must be submitted."), title=_("Sales chain"))
		if self.delivery_note:
			dn = frappe.db.get_value(
				"Delivery Note",
				self.delivery_note,
				["company", "customer", "docstatus", "sales_order"],
				as_dict=True,
			)
			if not dn:
				frappe.throw(_("Delivery Note does not exist."), title=_("Sales chain"))
			if dn.company != self.company or dn.customer != self.customer:
				frappe.throw(
					_("Delivery Note customer/company must match this invoice."),
					title=_("Sales chain"),
				)
			if dn.docstatus != 1:
				frappe.throw(_("Delivery Note must be submitted."), title=_("Sales chain"))
			if self.sales_order and dn.sales_order != self.sales_order:
				frappe.throw(
					_("Delivery Note must belong to the same Sales Order linked on this invoice."),
					title=_("Sales chain"),
				)

	def _apply_due_date_from_party(self):
		if self.due_date or self.is_return or not self.customer:
			return
		days = get_effective_credit_days("Customer", self.customer)
		if days <= 0:
			days = get_default_sales_invoice_due_days()
		if days > 0:
			self.due_date = add_days(getdate(self.posting_date), days)

	def _validate_customer_company(self):
		if not self.customer:
			return
		c_company = frappe.db.get_value("Customer", self.customer, "company")
		if c_company != self.company:
			frappe.throw(_("Customer belongs to a different company."), title=_("Company"))

	def _validate_due_date(self):
		if not self.due_date:
			return
		if getdate(self.due_date) < getdate(self.posting_date):
			frappe.throw(_("Due Date cannot be before Posting Date."), title=_("Due Date"))

	def _validate_return(self):
		if not self.is_return:
			self.return_against = None
			return
		if not self.return_against:
			frappe.throw(_("Return Against is required for a credit note."), title=_("Return"))
		orig = frappe.get_doc("Sales Invoice", self.return_against)
		if orig.docstatus != 1:
			frappe.throw(_("Return Against must be a submitted Sales Invoice."), title=_("Return"))
		if orig.company != self.company:
			frappe.throw(_("Original invoice must belong to the same company."), title=_("Return"))
		if orig.customer != self.customer:
			frappe.throw(
				_("Credit note customer must match the original invoice customer."),
				title=_("Return"),
			)
		if orig.get("is_return"):
			frappe.throw(_("Cannot return against another credit note (MVP)."), title=_("Return"))

	def _sync_and_validate_line_items(self):
		for row in self.items or []:
			if not row.item and (not row.item_code or not str(row.item_code).strip()):
				frappe.throw(
					_("Row {0}: Set Item or Item Code.").format(row.idx),
					title=_("Items"),
				)
			if not row.item:
				continue
			it = frappe.get_cached_doc("Item", row.item)
			if it.company != self.company:
				frappe.throw(
					_("Row {0}: Item belongs to a different company.").format(row.idx),
					title=_("Item"),
				)
			if it.disabled:
				frappe.throw(_("Row {0}: Item is disabled.").format(row.idx), title=_("Item"))
			if not it.is_sales_item:
				frappe.throw(
					_("Row {0}: Item cannot be sold (Is Sales Item is off).").format(row.idx),
					title=_("Item"),
				)
			if not row.item_code:
				row.item_code = it.item_code
			elif row.item_code != it.item_code:
				frappe.throw(
					_("Row {0}: Item Code must match the selected Item.").format(row.idx),
					title=_("Item"),
				)

	def on_submit(self):
		assert_posting_date_open(self.company, self.posting_date)
		self._check_credit_limit()
		try:
			from omnexa_accounting.utils.invoice_posting import post_sales_invoice_gl

			post_sales_invoice_gl(self)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Posting: Sales Invoice auto-post")
		try:
			from omnexa_accounting.utils.invoice_stock_sync import post_sales_invoice_stock

			stock_entry = post_sales_invoice_stock(self)
			if stock_entry and self.meta.has_field("posting_stock_entry"):
				self.db_set("posting_stock_entry", stock_entry, update_modified=False)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Stock: Sales Invoice auto stock-update")
		self._enqueue_eta_submission()

	def on_cancel(self):
		try:
			from omnexa_accounting.utils.invoice_posting import cancel_invoice_posting

			cancel_invoice_posting("Sales Invoice", self.name, self.company, getattr(self, "branch", None))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Posting: Sales Invoice cancel auto-post")
		try:
			from omnexa_accounting.utils.invoice_stock_sync import cancel_invoice_stock

			cancel_invoice_stock("Sales Invoice", self.name, self.company, getattr(self, "branch", None))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Stock: Sales Invoice cancel auto stock-update")

	def _set_amounts(self):
		net = 0
		tax = 0
		tax_breakdown = {}
		total_items = 0
		total_qty = 0
		for row in self.items or []:
			line_net = flt(row.qty) * flt(row.rate)
			row.amount = line_net
			net += line_net
			total_items += 1
			total_qty += flt(row.qty)
			rule_name = row.tax_rule or self.default_tax_rule
			if rule_name:
				rule = frappe.get_doc("Tax Rule", rule_name)
				if getdate(self.posting_date) < getdate(rule.valid_from) or getdate(
					self.posting_date
				) > getdate(rule.valid_to):
					frappe.throw(
						_("Row {0}: Tax Rule {1} is not valid on posting date.").format(row.idx, rule_name),
						title=_("Tax"),
					)
				if rule.tax_type == "standard" and flt(rule.rate):
					row_tax = line_net * flt(rule.rate) / 100.0
					tax += row_tax
					row_cat = getattr(row, "tax_category", None)
					key = (row_cat or rule.tax_category or "Uncategorized", flt(rule.rate))
					tax_breakdown[key] = flt(tax_breakdown.get(key, 0)) + row_tax
		items_subtotal = net
		if not self.default_tax_rule and flt(getattr(self, "tax_rate", 0)):
			manual_tax = net * flt(self.tax_rate) / 100.0
			tax += manual_tax
			key = (self.tax_category or "Manual", flt(self.tax_rate))
			tax_breakdown[key] = flt(tax_breakdown.get(key, 0)) + manual_tax
		shipping_cost = flt(getattr(self, "shipping_cost", 0))
		net += shipping_cost
		self.net_total = net
		self.tax_total = tax
		self.grand_total = net + tax
		if self.meta.has_field("items_subtotal"):
			self.items_subtotal = items_subtotal
		if self.meta.has_field("tax_amount_manual"):
			self.tax_amount_manual = tax
		if self.meta.has_field("tax_breakdown_summary"):
			lines = []
			for (cat, rate), amount in sorted(tax_breakdown.items(), key=lambda x: (str(x[0][0]), x[0][1])):
				lines.append(f"{cat} ({rate:g}%): {flt(amount):.2f}")
			self.tax_breakdown_summary = "\n".join(lines) if lines else _("No tax applied")
		if self.meta.has_field("total_items"):
			self.total_items = total_items
		if self.meta.has_field("total_qty"):
			self.total_qty = total_qty

	def _set_outstanding_amount(self):
		if not self.name:
			self.outstanding_amount = flt(self.grand_total)
			return
		allocated = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(per.allocated_amount), 0)
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_doctype = 'Sales Invoice'
				AND per.reference_name = %s
				AND pe.docstatus = 1
				AND per.parenttype = 'Payment Entry'
			""",
			(self.name,),
		)
		allocated_amount = flt(allocated[0][0] if allocated else 0)
		self.outstanding_amount = max(flt(self.grand_total) - allocated_amount, 0)

	def _validate_payment_schedule(self):
		payment_mode = (getattr(self, "payment_mode", "") or "Credit").strip()
		if payment_mode == "Cash":
			if self.payment_schedule:
				frappe.throw(_("Cash invoice cannot contain a payment schedule."), title=_("Payment Mode"))
			self.due_date = self.posting_date
			return
		if payment_mode == "Installment" and len(self.payment_schedule or []) < 2:
			frappe.throw(_("Installment mode requires at least 2 schedule rows."), title=_("Payment Mode"))
		if not self.payment_schedule:
			return
		total_schedule = 0
		max_due_date = None
		for row in self.payment_schedule:
			if getdate(row.due_date) < getdate(self.posting_date):
				frappe.throw(
					_("Payment Schedule row {0}: Due Date cannot be before Posting Date.").format(row.idx),
					title=_("Payment Schedule"),
				)
			if flt(row.payment_amount) <= 0:
				frappe.throw(
					_("Payment Schedule row {0}: Payment Amount must be greater than zero.").format(row.idx),
					title=_("Payment Schedule"),
				)
			total_schedule += flt(row.payment_amount)
			if max_due_date is None or getdate(row.due_date) > getdate(max_due_date):
				max_due_date = row.due_date
		if abs(flt(total_schedule) - flt(self.grand_total)) > 0.0001:
			frappe.throw(
				_("Payment Schedule total must equal Grand Total."),
				title=_("Payment Schedule"),
			)
		self.due_date = max_due_date

	def _validate_tax_rules(self):
		if (self.items or []) and not self.default_tax_rule:
			if not any((row.tax_rule or "").strip() for row in self.items or []):
				if not flt(getattr(self, "tax_rate", 0)):
					frappe.throw(
						_(
							"No Tax Rule found for company {0}. Create one under Accounting → Tax Rule, "
							"or set Default Tax Rule on this invoice."
						).format(self.company),
						title=_("Tax"),
					)
		if self.tax_category and not frappe.db.exists("Tax Category", self.tax_category):
			frappe.throw(_("Tax Category does not exist."), title=_("Tax"))
		if self.default_tax_rule:
			if frappe.db.get_value("Tax Rule", self.default_tax_rule, "company") != self.company:
				frappe.throw(_("Default Tax Rule must belong to the same company."), title=_("Tax"))
			if self.tax_category:
				rule_cat = frappe.db.get_value("Tax Rule", self.default_tax_rule, "tax_category")
				if rule_cat and rule_cat != self.tax_category:
					frappe.throw(_("Default Tax Rule Tax Category must match invoice Tax Category."), title=_("Tax"))
		if flt(getattr(self, "tax_rate", 0)) < 0:
			frappe.throw(_("Tax Rate cannot be negative."), title=_("Tax"))
		for row in self.items or []:
			if row.income_account and frappe.db.get_value("GL Account", row.income_account, "company") != self.company:
				frappe.throw(_("Row {0}: GL Account company mismatch.").format(row.idx), title=_("GL"))

	def _validate_item_cost_centers(self):
		for row in self.items or []:
			if not row.cost_center:
				continue
			cc_co = frappe.db.get_value("Cost Center", row.cost_center, "company")
			if cc_co != self.company:
				frappe.throw(
					_("Row {0}: Cost Center belongs to a different company.").format(row.idx),
					title=_("Cost Center"),
				)

	def _validate_project_links(self):
		if self.project_reference and frappe.db.exists("DocType", "Project Contract"):
			row = frappe.db.get_value("Project Contract", self.project_reference, ["company"], as_dict=True)
			if not row:
				frappe.throw(_("Project Reference does not exist."), title=_("Project"))
			if row.company and row.company != self.company:
				frappe.throw(_("Project Reference belongs to a different company."), title=_("Project"))
		if self.project_task_reference and frappe.db.exists("DocType", "PM WBS Task"):
			row = frappe.db.get_value(
				"PM WBS Task", self.project_task_reference, ["company", "project"], as_dict=True
			)
			if not row:
				frappe.throw(_("Project Task Reference does not exist."), title=_("Project"))
			if row.company and row.company != self.company:
				frappe.throw(_("Project Task Reference belongs to a different company."), title=_("Project"))
			if self.project_reference and row.project and row.project != self.project_reference:
				frappe.throw(
					_("Project Task Reference must belong to selected Project Reference."),
					title=_("Project"),
				)

	def _check_credit_limit(self):
		if self.is_return:
			return
		limit = flt(frappe.db.get_value("Customer", self.customer, "credit_limit"))
		if limit <= 0:
			return
		current_outstanding = self._get_customer_submitted_outstanding_before_current()
		projected_outstanding = flt(current_outstanding) + flt(self.outstanding_amount or self.grand_total)
		if projected_outstanding > limit:
			if cint(getattr(self, "credit_limit_override_approved", 0)):
				if not (getattr(self, "credit_limit_override_reason", "") or "").strip():
					frappe.throw(
						_("Credit limit override reason is required."),
						title=_("Credit"),
					)
				if not self._can_approve_credit_limit_override():
					frappe.throw(
						_("Credit limit override can only be approved by Accounts Manager or System Manager."),
						title=_("Credit"),
					)
				return
			frappe.throw(
				_("Projected outstanding exceeds the customer's credit limit."),
				title=_("Credit"),
			)

	def _can_approve_credit_limit_override(self):
		roles = set(frappe.get_roles(frappe.session.user))
		return bool({"Accounts Manager", "System Manager"} & roles)

	def _get_customer_submitted_outstanding_before_current(self):
		conditions = [
			"company = %(company)s",
			"customer = %(customer)s",
			"docstatus = 1",
			"is_return = 0",
		]
		params = {"company": self.company, "customer": self.customer}
		if self.name:
			conditions.append("name != %(current_name)s")
			params["current_name"] = self.name
		result = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(outstanding_amount), 0)
			FROM `tabSales Invoice`
			WHERE {' AND '.join(conditions)}
			""",
			params,
		)
		return flt(result[0][0] if result else 0)

	def _enqueue_eta_submission(self):
		if self.is_return:
			return
		try:
			from omnexa_einvoice.sales_invoice_eta import sales_invoice_is_egypt_branch

			if not sales_invoice_is_egypt_branch(self):
				return
		except ImportError:
			pass
		if self.meta.has_field("eta_billing_type"):
			billing = (self.eta_billing_type or "Regular").strip()
			if billing != "E-Invoice":
				return
		scope = self._resolve_einvoice_scope()
		if not scope.get("enabled"):
			return
		existing = frappe.db.get_value(
			"E-Document Submission",
			{
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"authority_operation": "submit",
			},
			"name",
		)
		if existing:
			existing_doc = frappe.get_doc("E-Document Submission", existing)
			# Idempotency: do not enqueue duplicates while processing/accepted.
			if existing_doc.authority_status in {
				DOC_STATUS_QUEUED,
				DOC_STATUS_SENT,
				DOC_STATUS_SUBMITTED,
				DOC_STATUS_ACCEPTED,
			}:
				return
			# Retry-safe path: rejected submissions are re-queued in place.
			if existing_doc.authority_status == DOC_STATUS_REJECTED:
				existing_doc.authority_status = DOC_STATUS_QUEUED
				existing_doc.eta_error_code = ""
				existing_doc.http_status_code = None
				existing_doc.response_body = ""
				existing_doc.save(ignore_permissions=True)
				return
		cust_label = frappe.db.get_value("Customer", self.customer, "customer_name") or self.customer
		payload = f"{self.doctype}|{self.name}|{self.posting_date}|{self.grand_total}|{cust_label}".encode()
		h = hashlib.sha256(payload).hexdigest()
		doc = frappe.new_doc("E-Document Submission")
		doc.company = self.company
		doc.branch = self.branch
		doc.reference_doctype = self.doctype
		doc.reference_name = self.name
		if self.branch and frappe.db.has_column("E-Document Submission", "tax_authority_profile"):
			doc.tax_authority_profile = frappe.db.get_value(
				"Branch", self.branch, "tax_authority_profile"
			)
		if self.branch and frappe.db.has_column("E-Document Submission", "signing_profile"):
			doc.signing_profile = frappe.db.get_value("Branch", self.branch, "signing_profile")
		doc.payload_hash = h
		doc.authority_operation = "submit"
		doc.authority_status = DOC_STATUS_QUEUED
		doc.insert(ignore_permissions=True)
		doc.submit()

	def _resolve_einvoice_scope(self):
		"""ETA settings live on Branch only (Egypt ETA tab)."""
		if not self.branch:
			return {"enabled": False}
		if not frappe.db.get_value("Branch", self.branch, "eta_einvoice_enabled"):
			return {"enabled": False}
		try:
			from omnexa_einvoice.branch_eta import branch_eta_is_configured

			if not branch_eta_is_configured(self.branch, kind="invoice"):
				frappe.throw(
					_("Complete Egypt ETA settings on Branch {0} (tab: Egypt ETA).").format(self.branch),
					title=_("ETA"),
				)
		except ImportError:
			pass
		return {"enabled": True, "branch": self.branch}


@frappe.whitelist()
def get_form_defaults() -> dict:
	"""Defaults for new Sales Invoice form (tax category, due days)."""
	out = {"tax_category": None, "due_days": get_default_sales_invoice_due_days()}
	try:
		from omnexa_core.omnexa_core.doctype.omnexa_sales_settings.omnexa_sales_settings import (
			get_sales_settings,
		)

		cat = (get_sales_settings().get("default_sales_tax_category") or "").strip()
		if cat and frappe.db.exists("Tax Category", cat):
			out["tax_category"] = cat
	except Exception:
		pass
	return out
