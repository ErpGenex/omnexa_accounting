# Copyright (c) 2026, Omnexa
from frappe.tests.utils import FrappeTestCase

import frappe

from omnexa_accounting.utils.fs_matrix_posting import (
	FS_LIVE_POSTING_FLAG,
	is_fs_live_posting_enabled,
	matrix_lines_to_je_lines,
	post_fs_matrix_gl,
)
from omnexa_finance_engine.fs_posting_matrix import preview_loan_disbursement_posting


class TestFsMatrixPosting(FrappeTestCase):
	def test_flag_off_returns_preview_only(self):
		old = frappe.local.conf.get("omnexa_feature_flags")
		frappe.local.conf["omnexa_feature_flags"] = {FS_LIVE_POSTING_FLAG: False}
		try:
			lines = preview_loan_disbursement_posting(__import__("decimal").Decimal("100"))
			out = post_fs_matrix_gl(company="_Test", scenario="loan_disbursement", matrix_lines=lines)
			self.assertFalse(out["posted"])
			self.assertEqual(out["reason"], "feature_flag_off")
		finally:
			if old is None:
				frappe.local.conf.pop("omnexa_feature_flags", None)
			else:
				frappe.local.conf["omnexa_feature_flags"] = old

	def test_matrix_lines_to_je_requires_accounts(self):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("No company")
		lines = preview_loan_disbursement_posting(__import__("decimal").Decimal("10"))
		try:
			je_lines = matrix_lines_to_je_lines(company, lines)
			self.assertTrue(len(je_lines) >= 2)
		except Exception as exc:
			self.assertIn("Missing GL mapping", str(exc))
