from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, getdate, nowdate, today

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
	allowed_operations = {
		"Generate COA",
		"Resync COA Labels",
		"Seed Demo Data",
		"Reset Transactions",
	}
	operation_value = operation if operation in allowed_operations else "Seed Demo Data"
	doc = frappe.get_doc(
		{
			"doctype": "Production Seed Log",
			"operation": operation_value,
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
	if parent_name and not frappe.db.get_value("GL Account", parent_name, "is_group"):
		# Defensive fix for fresh installs with partial/legacy rows:
		# parent nodes must always be headers before any child is linked.
		parent_doc = frappe.get_doc("GL Account", parent_name)
		parent_doc.is_group = 1
		if parent_doc.meta.has_field("posting_type"):
			parent_doc.posting_type = "Header"
		parent_doc.save(ignore_permissions=True)
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
	# Keep parent rows before children even if extension order changes.
	template.sort(key=lambda row: (len(str(row.get("code") or "")), str(row.get("code") or "")))

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
def reset_transactions(
	company: str,
	branch: str | None = None,
	dry_run: int | str = 1,
	limit: int | str = 5000,
):
	"""Reset accounting transactions for company/branch by System Manager only."""
	_assert_admin()
	if not company:
		frappe.throw(_("Company is required"))
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} not found").format(company))

	# IMPORTANT: do not treat 0 as "missing" (Python `0 or 1` => 1).
	is_dry = cint(dry_run) == 1
	limit = cint(limit or 5000)
	report = []

	for dt in _RESET_DOCTYPES:
		filters = _doc_filters(dt, company, branch)
		if not filters:
			continue
		names = frappe.get_all(dt, filters=filters, pluck="name", limit=limit)
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


@frappe.whitelist(methods=["POST"])
def enqueue_reset_transactions(
	company: str,
	branch: str | None = None,
	limit: int | str = 0,
	batch_size: int | str = 200,
):
	"""Background reset with batching + commits (recommended for large datasets)."""
	_assert_admin()
	job = frappe.enqueue(
		"omnexa_accounting.utils.production_readiness.run_reset_transactions_batched",
		queue="long",
		timeout=7200,
		company=company,
		branch=branch,
		limit=cint(limit or 0),
		batch_size=cint(batch_size or 200),
		user=frappe.session.user,
	)
	return {"ok": True, "queued": True, "job_id": job.id if job else None}


def run_reset_transactions_batched(company: str, branch: str | None = None, limit: int = 0, batch_size: int = 200, user: str | None = None):
	"""Cancel + delete transactions in batches until empty (or until limit reached)."""
	frappe.set_user(user or "Administrator")
	_assert_admin()
	overall = {"ok": True, "company": company, "branch": branch, "limit": limit, "batch_size": batch_size, "details": []}

	for dt in _RESET_DOCTYPES:
		filters = _doc_filters(dt, company, branch)
		if not filters:
			continue
		deleted_total = 0
		cancelled_total = 0
		while True:
			to_fetch = batch_size
			if limit and (deleted_total + cancelled_total) >= limit:
				break
			if limit:
				to_fetch = min(to_fetch, max(0, limit - (deleted_total + cancelled_total)))
			names = frappe.get_all(dt, filters=filters, pluck="name", limit=to_fetch)
			if not names:
				break
			for name in reversed(names):
				doc = frappe.get_doc(dt, name)
				if hasattr(doc, "docstatus") and int(doc.docstatus or 0) == 1:
					try:
						doc.cancel()
						cancelled_total += 1
					except Exception:
						# even if cancel fails, still attempt forced delete
						pass
				try:
					frappe.delete_doc(dt, name, ignore_permissions=True, force=1)
					deleted_total += 1
				except Exception:
					pass
			frappe.db.commit()
		overall["details"].append({"doctype": dt, "cancelled": cancelled_total, "deleted": deleted_total})

	log_id = _log_seed_operation(
		"Reset Transactions",
		company,
		branch,
		None,
		0,
		"Success",
		overall,
	)
	overall["log_id"] = log_id
	frappe.db.commit()
	return overall


@frappe.whitelist(methods=["POST"])
def wipe_company_all_data(company: str, branch: str | None = None, confirm_text: str | None = None):
	"""Hard wipe for one company scope: transactions + CoA + core masters."""
	if frappe.session.user != "Administrator":
		frappe.throw(_("Only Administrator can run full company wipe."), frappe.PermissionError)
	_assert_admin()
	if (confirm_text or "").strip() != "DELETE ALL":
		frappe.throw(_("Type DELETE ALL to confirm full wipe."), title=_("Wipe Company Data"))
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Company is required"), title=_("Wipe Company Data"))

	# 1) Cancel + delete all transactions synchronously.
	tx = run_reset_transactions_batched(
		company=company, branch=branch, limit=0, batch_size=300, user=frappe.session.user
	)

	# 2) Reset chart of accounts (with backup + audit log).
	from omnexa_accounting.utils.coa_reset_service import reset_coa

	coa = reset_coa(company=company, branch=branch, confirm_text="RESET COA")

	# 3) Delete core master data bound to this company.
	master_doctypes = ["Customer", "Supplier", "Item", "Employee", "Warehouse", "Bank Account", "Cost Center"]
	master_deleted = []
	for dt in master_doctypes:
		if not frappe.db.exists("DocType", dt):
			continue
		if not frappe.db.has_column(f"tab{dt}", "company"):
			continue
		filters = {"company": company}
		before = frappe.db.count(dt, filters)
		if before:
			frappe.db.delete(dt, filters)
			frappe.db.commit()
		after = frappe.db.count(dt, filters)
		master_deleted.append({"doctype": dt, "before": before, "deleted": max(before - after, 0), "after": after})

	result = {
		"ok": True,
		"company": company,
		"branch": branch,
		"transactions": tx,
		"coa_reset": coa,
		"masters": master_deleted,
	}
	log_id = _log_seed_operation("Reset Transactions", company, branch, None, 0, "Success", result)
	result["log_id"] = log_id
	return result


def _ensure_branch(branch: str) -> tuple[str, str]:
	if not frappe.db.exists("Branch", branch):
		frappe.throw(_("Branch {0} not found").format(branch))
	company = frappe.db.get_value("Branch", branch, "company")
	if not company:
		frappe.throw(_("Branch {0} has no company").format(branch))
	return branch, company


def _ensure_master_data(
	company: str,
	branch: str,
	item_count: int,
	customer_count: int,
	supplier_count: int,
	employee_count: int,
) -> dict:
	def _has_field(doctype: str, fieldname: str) -> bool:
		return bool(frappe.get_meta(doctype).has_field(fieldname))

	if not frappe.db.exists("UOM", "Nos"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert(ignore_permissions=True)

	warehouse_filters = {"company": company}
	if _has_field("Warehouse", "branch"):
		warehouse_filters["branch"] = branch
	warehouse = frappe.db.get_value("Warehouse", warehouse_filters, "name")
	if not warehouse:
		wh_code = ("SIM" + "".join(ch for ch in branch if ch.isalnum()).upper())[:10]
		wh_data = {
			"doctype": "Warehouse",
			"warehouse_name": f"SIM-WH-{branch}",
			"warehouse_code": wh_code,
			"company": company,
		}
		if _has_field("Warehouse", "branch"):
			wh_data["branch"] = branch
		wh = frappe.get_doc(wh_data)
		wh.insert(ignore_permissions=True)
		warehouse = wh.name

	items = []
	service_items = []
	stock_items = []
	for idx in range(1, item_count + 1):
		item_code = f"SIM-{branch}-ITEM-{idx:02d}"
		existing = frappe.db.get_value("Item", {"item_code": item_code}, "name")
		if existing:
			items.append(existing)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": f"Simulation Item {idx}",
					"company": company,
					"stock_uom": "Nos",
					"is_stock_item": 1 if idx <= max(2, item_count // 2) else 0,
				}
			)
			doc.insert(ignore_permissions=True)
			items.append(doc.name)
		if cint(frappe.db.get_value("Item", items[-1], "is_stock_item")):
			stock_items.append(items[-1])
		else:
			service_items.append(items[-1])

	customers = []
	for idx in range(1, customer_count + 1):
		customer_name = f"SIM-CUST-{branch}-{idx:02d}"
		existing = frappe.db.get_value("Customer", {"customer_name": customer_name, "company": company}, "name")
		if existing:
			customers.append(existing)
			continue
		doc = frappe.get_doc({"doctype": "Customer", "customer_name": customer_name, "company": company})
		doc.insert(ignore_permissions=True)
		customers.append(doc.name)

	suppliers = []
	for idx in range(1, supplier_count + 1):
		supplier_name = f"SIM-SUPP-{branch}-{idx:02d}"
		existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name, "company": company}, "name")
		if existing:
			suppliers.append(existing)
			continue
		doc = frappe.get_doc({"doctype": "Supplier", "supplier_name": supplier_name, "company": company})
		doc.insert(ignore_permissions=True)
		suppliers.append(doc.name)

	employees = []
	for idx in range(1, employee_count + 1):
		employee_name = f"SIM-EMP-{branch}-{idx:02d}"
		existing = frappe.db.get_value("Employee", {"employee_name": employee_name, "company": company}, "name")
		if existing:
			employees.append(existing)
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"employee_name": employee_name,
				"employee_code": f"SIM-{idx:03d}",
				"first_name": f"SIM{idx}",
				"company": company,
				"branch": branch,
				"status": "Active",
				"date_of_joining": nowdate(),
			}
		)
		doc.insert(ignore_permissions=True)
		employees.append(doc.name)

	return {
		"warehouse": warehouse,
		"items": items,
		"service_items": service_items or items,
		"stock_items": stock_items or items,
		"customers": customers,
		"suppliers": suppliers,
		"employees": employees,
	}


