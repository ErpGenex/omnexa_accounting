# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class Budget(Document):
	def validate(self):
		if self.from_date and self.to_date and getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date."), title=_("Budget"))
		if not self.budget_lines:
			frappe.throw(_("Add at least one budget line."), title=_("Budget"))
		seen = set()
		for row in self.budget_lines:
			if not row.gl_account:
				continue
			key = (
				row.gl_account,
				(row.cost_center or "").strip(),
				str(row.period_month or ""),
			)
			if key in seen:
				frappe.throw(_("Duplicate budget line for the same GL / Cost Center / Month."), title=_("Budget"))
			seen.add(key)
			gl_co = frappe.db.get_value("GL Account", row.gl_account, "company")
			if gl_co and self.company and gl_co != self.company:
				frappe.throw(
					_("Row {0}: GL Account must belong to the same company.").format(row.idx),
					title=_("Budget"),
				)
			at = frappe.db.get_value("GL Account", row.gl_account, "account_type")
			if at not in ("Income", "Expense"):
				frappe.throw(
					_("Row {0}: Budget lines may only reference Income or Expense accounts.").format(row.idx),
					title=_("Budget"),
				)
			if flt(row.budget_amount) < 0:
				frappe.throw(_("Row {0}: Budget amount cannot be negative.").format(row.idx), title=_("Budget"))
			if row.get("cost_center"):
				cc_co = frappe.db.get_value("Cost Center", row.cost_center, "company")
				if cc_co and self.company and cc_co != self.company:
					frappe.throw(
						_("Row {0}: Cost Center must belong to the same company.").format(row.idx),
						title=_("Budget"),
					)
			if row.get("period_month"):
				pm = getdate(row.period_month)
				if getdate(self.from_date) > pm or pm > getdate(self.to_date):
					frappe.throw(
						_("Row {0}: For Month must fall between Budget From Date and To Date.").format(row.idx),
						title=_("Budget"),
					)
