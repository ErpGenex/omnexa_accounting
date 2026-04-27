from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate


@frappe.whitelist()
def get_invoice_posting_journal_entry(doctype: str, docname: str, company: str, branch: str | None = None) -> str | None:
	"""Return the auto-posting Journal Entry name for an invoice, if found."""
	if not (doctype and docname and company):
		return None
	if not frappe.db.exists("Journal Entry", {"company": company}):
		return None
	ref = f"{doctype}:{docname}"
	filters = {"company": company, "reference": ref}
	if branch and frappe.get_meta("Journal Entry").has_field("branch"):
		filters["branch"] = branch
	return frappe.db.get_value("Journal Entry", filters, "name")


@frappe.whitelist()
def get_gl_account_balance(
	company: str,
	account: str,
	branch: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Compute balance from submitted Journal Entry lines (debit-credit)."""
	if not company or not account:
		frappe.throw(_("Company and Account are required."), title=_("Filters"))

	conditions = ["je.company=%(company)s", "je.docstatus=1", "jea.account=%(account)s"]
	params = {"company": company, "account": account}

	if branch and frappe.get_meta("Journal Entry").has_field("branch"):
		conditions.append("je.branch=%(branch)s")
		params["branch"] = branch
	if from_date:
		conditions.append("je.posting_date >= %(from_date)s")
		params["from_date"] = getdate(from_date)
	if to_date:
		conditions.append("je.posting_date <= %(to_date)s")
		params["to_date"] = getdate(to_date)

	row = frappe.db.sql(
		f"""
		SELECT
			COALESCE(SUM(jea.debit),0) AS debit,
			COALESCE(SUM(jea.credit),0) AS credit
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		WHERE {' AND '.join(conditions)}
		""",
		params,
		as_dict=True,
	)
	r = row[0] if row else {}
	debit = float(r.get("debit") or 0)
	credit = float(r.get("credit") or 0)
	return {"ok": True, "debit": debit, "credit": credit, "balance": debit - credit}