def _pick_leaf_account(company: str, branch: str | None, account_number: str) -> str | None:
	return _leaf_gl_by_number(company, branch, account_number)


def _submit_if_draft(doc):
	if int(doc.docstatus or 0) == 0:
		doc.submit()


def _insert_sales_invoice(company: str, branch: str, posting_date: str, customer: str, item: str, rate: float) -> str:
	item_code = frappe.db.get_value("Item", item, "item_code")
	currency = _company_currency(company)
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": company,
			"branch": branch,
			"customer": customer,
			"posting_date": posting_date,
			"currency": currency,
			"conversion_rate": 1,
			"remarks": f"SIM-AUTO {branch} {posting_date}",
			"items": [{"item": item, "item_code": item_code, "qty": 1, "rate": rate}],
		}
	)
	si.insert(ignore_permissions=True)
	_submit_if_draft(si)
	return si.name


def _insert_purchase_invoice(
	company: str, branch: str, posting_date: str, supplier: str, item: str, rate: float
) -> str:
	item_code = frappe.db.get_value("Item", item, "item_code")
	currency = _company_currency(company)
	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": company,
			"branch": branch,
			"supplier": supplier,
			"posting_date": posting_date,
			"currency": currency,
			"conversion_rate": 1,
			"remarks": f"SIM-AUTO {branch} {posting_date}",
			"items": [{"item": item, "item_code": item_code, "qty": 1, "rate": rate}],
		}
	)
	pi.insert(ignore_permissions=True)
	_submit_if_draft(pi)
	return pi.name


