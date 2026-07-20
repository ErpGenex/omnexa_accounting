from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def _company_default(company: str, fieldname: str) -> str | None:
	if not company or not frappe.db.exists("Company", company):
		return None
	if not frappe.get_meta("Company").has_field(fieldname):
		return None
	return frappe.db.get_value("Company", company, fieldname)


def _warehouse_account(warehouse: str | None, fieldname: str) -> str | None:
	if not warehouse or not frappe.db.exists("Warehouse", warehouse):
		return None
	if not frappe.get_meta("Warehouse").has_field(fieldname):
		return None
	return frappe.db.get_value("Warehouse", warehouse, fieldname)


def _item_inventory_account(item: str | None) -> str | None:
	if not item or not frappe.db.exists("Item", item):
		return None
	if not frappe.get_meta("Item").has_field("inventory_control_account"):
		return None
	return frappe.db.get_value("Item", item, "inventory_control_account")


def _resolve_inventory_account(company: str, warehouse: str | None, item: str | None) -> str | None:
	return (
		_warehouse_account(warehouse, "inventory_gl_account")
		or _item_inventory_account(item)
		or _company_default(company, "default_inventory_gl")
	)


def _resolve_adjustment_account(company: str, warehouse: str | None) -> str | None:
	return _warehouse_account(warehouse, "stock_adjustment_gl_account") or _company_default(company, "default_opex_gl")


def _resolve_cogs_account(company: str) -> str | None:
	return _company_default(company, "default_cogs_gl") or _company_default(company, "default_opex_gl")


def validate_stock_entry_accounting_ready(doc):
	"""IFRS-aligned minimum controls before posting stock movements."""
	if not doc or not doc.company:
		return
	cogs = _resolve_cogs_account(doc.company)
	if not cogs:
		frappe.throw(_("Default COGS/OPEX GL is required on Company for stock accounting."), title=_("Inventory GL"))

	for row in doc.get("items") or []:
		source_wh = row.s_warehouse or doc.from_warehouse
		target_wh = row.t_warehouse or doc.to_warehouse
		if doc.purpose in ("Material Issue", "Material Transfer"):
			inv_src = _resolve_inventory_account(doc.company, source_wh, row.item)
			if not inv_src:
				frappe.throw(
					_("Row {0}: missing inventory GL mapping for source warehouse/item.").format(row.idx),
					title=_("Inventory GL"),
				)
		if doc.purpose in ("Material Receipt", "Material Transfer"):
			inv_tgt = _resolve_inventory_account(doc.company, target_wh, row.item)
			if not inv_tgt:
				frappe.throw(
					_("Row {0}: missing inventory GL mapping for target warehouse/item.").format(row.idx),
					title=_("Inventory GL"),
				)
		if doc.purpose == "Material Receipt":
			adj = _resolve_adjustment_account(doc.company, target_wh)
			if not adj:
				frappe.throw(
					_("Row {0}: missing stock adjustment GL mapping for receipt warehouse/company.").format(row.idx),
					title=_("Inventory GL"),
				)


def _posting_reference(doc) -> str:
	return f"Stock Entry:{doc.name}"


def _find_posting_je(doc) -> str | None:
	filters = {"company": doc.company, "reference": _posting_reference(doc)}
	if doc.meta.has_field("branch") and doc.branch and frappe.get_meta("Journal Entry").has_field("branch"):
		filters["branch"] = doc.branch
	return frappe.db.get_value("Journal Entry", filters, "name")


def _append_line(
	lines: list[dict],
	account: str,
	debit: float = 0,
	credit: float = 0,
	cost_center: str | None = None,
):
	if not account:
		return
	debit = flt(debit)
	credit = flt(credit)
	if debit == 0 and credit == 0:
		return
	row = {"account": account, "debit": debit, "credit": credit}
	if cost_center:
		row["cost_center"] = cost_center
	lines.append(row)


def post_stock_entry_gl(doc) -> str | None:
	"""Create accounting JE for stock receipt/issue (transfer is stock-to-stock, no P&L)."""
	if not doc or int(doc.docstatus or 0) != 1:
		return None
	if doc.purpose not in ("Material Receipt", "Material Issue"):
		return None
	existing = _find_posting_je(doc)
	if existing:
		return existing

	header_cc = doc.cost_center if doc.meta.has_field("cost_center") else None

	lines: list[dict] = []
	cogs = _resolve_cogs_account(doc.company)

	for row in doc.get("items") or []:
		amount = flt(row.amount) if flt(row.amount) else flt(row.qty) * flt(row.rate)
		if amount <= 0:
			continue
		source_wh = row.s_warehouse or doc.from_warehouse
		target_wh = row.t_warehouse or doc.to_warehouse
		if doc.purpose == "Material Receipt":
			inv = _resolve_inventory_account(doc.company, target_wh, row.item)
			adj = _resolve_adjustment_account(doc.company, target_wh)
			_append_line(lines, inv, debit=amount, credit=0, cost_center=header_cc)
			_append_line(lines, adj, debit=0, credit=amount, cost_center=header_cc)
		elif doc.purpose == "Material Issue":
			inv = _resolve_inventory_account(doc.company, source_wh, row.item)
			_append_line(lines, cogs, debit=amount, credit=0, cost_center=header_cc)
			_append_line(lines, inv, debit=0, credit=amount, cost_center=header_cc)

	if not lines:
		return None

	je = frappe.new_doc("Journal Entry")
	je.company = doc.company
	if doc.meta.has_field("branch") and doc.branch and je.meta.has_field("branch"):
		je.branch = doc.branch
	je.posting_date = doc.posting_date
	je.reference = _posting_reference(doc)
	je.remarks = f"Auto-post Stock Entry {doc.name}"
	for l in lines:
		je.append("accounts", l)
	je.insert(ignore_permissions=True)
	je.submit()
	return je.name


def cancel_stock_entry_posting(doc):
	je_name = _find_posting_je(doc)
	if not je_name:
		return None
	je = frappe.get_doc("Journal Entry", je_name)
	if int(je.docstatus or 0) == 1:
		je.cancel()
	return je_name

