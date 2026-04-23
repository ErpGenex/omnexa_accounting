from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, today

from omnexa_accounting.utils.coa_seed_templates import ACTIVITY_EXTENSIONS, BASE_COA_TEMPLATE


def _localized_account_label(entry: dict) -> str:
	"""Pick account label for `account_name` by session/user language (ar vs en)."""
	legacy = (entry.get("name") or "").strip()
	en = (entry.get("name_en") or legacy or "").strip()
	ar = (entry.get("name_ar") or "").strip()
	lang = (
		getattr(frappe.local, "lang", None)
		or frappe.db.get_value("User", frappe.session.user, "language")
		or frappe.get_system_settings("language")
		or "en"
	)
	lang = (lang or "en").lower()
	if lang.startswith("ar"):
		return ar or en
	return en or ar

_RESET_DOCTYPES = [
	"Payment Entry",
	"Journal Entry",
	"Sales Invoice",
	"Purchase Invoice",
	"Delivery Note",
	"Purchase Receipt",
	"Sales Order",
	"Purchase Order",
	"Stock Entry",
	"Stock Reconciliation",
	"Landed Cost Voucher",
]


def _assert_admin():
	if "System Manager" not in (frappe.get_roles() or []):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _log_seed_operation(
	operation: str,
	company: str,
	branch: str | None,
	activity: str | None,
	dry_run: int,
	status: str,
	summary: dict,
) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Production Seed Log",
			"operation": operation,
			"company": company,
			"branch": branch,
			"activity": activity,
			"executed_by": frappe.session.user,
			"executed_on": frappe.utils.now_datetime(),
			"dry_run": int(dry_run or 0),
			"status": status,
			"summary_json": frappe.as_json(summary),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_account(entry: dict, company: str, branch: str | None, parent_map: dict[str, str]) -> str:
	parent_name = parent_map.get(entry.get("parent") or "")
	filters = {"company": company, "account_number": entry["code"]}
	if branch:
		filters["branch"] = branch
	name = frappe.db.get_value("GL Account", filters, "name")
	values = {
		"account_number": entry["code"],
		"account_name": _localized_account_label(entry),
		"company": company,
		"branch": branch,
		"is_group": int(entry.get("group") or 0),
		"account_type": entry["type"],
		"main_account_type": entry.get("main"),
		"sub_account_type": entry.get("sub"),
		"parent_account": parent_name,
	}
	for opt in ("pl_bucket", "cash_flow_section", "working_capital_bucket"):
		if entry.get(opt):
			values[opt] = entry[opt]
	if "is_stock_valuation" in entry:
		values["is_stock_valuation"] = int(entry.get("is_stock_valuation") or 0)
	if name:
		doc = frappe.get_doc("GL Account", name)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc.name
	doc = frappe.get_doc({"doctype": "GL Account", **values})
	doc.insert(ignore_permissions=True)
	return doc.name


def _run_professional_coa_sync(company: str, branch: str | None, activity: str | None) -> dict:
	"""Build/update GL accounts from the bilingual template (same logic for generate and resync)."""
	_assert_admin()
	if not company:
		frappe.throw(_("Company is required"))
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} not found").format(company))
	company_doc = frappe.get_doc("Company", company)
	industry = (activity or company_doc.get("industry_sector") or "General").strip()
	template = list(BASE_COA_TEMPLATE)
	extra = ACTIVITY_EXTENSIONS.get(industry) or ACTIVITY_EXTENSIONS.get("General", [])
	template.extend(list(extra))

	parent_map: dict[str, str] = {}
	created_or_updated = []
	for entry in template:
		name = _ensure_account(entry, company, branch, parent_map)
		parent_map[entry["code"]] = name
		created_or_updated.append(name)

	return {
		"ok": True,
		"company": company,
		"branch": branch,
		"industry": industry,
		"accounts_created_or_updated": len(created_or_updated),
		"account_ids": created_or_updated,
	}


@frappe.whitelist(methods=["POST"])
def generate_professional_chart_of_accounts(company: str, branch: str | None = None, activity: str | None = None):
	"""Generate professional CoA template per company/branch/activity."""
	result = _run_professional_coa_sync(company, branch, activity)
	try:
		from omnexa_accounting.utils.company_financial_defaults import apply_company_default_gl_from_coa

		result["company_default_gl_fill"] = apply_company_default_gl_from_coa(company, branch=branch, overwrite=0)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa: apply_company_default_gl_from_coa after COA")
		result["company_default_gl_fill"] = {"ok": False}
	log_id = _log_seed_operation(
		"Generate COA",
		company,
		branch,
		result.get("industry"),
		0,
		"Success",
		result,
	)
	result["log_id"] = log_id
	return result