def _insert_stock_entries(
	company: str, branch: str, posting_date: str, warehouse: str, item: str, receipt_qty: float, issue_qty: float
) -> tuple[str | None, str | None]:
	item_code = frappe.db.get_value("Item", item, "item_code")
	receipt = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": company,
			"branch": branch,
			"posting_date": posting_date,
			"remarks": f"SIM-STOCK-RECEIPT {branch} {posting_date}",
			"items": [{"item_code": item_code, "t_warehouse": warehouse, "qty": receipt_qty, "basic_rate": 80}],
		}
	)
	receipt.insert(ignore_permissions=True)
	_submit_if_draft(receipt)
	issue = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": company,
			"branch": branch,
			"posting_date": posting_date,
			"remarks": f"SIM-STOCK-ISSUE {branch} {posting_date}",
			"items": [{"item_code": item_code, "s_warehouse": warehouse, "qty": issue_qty, "basic_rate": 80}],
		}
	)
	issue.insert(ignore_permissions=True)
	_submit_if_draft(issue)
	return receipt.name, issue.name


def _insert_journal_entry(
	company: str, branch: str, posting_date: str, remarks: str, debit_account: str, credit_account: str, amount: float
) -> str:
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": company,
			"branch": branch,
			"posting_date": posting_date,
			"remarks": remarks,
			"accounts": [
				{"account": debit_account, "debit": amount, "credit": 0},
				{"account": credit_account, "debit": 0, "credit": amount},
			],
		}
	)
	je.insert(ignore_permissions=True)
	_submit_if_draft(je)
	return je.name


