# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate

from omnexa_accounting.utils.branch import validate_branch_company
from omnexa_accounting.utils.tax_rule_resolver import apply_invoice_tax_rule_defaults
from omnexa_accounting.utils.currency import apply_multi_currency_to_invoice
from omnexa_accounting.utils.party import get_effective_credit_days
from omnexa_accounting.utils.posting import assert_posting_date_open
from omnexa_accounting.utils.enterprise_codes import ensure_invoice_name


class PurchaseInvoice(Document):
	def autoname(self):
		ensure_invoice_name(self, prefix="PINV-", date_field="posting_date", digits=5)

	def validate(self):
		# Amend copies may carry cancelled workflow state; reset so Frappe workflow can start from draft.
		if self.is_new() and self.amended_from and self.meta.has_field("workflow_state"):
			self.workflow_state = None

		self._apply_due_date_from_party()
		self._validate_supplier_company()
		validate_branch_company(self)
		self._validate_due_date()
		self._validate_return()
		self._sync_and_validate_line_items()
		apply_invoice_tax_rule_defaults(self)
		self._set_amounts()
		apply_multi_currency_to_invoice(self)
		self._validate_payment_schedule()
		self._validate_accounts_and_dimensions()
		self._validate_project_links()
		self._set_outstanding_amount()

	def _apply_due_date_from_party(self):
		if self.due_date or self.is_return or not self.supplier:
			return
		days = get_effective_credit_days("Supplier", self.supplier)
		if days > 0:
			self.due_date = add_days(getdate(self.posting_date), days)

	def _validate_supplier_company(self):
		if not self.supplier:
			return
		s_company = frappe.db.get_value("Supplier", self.supplier, "company")
		if s_company != self.company:
			frappe.throw(_("Supplier belongs to a different company."), title=_("Company"))

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
			frappe.throw(_("Return Against is required for a debit note."), title=_("Return"))
		orig = frappe.get_doc("Purchase Invoice", self.return_against)
		if orig.docstatus != 1:
			frappe.throw(_("Return Against must be a submitted Purchase Invoice."), title=_("Return"))
		if orig.company != self.company:
			frappe.throw(_("Original invoice must belong to the same company."), title=_("Return"))
		if orig.supplier != self.supplier:
			frappe.throw(
				_("Debit note supplier must match the original invoice supplier."),
				title=_("Return"),
			)
		if orig.get("is_return"):
			frappe.throw(_("Cannot return against another debit note (MVP)."), title=_("Return"))

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
			if not it.is_purchase_item:
				frappe.throw(
					_("Row {0}: Item cannot be purchased (Is Purchase Item is off).").format(row.idx),
					title=_("Item"),
				)
			if not row.item_code:
				row.item_code = it.item_code
			elif row.item_code != it.item_code:
				frappe.throw(
					_("Row {0}: Item Code must match the selected Item.").format(row.idx),
					title=_("Item"),
				)

	def before_submit(self):
		self._validate_approval_rule_on_submit()
		assert_posting_date_open(self.company, self.posting_date)

	def on_submit(self):
		try:
			from omnexa_accounting.utils.invoice_posting import post_purchase_invoice_gl

			post_purchase_invoice_gl(self)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Posting: Purchase Invoice auto-post")
		try:
			from omnexa_accounting.utils.invoice_stock_sync import post_purchase_invoice_stock

			stock_entry = post_purchase_invoice_stock(self)
			if stock_entry and self.meta.has_field("posting_stock_entry"):
				self.db_set("posting_stock_entry", stock_entry, update_modified=False)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Stock: Purchase Invoice auto stock-update")

	def on_cancel(self):
		try:
			from omnexa_accounting.utils.invoice_posting import cancel_invoice_posting

			cancel_invoice_posting("Purchase Invoice", self.name, self.company, getattr(self, "branch", None))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Posting: Purchase Invoice cancel auto-post")
		try:
			from omnexa_accounting.utils.invoice_stock_sync import cancel_invoice_stock

			cancel_invoice_stock("Purchase Invoice", self.name, self.company, getattr(self, "branch", None))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Omnexa Stock: Purchase Invoice cancel auto stock-update")

	def _validate_accounts_and_dimensions(self):
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
			if row.expense_account and frappe.db.get_value("GL Account", row.expense_account, "company") != self.company:
				frappe.throw(_("Row {0}: GL Account company mismatch.").format(row.idx), title=_("GL"))
			if row.cost_center:
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
			WHERE per.reference_doctype = 'Purchase Invoice'
				AND per.reference_name = %s
				AND pe.docstatus = 1
				AND per.parenttype = 'Payment Entry'
			""",
			(self.name,),
		)
		allocated_amount = flt(allocated[0][0] if allocated else 0)
		self.outstanding_amount = max(flt(self.grand_total) - allocated_amount, 0)

	def _validate_approval_rule_on_submit(self):
		rule = self._get_matching_approval_rule()
		if not rule:
			return
		if rule.require_three_way_match and (not self.po_reference or not self.goods_receipt_reference):
			frappe.throw(
				_("PO Reference and Goods Receipt Reference are required by the approval rule."),
				title=_("Approval"),
			)
		if rule.require_three_way_match:
			self._validate_three_way_match_against_documents()
		user_roles = set(frappe.get_roles(frappe.session.user))
		if rule.approver_role not in user_roles:
			frappe.throw(
				_("Submit requires role {0} based on purchase approval matrix.").format(rule.approver_role),
				title=_("Approval"),
			)

	def _get_matching_approval_rule(self):
		rules = frappe.get_all(
			"Purchase Approval Rule",
			filters={"company": self.company, "is_active": 1},
			fields=["name", "approver_role", "min_amount", "max_amount", "require_three_way_match"],
			order_by="min_amount asc",
		)
		for r in rules:
			if flt(r.min_amount) <= flt(self.grand_total) <= flt(r.max_amount):
				return frappe._dict(r)
		return None

	def _validate_three_way_match_against_documents(self):
		po = frappe.get_doc("Purchase Order", self.po_reference)
		if po.docstatus != 1:
			frappe.throw(_("Referenced Purchase Order must be submitted."), title=_("Three-Way Match"))
		grn = frappe.get_doc("Purchase Receipt", self.goods_receipt_reference)
		if grn.docstatus != 1:
			frappe.throw(_("Referenced Goods Receipt must be submitted."), title=_("Three-Way Match"))
		if po.company != self.company or po.supplier != self.supplier:
			frappe.throw(_("Purchase Order company/supplier mismatch with invoice."), title=_("Three-Way Match"))
		if grn.company != self.company or grn.supplier != self.supplier:
			frappe.throw(_("Goods Receipt company/supplier mismatch with invoice."), title=_("Three-Way Match"))
		if grn.purchase_order and grn.purchase_order != po.name:
			frappe.throw(_("Goods Receipt does not reference the selected Purchase Order."), title=_("Three-Way Match"))

		po_items = {row.item_code: row for row in po.items}
		grn_qty = {}
		for row in grn.items:
			grn_qty[row.item_code] = flt(grn_qty.get(row.item_code, 0)) + flt(row.qty)

		for row in self.items or []:
			po_row = po_items.get(row.item_code)
			if not po_row:
				frappe.throw(
					_("Invoice item {0} is not present in Purchase Order.").format(row.item_code),
					title=_("Three-Way Match"),
				)
			if flt(row.qty) > flt(grn_qty.get(row.item_code, 0)):
				frappe.throw(
					_("Invoice Qty exceeds received Qty for item {0}.").format(row.item_code),
					title=_("Three-Way Match"),
				)
			if flt(row.qty) > flt(po_row.qty):
				frappe.throw(
					_("Invoice Qty exceeds ordered Qty for item {0}.").format(row.item_code),
					title=_("Three-Way Match"),
				)
			if flt(row.rate) > flt(po_row.rate):
				frappe.throw(
					_("Invoice Rate exceeds PO Rate for item {0}.").format(row.item_code),
					title=_("Three-Way Match"),
				)

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