@frappe.whitelist(methods=["POST"])
def resync_chart_of_accounts_labels(company: str, branch: str | None = None, activity: str | None = None):
	"""Re-apply template to existing accounts: updates localized `account_name` and template fields (P&L bucket, etc.).

	Use after changing bilingual templates or user language, so old labels are replaced for all accounts
	that match seeded `account_number` values for this company/branch.
	"""
	result = _run_professional_coa_sync(company, branch, activity)
	try:
		from omnexa_accounting.utils.company_financial_defaults import apply_company_default_gl_from_coa

		result["company_default_gl_fill"] = apply_company_default_gl_from_coa(company, branch=branch, overwrite=0)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Omnexa: apply_company_default_gl_from_coa after COA resync")
		result["company_default_gl_fill"] = {"ok": False}
	log_id = _log_seed_operation(
		"Resync COA Labels",
		company,
		branch,
		result.get("industry"),
		0,
		"Success",
		result,
	)
	result["log_id"] = log_id
	return result


@frappe.whitelist(methods=["POST"])
def seed_activity_demo_data(
	company: str,
	branch: str | None = None,
	activity: str | None = None,
	include_transactions: int | str | None = 0,
):
	"""Seed minimal demo data per activity to support pilots/training."""
	_assert_admin()
	if not company:
		frappe.throw(_("Company is required"))
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} not found").format(company))

	created = {"customer": None, "supplier": None, "warehouse": None, "item": None}
	if not frappe.db.exists("UOM", "Nos"):
		uom = frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"})
		uom.insert(ignore_permissions=True)

	cust_name = f"DEMO-CUST-{company}"
	existing_cust = frappe.db.get_value("Customer", {"customer_name": cust_name, "company": company}, "name")
	if existing_cust:
		created["customer"] = existing_cust
	else:
		cust = frappe.get_doc({"doctype": "Customer", "customer_name": cust_name, "company": company})
		cust.insert(ignore_permissions=True)
		created["customer"] = cust.name

	supp_name = f"DEMO-SUPP-{company}"
	existing_supp = frappe.db.get_value("Supplier", {"supplier_name": supp_name, "company": company}, "name")
	if existing_supp:
		created["supplier"] = existing_supp
	else:
		supp = frappe.get_doc({"doctype": "Supplier", "supplier_name": supp_name, "company": company})
		supp.insert(ignore_permissions=True)
		created["supplier"] = supp.name

	wh_name = f"DEMO-WH-{company}"
	wh_code = ("DM" + "".join(ch for ch in company if ch.isalnum()).upper())[:12]
	existing_wh = frappe.db.get_value("Warehouse", {"warehouse_name": wh_name, "company": company}, "name")
	if existing_wh:
		created["warehouse"] = existing_wh
	else:
		wh = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": wh_name,
				"warehouse_code": wh_code,
				"company": company,
			}
		)
		wh.insert(ignore_permissions=True)
		created["warehouse"] = wh.name

	item_code = f"DEMO-ITEM-{company}"
	existing_item = frappe.db.get_value("Item", {"item_code": item_code, "company": company}, "name")
	if existing_item:
		created["item"] = existing_item
	else:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": f"Demo Item {activity or 'General'}",
				"company": company,
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		)
		item.insert(ignore_permissions=True)
		created["item"] = item.name

	with_tx = cint(include_transactions or 0) == 1
	tx_summary: dict | None = None
	if with_tx:
		tx_summary = _seed_demo_transactions(
			company=company,
			branch=branch,
			customer=created["customer"],
			supplier=created["supplier"],
			warehouse=created["warehouse"],
			item=created["item"],
		)

	result = {
		"ok": True,
		"company": company,
		"branch": branch,
		"activity": activity or "General",
		"created": created,
		"include_transactions": with_tx,
	}
	if tx_summary is not None:
		result["transactions"] = tx_summary
	log_id = _log_seed_operation("Seed Demo Data", company, branch, activity or "General", 0, "Success", result)
	result["log_id"] = log_id
	return result


def _company_currency(company: str) -> str:
	return frappe.db.get_value("Company", company, "default_currency") or frappe.db.get_single_value(
		"Global Defaults", "default_currency"
	)


def _leaf_gl_by_number(company: str, branch: str | None, account_number: str) -> str | None:
	filters = {"company": company, "account_number": account_number, "is_group": 0}
	if branch:
		filters["branch"] = branch
	return frappe.db.get_value("GL Account", filters, "name")


