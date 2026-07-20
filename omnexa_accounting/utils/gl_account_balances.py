from __future__ import annotations

import frappe
from frappe.utils import flt


def recompute_gl_account_balance_snapshot(accounts: list[str] | None = None) -> int:
	"""Recompute balance snapshot for GL Account(s) from submitted Journal Entries.

	Balance = SUM(debit - credit) from Journal Entry Account lines where parent JE is submitted.
	"""
	if not frappe.db.exists("DocType", "GL Account"):
		return 0
	if not frappe.get_meta("GL Account").has_field("balance_snapshot"):
		return 0

	params = {}
	where = ""
	if accounts:
		params["accounts"] = tuple(set(accounts))
		where = "WHERE jea.account IN %(accounts)s"

	rows = frappe.db.sql(
		f"""
		SELECT
			jea.account AS account,
			COALESCE(SUM(jea.debit - jea.credit), 0) AS balance
		FROM `tabJournal Entry Account` jea
		INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
		{where}
		  {"AND" if where else "WHERE"} je.docstatus = 1
		GROUP BY jea.account
		""",
		params,
		as_dict=True,
	)
	balance_map = {r.account: flt(r.balance) for r in rows}

	target_accounts = accounts or frappe.get_all("GL Account", pluck="name")
	updated = 0
	for acc in target_accounts:
		new_bal = flt(balance_map.get(acc))
		frappe.db.set_value("GL Account", acc, "balance_snapshot", new_bal, update_modified=False)
		updated += 1
	frappe.db.commit()
	return updated


def on_journal_entry_submit(doc, method=None):
	accounts = [row.account for row in (doc.get("accounts") or []) if row.account]
	recompute_gl_account_balance_snapshot(accounts)


def on_journal_entry_cancel(doc, method=None):
	accounts = [row.account for row in (doc.get("accounts") or []) if row.account]
	recompute_gl_account_balance_snapshot(accounts)

