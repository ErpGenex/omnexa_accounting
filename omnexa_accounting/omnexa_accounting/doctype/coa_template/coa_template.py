# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from omnexa_accounting.utils.coa_template_service import _clean_main_account_type, _clean_sub_account_type


class COATemplate(Document):
	def validate(self):
		seen = set()
		for row in self.accounts or []:
			# Normalize legacy COA labels before Select validation/save.
			row.main_account_type = _clean_main_account_type(row.main_account_type)
			row.sub_account_type = _clean_sub_account_type(row.sub_account_type)
			code = (row.account_number or "").strip()
			if not code:
				frappe.throw(_("COA Template Line: Account Number is required."), title=_("COA Template"))
			# Keep account names canonical on template rows before registration.
			name_en = (row.account_name_en or "").strip()
			name_ar = (row.account_name_ar or "").strip()
			row.account_name_en = name_en or name_ar or code
			row.account_name_ar = name_ar or row.account_name_en
			if code in seen:
				frappe.throw(_("Duplicate Account Number in template: {0}").format(code), title=_("COA Template"))
			seen.add(code)

