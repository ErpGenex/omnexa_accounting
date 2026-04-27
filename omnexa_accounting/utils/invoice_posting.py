from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def _company_default(company: str, fieldname: str) -> str | None:
	if not company:
		return None
	if not frappe.db.exists("Company", company):
		return None
	if not frappe.get_meta("Company").has_field(fieldname):
		return None
	return frappe.db.get_value("Company", company, fieldname)


def _get_sales_income_account(company: str) -> str | None:
	return _company_default(company, "default_sales_revenue_gl") or _company_default(company, "default_service_revenue_gl")


def _get_purchase_expense_account(company: str) -> str | None:
	# Use COGS by default for simplicity (MVP). Tenants can override per item row.
	return _company_default(company, "default_cogs_gl") or _company_default(company, "default_opex_gl")


def _reference_for_invoice(doctype: str, name: str) -> str:
	return f"{doctype}:{name}"


def _find_existing_posting_je(company: str, branch: str | None, reference: str) -> str | None:
	filters = {"company": company, "reference": reference}
	if branch and frappe.get_meta("Journal Entry").has_field("branch"):
		filters["branch"] = branch
	return frappe.db.get_value("Journal Entry", filters, "name")


def _make_je(*, company: str, branch: str | None, posting_date, reference: str, remarks: str, lines: list[dict]) -> str:
	if not company:
		frappe.throw(_("Company is required"), title=_("Posting"))
	je = frappe.new_doc("Journal Entry")
	je.company = company
	if branch and je.meta.has_field("branch"):
		je.branch = branch
	je.posting_date = posting_date
	je.reference = reference
	je.remarks = remarks
	for line in lines:
		je.append("accounts", line)
	je.insert(ignore_permissions=True)
	je.submit()
	return je.name


def post_sales_invoice_gl(sales_invoice) -> str | None:
	"""Create a Journal Entry for Sales Invoice (AR / Revenue / Output VAT)."""
	if not sales_invoice or sales_invoice.docstatus != 1:
		return None
	company = sales_invoice.company
	branch = getattr(sales_invoice, "branch", None)
	ref = _reference_for_invoice("Sales Invoice", sales_invoice.name)
	existing = _find_existing_posting_je(company, branch, ref)
	if existing:
		return existing

	ar = _company_default(company, "default_receivable_gl")
	income = _get_sales_income_account(company)
	vat = _company_default(company, "default_output_vat_gl")
	if not (ar and income):
		frappe.log_error(
			f"Missing default GLs for Sales Invoice posting. company={company} ar={ar} income={income} vat={vat}",
			"Omnexa Posting: Sales Invoice defaults missing",
		)
		return None

	net = flt(getattr(sales_invoice, "net_total", 0)) or flt(getattr(sales_invoice, "grand_total", 0))
	tax = flt(getattr(sales_invoice, "tax_total", 0))
	grand = flt(getattr(sales_invoice, "grand_total", 0)) or flt(net + tax)

	lines: list[dict] = [
		{"account": ar, "debit": grand, "credit": 0},
		{"account": income, "debit": 0, "credit": net},
	]
	if tax and vat:
		lines.append({"account": vat, "debit": 0, "credit": tax})

	je_name = _make_je(
		company=company,
		branch=branch,
		posting_date=sales_invoice.posting_date,
		reference=ref,
		remarks=f"Auto-post Sales Invoice {sales_invoice.name}",
		lines=lines,
	)
	if je_name and getattr(sales_invoice, "meta", None) and sales_invoice.meta.has_field("posting_journal_entry"):
		sales_invoice.db_set("posting_journal_entry", je_name, update_modified=False)
	return je_name


def post_purchase_invoice_gl(purchase_invoice) -> str | None:
	"""Create a Journal Entry for Purchase Invoice (Expense/Inventory / Input VAT / AP)."""
	if not purchase_invoice or purchase_invoice.docstatus != 1:
		return None
	company = purchase_invoice.company
	branch = getattr(purchase_invoice, "branch", None)
	ref = _reference_for_invoice("Purchase Invoice", purchase_invoice.name)
	existing = _find_existing_posting_je(company, branch, ref)
	if existing:
		return existing

	ap = _company_default(company, "default_trade_payable_gl")
	expense = _get_purchase_expense_account(company)
	vat = _company_default(company, "default_input_vat_gl")
	if not (ap and expense):
		frappe.log_error(
			f"Missing default GLs for Purchase Invoice posting. company={company} ap={ap} expense={expense} vat={vat}",
			"Omnexa Posting: Purchase Invoice defaults missing",
		)
		return None

	net = flt(getattr(purchase_invoice, "net_total", 0)) or flt(getattr(purchase_invoice, "grand_total", 0))
	tax = flt(getattr(purchase_invoice, "tax_total", 0))
	grand = flt(getattr(purchase_invoice, "grand_total", 0)) or flt(net + tax)

	lines: list[dict] = [
		{"account": expense, "debit": net, "credit": 0},
	]
	if tax and vat:
		lines.append({"account": vat, "debit": tax, "credit": 0})
	lines.append({"account": ap, "debit": 0, "credit": grand})

	je_name = _make_je(
		company=company,
		branch=branch,
		posting_date=purchase_invoice.posting_date,
		reference=ref,
		remarks=f"Auto-post Purchase Invoice {purchase_invoice.name}",
		lines=lines,
	)
	if je_name and getattr(purchase_invoice, "meta", None) and purchase_invoice.meta.has_field(
		"posting_journal_entry"
	):
		purchase_invoice.db_set("posting_journal_entry", je_name, update_modified=False)
	return je_name


def cancel_invoice_posting(doctype: str, docname: str, company: str, branch: str | None = None) -> str | None:
	"""Cancel the auto JE created for an invoice if present."""
	ref = _reference_for_invoice(doctype, docname)
	je_name = _find_existing_posting_je(company, branch, ref)
	if not je_name:
		return None
	je = frappe.get_doc("Journal Entry", je_name)
	if int(je.docstatus or 0) == 1:
		je.cancel()
	return je_name