@frappe.whitelist(methods=["POST"])
def start_branch_enterprise_simulation_seed(
	branch: str,
	months: int | str = 6,
	daily_purchase_invoices: int | str = 10,
	daily_sales_invoices: int | str = 50,
	employees: int | str = 5,
	customers: int | str = 5,
	suppliers: int | str = 5,
	items: int | str = 10,
):
	_assert_admin()
	branch, company = _ensure_branch(branch)
	payload = {
		"branch": branch,
		"company": company,
		"months": max(1, cint(months or 6)),
		"daily_purchase_invoices": max(1, cint(daily_purchase_invoices or 10)),
		"daily_sales_invoices": max(1, cint(daily_sales_invoices or 50)),
		"employees": max(1, cint(employees or 5)),
		"customers": max(1, cint(customers or 5)),
		"suppliers": max(1, cint(suppliers or 5)),
		"items": max(2, cint(items or 10)),
		"user": frappe.session.user,
	}
	job = frappe.enqueue(
		"omnexa_accounting.utils.production_readiness.run_branch_enterprise_simulation_seed",
		queue="long",
		timeout=7200,
		**payload,
	)
	return {"ok": True, "queued": True, "job_id": job.id if job else None, "config": payload}


def run_branch_enterprise_simulation_seed(**kwargs):
	params = frappe._dict(kwargs or {})
	if isinstance(params.get("kwargs"), dict):
		# Backward compatibility for previously enqueued payload style.
		params = frappe._dict(params.get("kwargs"))
	branch = params.branch
	company = params.company
	months = cint(params.get("months") or 6)
	daily_pi = cint(params.get("daily_purchase_invoices") or 10)
	daily_si = cint(params.get("daily_sales_invoices") or 50)
	employee_count = cint(params.get("employees") or 5)
	customer_count = cint(params.get("customers") or 5)
	supplier_count = cint(params.get("suppliers") or 5)
	item_count = cint(params.get("items") or 10)

	frappe.set_user(params.user or "Administrator")
	try:
		masters = _ensure_master_data(
			company=company,
			branch=branch,
			item_count=item_count,
			customer_count=customer_count,
			supplier_count=supplier_count,
			employee_count=employee_count,
		)

		end_date = getdate(nowdate())
		start_date = add_days(add_months(end_date, -months), 1)
		service_items = masters.get("service_items") or []
		stock_items = masters.get("stock_items") or []
		customers = masters.get("customers") or []
		suppliers = masters.get("suppliers") or []
		employees = masters.get("employees") or []
		warehouse = masters.get("warehouse")

		salary_expense = _pick_leaf_account(company, branch, "5101")
		opex_gl = _pick_leaf_account(company, branch, "5102")
		finance_cost_gl = _pick_leaf_account(company, branch, "5109")
		bank_gl = _pick_leaf_account(company, branch, "1102")
		equity_gl = _pick_leaf_account(company, branch, "3101")
		payable_gl = _pick_leaf_account(company, branch, "2101")
		receivable_gl = _pick_leaf_account(company, branch, "1103")

		summary = {
			"ok": True,
			"company": company,
			"branch": branch,
			"from_date": str(start_date),
			"to_date": str(end_date),
			"masters": {
				"items": len(masters.get("items") or []),
				"customers": len(customers),
				"suppliers": len(suppliers),
				"employees": len(employees),
				"warehouse": warehouse,
			},
			"transactions": {
				"sales_invoice_submitted": 0,
				"purchase_invoice_submitted": 0,
				"stock_receipt_submitted": 0,
				"stock_issue_submitted": 0,
				"salary_journal_submitted": 0,
				"opex_journal_submitted": 0,
				"finance_cost_journal_submitted": 0,
				"bank_deposit_journal_submitted": 0,
				"errors": [],
			},
			"kpis": {
				"simulated_sales_total": 0.0,
				"simulated_purchase_total": 0.0,
				"simulated_gross_profit": 0.0,
				"simulated_customer_receivables": 0.0,
				"simulated_supplier_payables": 0.0,
			},
		}

		def _push_error(message: str):
			errs = summary["transactions"]["errors"]
			if len(errs) < 200:
				errs.append(message)

		d = start_date
		day_counter = 0
		while d <= end_date:
			posting_date = str(d)
			for i in range(daily_pi):
				try:
					supplier = suppliers[i % len(suppliers)]
					item = service_items[i % len(service_items)]
					rate = 70 + (i % 7)
					_insert_purchase_invoice(company, branch, posting_date, supplier, item, rate=rate)
					summary["transactions"]["purchase_invoice_submitted"] += 1
					summary["kpis"]["simulated_purchase_total"] += float(rate)
					summary["kpis"]["simulated_supplier_payables"] += float(rate)
				except Exception:
					_push_error(f"PI {posting_date}: {frappe.get_traceback()}")
			for i in range(daily_si):
				try:
					customer = customers[i % len(customers)]
					item = service_items[i % len(service_items)]
					rate = 110 + (i % 9)
					_insert_sales_invoice(company, branch, posting_date, customer, item, rate=rate)
					summary["transactions"]["sales_invoice_submitted"] += 1
					summary["kpis"]["simulated_sales_total"] += float(rate)
					summary["kpis"]["simulated_customer_receivables"] += float(rate)
				except Exception:
					_push_error(f"SI {posting_date}: {frappe.get_traceback()}")
			try:
				item = stock_items[day_counter % len(stock_items)]
				receipt_name, issue_name = _insert_stock_entries(
					company=company,
					branch=branch,
					posting_date=posting_date,
					warehouse=warehouse,
					item=item,
					receipt_qty=20,
					issue_qty=12,
				)
				if receipt_name:
					summary["transactions"]["stock_receipt_submitted"] += 1
				if issue_name:
					summary["transactions"]["stock_issue_submitted"] += 1
			except Exception:
				_push_error(f"SE {posting_date}: {frappe.get_traceback()}")

			day_counter += 1
			d = add_days(d, 1)
			if day_counter % 5 == 0:
				frappe.db.commit()

		month_cursor = getdate(start_date.replace(day=1))
		month_end = getdate(end_date.replace(day=1))
		while month_cursor <= month_end:
			posting_date = str(month_cursor)
			for emp in employees:
				if salary_expense and bank_gl:
					try:
						_insert_journal_entry(
							company=company,
							branch=branch,
							posting_date=posting_date,
							remarks=f"SIM Payroll {emp} {posting_date}",
							debit_account=salary_expense,
							credit_account=bank_gl if not payable_gl else payable_gl,
							amount=2500,
						)
						summary["transactions"]["salary_journal_submitted"] += 1
					except Exception:
						_push_error(f"PAY {posting_date}: {frappe.get_traceback()}")
					if payable_gl and bank_gl:
						try:
							_insert_journal_entry(
								company=company,
								branch=branch,
								posting_date=posting_date,
								remarks=f"SIM Payroll Payment {emp} {posting_date}",
								debit_account=payable_gl,
								credit_account=bank_gl,
								amount=2500,
							)
						except Exception:
							_push_error(f"PAYMENT {posting_date}: {frappe.get_traceback()}")
			if bank_gl and equity_gl:
				try:
					deposit_amount = 250000 if month_cursor == getdate(start_date.replace(day=1)) else 50000
					_insert_journal_entry(
						company=company,
						branch=branch,
						posting_date=posting_date,
						remarks=f"SIM Bank Deposit {posting_date}",
						debit_account=bank_gl,
						credit_account=equity_gl,
						amount=deposit_amount,
					)
					summary["transactions"]["bank_deposit_journal_submitted"] += 1
				except Exception:
					_push_error(f"DEPOSIT {posting_date}: {frappe.get_traceback()}")
			if opex_gl and bank_gl:
				try:
					_insert_journal_entry(
						company=company,
						branch=branch,
						posting_date=posting_date,
						remarks=f"SIM Operating Expenses {posting_date}",
						debit_account=opex_gl,
						credit_account=bank_gl,
						amount=8000,
					)
					summary["transactions"]["opex_journal_submitted"] += 1
				except Exception:
					_push_error(f"OPEX {posting_date}: {frappe.get_traceback()}")
			if finance_cost_gl and bank_gl:
				try:
					_insert_journal_entry(
						company=company,
						branch=branch,
						posting_date=posting_date,
						remarks=f"SIM Finance Cost {posting_date}",
						debit_account=finance_cost_gl,
						credit_account=bank_gl,
						amount=1200,
					)
					summary["transactions"]["finance_cost_journal_submitted"] += 1
				except Exception:
					_push_error(f"FIN {posting_date}: {frappe.get_traceback()}")
			month_cursor = add_months(month_cursor, 1)
			frappe.db.commit()

		summary["kpis"]["simulated_gross_profit"] = round(
			float(summary["kpis"]["simulated_sales_total"]) - float(summary["kpis"]["simulated_purchase_total"]), 2
		)
		# Keep receivables/payables bounded so reports show realistic outstanding.
		# If receivable/payable GL does not exist in a tenant, this step is skipped safely.
		if bank_gl and receivable_gl and summary["kpis"]["simulated_customer_receivables"] > 0:
			try:
				collection_amount = round(summary["kpis"]["simulated_customer_receivables"] * 0.65, 2)
				_insert_journal_entry(
					company=company,
					branch=branch,
					posting_date=str(end_date),
					remarks=f"SIM Collections Closing {end_date}",
					debit_account=bank_gl,
					credit_account=receivable_gl,
					amount=collection_amount,
				)
				summary["kpis"]["simulated_customer_receivables"] = round(
					summary["kpis"]["simulated_customer_receivables"] - collection_amount, 2
				)
			except Exception:
				_push_error(f"AR-CLOSE {end_date}: {frappe.get_traceback()}")
		if bank_gl and payable_gl and summary["kpis"]["simulated_supplier_payables"] > 0:
			try:
				payment_amount = round(summary["kpis"]["simulated_supplier_payables"] * 0.55, 2)
				_insert_journal_entry(
					company=company,
					branch=branch,
					posting_date=str(end_date),
					remarks=f"SIM Supplier Payments Closing {end_date}",
					debit_account=payable_gl,
					credit_account=bank_gl,
					amount=payment_amount,
				)
				summary["kpis"]["simulated_supplier_payables"] = round(
					summary["kpis"]["simulated_supplier_payables"] - payment_amount, 2
				)
			except Exception:
				_push_error(f"AP-CLOSE {end_date}: {frappe.get_traceback()}")

		log_id = _log_seed_operation(
			"Branch Enterprise Simulation Seed",
			company,
			branch,
			"Enterprise",
			0,
			"Success",
			summary,
		)
		summary["log_id"] = log_id
		frappe.db.commit()
		return summary
	except Exception:
		error_summary = {
			"ok": False,
			"company": company,
			"branch": branch,
			"error": frappe.get_traceback(),
		}
		_log_seed_operation(
			"Branch Enterprise Simulation Seed",
			company,
			branch,
			"Enterprise",
			0,
			"Failed",
			error_summary,
		)
		frappe.db.commit()
		raise