def _seed_demo_transactions(
	company: str,
	branch: str | None,
	customer: str | None,
	supplier: str | None,
	warehouse: str | None,
	item: str | None,
) -> dict:
	"""Create a small submitted document chain for training dashboards (best-effort)."""
	if not (customer and supplier and warehouse and item):
		return {"ok": False, "skipped": True, "reason": "missing_masters"}

	item_code = frappe.db.get_value("Item", item, "item_code")
	currency = _company_currency(company)
	if not currency:
		return {"ok": False, "skipped": True, "reason": "missing_currency"}

	tx_tag = f"DEMO-TX-{company}"
	so_name = frappe.db.sql(
		"""
		SELECT so.name
		FROM `tabSales Order` so
		INNER JOIN `tabSales Order Item` li ON li.parent = so.name
		WHERE so.company = %s AND so.customer = %s AND so.docstatus = 1
		  AND li.item = %s AND li.qty = %s AND li.rate = %s
		ORDER BY so.creation DESC
		LIMIT 1
		""",
		(company, customer, item, 5, 40),
	)
	so_name = so_name[0][0] if so_name else None

	po_name = frappe.db.sql(
		"""
		SELECT po.name
		FROM `tabPurchase Order` po
		INNER JOIN `tabPurchase Order Item` li ON li.parent = po.name
		WHERE po.company = %s AND po.supplier = %s AND po.docstatus = 1
		  AND li.item = %s AND li.qty = %s AND li.rate = %s
		ORDER BY po.creation DESC
		LIMIT 1
		""",
		(company, supplier, item, 10, 25),
	)
	po_name = po_name[0][0] if po_name else None

	created: dict[str, str | None] = {}

	def _submit(doc):
		if doc.docstatus == 0:
			doc.submit()

	# --- Purchase chain ---
	if not po_name:
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"company": company,
				"supplier": supplier,
				"posting_date": today(),
				"items": [{"item": item, "item_code": item_code, "qty": 10, "rate": 25}],
			}
		)
		po.insert(ignore_permissions=True)
		_submit(po)
		po_name = po.name
		created["purchase_order"] = po_name

	pr_name = None
	if po_name:
		pr_name = frappe.db.get_value(
			"Purchase Receipt",
			{"company": company, "supplier": supplier, "purchase_order": po_name, "docstatus": 1},
			"name",
		)
	if not pr_name and po_name:
		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"company": company,
				"supplier": supplier,
				"posting_date": today(),
				"purchase_order": po_name,
				"items": [{"item_code": item_code, "qty": 10, "rate": 25}],
			}
		)
		pr.insert(ignore_permissions=True)
		_submit(pr)
		pr_name = pr.name
		created["purchase_receipt"] = pr_name

	pi_name = frappe.db.sql(
		"""
		SELECT pi.name
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` li ON li.parent = pi.name
		WHERE pi.company = %s AND pi.supplier = %s AND pi.docstatus = 1
		  AND IFNULL(pi.is_return, 0) = 0
		  AND pi.po_reference = %s AND pi.goods_receipt_reference = %s
		  AND li.item = %s AND li.qty = %s AND li.rate = %s
		ORDER BY pi.creation DESC
		LIMIT 1
		""",
		(company, supplier, po_name, pr_name, item, 10, 25),
	)
	pi_name = pi_name[0][0] if pi_name else None

	if not pi_name and po_name and pr_name:
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": company,
				"branch": branch,
				"supplier": supplier,
				"posting_date": today(),
				"currency": currency,
				"conversion_rate": 1,
				"po_reference": po_name,
				"goods_receipt_reference": pr_name,
				"items": [{"item": item, "item_code": item_code, "qty": 10, "rate": 25}],
			}
		)
		pi.insert(ignore_permissions=True)
		try:
			_submit(pi)
			pi_name = pi.name
			created["purchase_invoice"] = pi_name
		except Exception as e:
			created["purchase_invoice_error"] = str(e)

	# --- Sales chain ---
	if not so_name:
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"company": company,
				"branch": branch,
				"customer": customer,
				"transaction_date": today(),
				"currency": currency,
				"conversion_rate": 1,
				"items": [{"item": item, "item_code": item_code, "qty": 5, "rate": 40}],
			}
		)
		so.insert(ignore_permissions=True)
		_submit(so)
		so_name = so.name
		created["sales_order"] = so_name

	dn_name = None
	if so_name:
		dn_name = frappe.db.get_value(
			"Delivery Note",
			{"company": company, "customer": customer, "sales_order": so_name, "docstatus": 1},
			"name",
		)
	if not dn_name and so_name:
		dn = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": company,
				"branch": branch,
				"customer": customer,
				"sales_order": so_name,
				"warehouse": warehouse,
				"transaction_date": today(),
				"items": [{"item": item, "item_code": item_code, "qty": 5, "rate": 40}],
			}
		)
		dn.insert(ignore_permissions=True)
		_submit(dn)
		dn_name = dn.name
		created["delivery_note"] = dn_name

	si_name = frappe.db.sql(
		"""
		SELECT si.name
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` li ON li.parent = si.name
		WHERE si.company = %s AND si.customer = %s AND si.docstatus = 1
		  AND IFNULL(si.is_return, 0) = 0
		  AND si.sales_order = %s AND si.delivery_note = %s
		  AND li.item = %s AND li.qty = %s AND li.rate = %s
		ORDER BY si.creation DESC
		LIMIT 1
		""",
		(company, customer, so_name, dn_name, item, 5, 40),
	)
	si_name = si_name[0][0] if si_name else None

	if not si_name and so_name and dn_name:
		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": company,
				"branch": branch,
				"customer": customer,
				"posting_date": today(),
				"currency": currency,
				"conversion_rate": 1,
				"sales_order": so_name,
				"delivery_note": dn_name,
				"items": [{"item": item, "item_code": item_code, "qty": 5, "rate": 40}],
			}
		)
		si.insert(ignore_permissions=True)
		try:
			_submit(si)
			si_name = si.name
			created["sales_invoice"] = si_name
		except Exception as e:
			created["sales_invoice_error"] = str(e)

	# --- Simple balanced journal entry (optional GL leaf accounts) ---
	je_name = frappe.db.get_value("Journal Entry", {"company": company, "reference": tx_tag}, "name")
	if not je_name:
		cash = _leaf_gl_by_number(company, branch, "1101")
		bank = _leaf_gl_by_number(company, branch, "1102")
		if cash and bank:
			je = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"company": company,
					"branch": branch,
					"posting_date": today(),
					"reference": tx_tag,
					"remarks": "Omnexa demo journal (cash to bank)",
					"accounts": [
						{"account": bank, "debit": 100, "credit": 0},
						{"account": cash, "debit": 0, "credit": 100},
					],
				}
			)
			je.insert(ignore_permissions=True)
			try:
				_submit(je)
				je_name = je.name
				created["journal_entry"] = je_name
			except Exception as e:
				created["journal_entry_error"] = str(e)

	return {"ok": True, "tag": tx_tag, "created": created}