def auto_bootstrap_defaults_after_install() -> dict:
	"""Auto-configure company/branch defaults so fresh installs are ready to use."""
	from omnexa_accounting.utils.company_financial_defaults import (
		apply_branch_default_gl_from_company,
		apply_company_default_gl_from_coa,
	)

	existing = frappe.db.get_value(
		"Production Seed Log",
		{"operation": "Auto Bootstrap Defaults (Install)", "status": ["in", ["Success", "Partial"]]},
		"name",
	)
	if existing:
		return {"ok": True, "skipped": True, "reason": "already_bootstrapped", "log_id": existing}

	companies = frappe.get_all("Company", pluck="name")
	summary = {
		"ok": True,
		"companies": len(companies),
		"coa_bootstrapped": 0,
		"company_gl_defaults_applied": 0,
		"branch_gl_defaults_applied": 0,
		"demo_masters_seeded": 0,
		"errors": [],
	}

	for company in companies:
		try:
			_run_professional_coa_sync(company=company, branch=None, activity=None)
			summary["coa_bootstrapped"] += 1
		except Exception:
			summary["errors"].append(f"COA {company}: {frappe.get_traceback()}")
			continue

		try:
			apply_company_default_gl_from_coa(company=company, branch=None, overwrite=0)
			summary["company_gl_defaults_applied"] += 1
		except Exception:
			summary["errors"].append(f"Company defaults {company}: {frappe.get_traceback()}")

		branches = frappe.get_all("Branch", filters={"company": company}, pluck="name")
		for branch in branches:
			try:
				apply_branch_default_gl_from_company(company=company, branch=branch, overwrite=0)
				summary["branch_gl_defaults_applied"] += 1
			except Exception:
				summary["errors"].append(f"Branch defaults {branch}: {frappe.get_traceback()}")
				continue
			try:
				# Keep fresh setup practical: seed branch masters only (no heavy transactions).
				_ensure_master_data(
					company=company,
					branch=branch,
					item_count=10,
					customer_count=5,
					supplier_count=5,
					employee_count=5,
				)
				summary["demo_masters_seeded"] += 1
			except Exception:
				summary["errors"].append(f"Masters seed {branch}: {frappe.get_traceback()}")
		frappe.db.commit()

	if companies:
		log_id = _log_seed_operation(
			"Auto Bootstrap Defaults (Install)",
			companies[0],
			None,
			"General",
			0,
			"Success" if not summary["errors"] else "Partial",
			summary,
		)
		summary["log_id"] = log_id
	return summary