def _doc_filters(doctype: str, company: str, branch: str | None):
	meta = frappe.get_meta(doctype)
	fields = {d.fieldname for d in meta.fields}
	filters = {}
	if "company" in fields:
		filters["company"] = company
	if branch and "branch" in fields:
		filters["branch"] = branch
	return filters


@frappe.whitelist(methods=["POST"])
def reset_transactions(company: str, branch: str | None = None, dry_run: int | str = 1):
	"""Reset accounting transactions for company/branch by System Manager only."""
	_assert_admin()
	if not company:
		frappe.throw(_("Company is required"))
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} not found").format(company))

	is_dry = int(dry_run or 1) == 1
	report = []

	for dt in _RESET_DOCTYPES:
		filters = _doc_filters(dt, company, branch)
		if not filters:
			continue
		names = frappe.get_all(dt, filters=filters, pluck="name", limit=5000)
		if is_dry:
			report.append({"doctype": dt, "matched": len(names), "cancelled": 0, "deleted": 0})
			continue

		cancelled = 0
		deleted = 0
		for name in reversed(names):
			doc = frappe.get_doc(dt, name)
			if hasattr(doc, "docstatus") and int(doc.docstatus or 0) == 1:
				try:
					doc.cancel()
					cancelled += 1
				except Exception:
					continue
			try:
				frappe.delete_doc(dt, name, ignore_permissions=True, force=1)
				deleted += 1
			except Exception:
				pass
		report.append({"doctype": dt, "matched": len(names), "cancelled": cancelled, "deleted": deleted})

	result = {"ok": True, "company": company, "branch": branch, "dry_run": is_dry, "details": report}
	log_id = _log_seed_operation(
		"Reset Transactions",
		company,
		branch,
		None,
		1 if is_dry else 0,
		"Success",
		result,
	)
	result["log_id"] = log_id
	return result

