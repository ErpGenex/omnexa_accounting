# Copyright (c) 2026, Omnexa
"""Post FS parity matrix lines → Journal Entry (gated by omnexa_core feature flag)."""

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from omnexa_accounting.utils.invoice_posting import _company_default, _find_existing_posting_je, _make_je
from omnexa_core.omnexa_core.feature_flags import is_feature_enabled

FS_LIVE_POSTING_FLAG = "fs_live_gl_posting"

# account_role → Company default field (first match wins)
ROLE_COMPANY_FIELDS: dict[str, tuple[str, ...]] = {
	"bank": ("default_cash_gl", "default_bank_gl"),
	"loan_receivable": ("default_receivable_gl",),
	"lease_liability": ("default_trade_payable_gl",),
	"rou_asset": ("default_inventory_gl",),
	"termination_pl": ("default_opex_gl", "default_cogs_gl"),
	"cash_account_role": ("default_cash_gl", "default_bank_gl")}


def is_fs_live_posting_enabled() -> bool:
	return is_feature_enabled(FS_LIVE_POSTING_FLAG, default=False)


def resolve_role_account(company: str, account_role: str) -> str | None:
	"""Map FS matrix role → GL Account name for company."""
	role = (account_role or "").strip().lower()
	conf = frappe.get_conf() or {}
	overrides = conf.get("omnexa_fs_gl_role_accounts") or {}
	if isinstance(overrides, dict):
		key = f"{company}::{role}"
		if key in overrides:
			return overrides[key]
		if role in overrides:
			return overrides[role]

	for field in ROLE_COMPANY_FIELDS.get(role, ()):
		acct = _company_default(company, field)
		if acct:
			return acct
	return _fallback_gl_for_role(company, role)


def _fallback_gl_for_role(company: str, role: str) -> str | None:
	if role in ("bank", "cash_account_role"):
		return frappe.db.get_value(
			"GL Account",
			{"company": company, "account_type": "Bank", "is_group": 0
	},
			"name",
			order_by="name asc",
		)
	if role in ("rou_asset", "loan_receivable"):
		return frappe.db.get_value(
			"GL Account",
			{"company": company, "account_type": "Asset", "is_group": 0
	},
			"name",
			order_by="name asc",
		)
	if role == "lease_liability":
		return frappe.db.get_value(
			"GL Account",
			{"company": company, "account_type": "Liability", "is_group": 0
	},
			"name",
			order_by="name asc",
		)
	if role == "termination_pl":
		return frappe.db.get_value(
			"GL Account",
			{"company": company, "account_type": "Expense", "is_group": 0
	},
			"name",
			order_by="name asc",
		)
	return None


def matrix_lines_to_je_lines(company: str, matrix_lines: list[dict]) -> list[dict]:
	je_lines: list[dict] = []
	missing: list[str] = []
	for row in matrix_lines or []:
		role = row.get("account_role") or ""
		account = resolve_role_account(company, role)
		if not account:
			missing.append(role)
			continue
		debit = flt(row.get("debit"))
		credit = flt(row.get("credit"))
		if debit <= 0 and credit <= 0:
			continue
		je_lines.append({"account": account, "debit": debit, "credit": credit
	})
	if missing:
		frappe.throw(
			_("Missing GL mapping for roles: {0}. Set Company defaults or omnexa_fs_gl_role_accounts in site_config.").format(
				", ".join(sorted(set(missing)))
			),
			title=_("FS GL Posting"),
		)
	if not je_lines:
		frappe.throw(_("No posting lines"), title=_("FS GL Posting"))
	debit_sum = sum(flt(l["debit"]) for l in je_lines)
	credit_sum = sum(flt(l["credit"]) for l in je_lines)
	if flt(debit_sum - credit_sum, 2) != 0:
		frappe.throw(_("Matrix lines are unbalanced"), title=_("FS GL Posting"))
	return je_lines


def post_fs_matrix_gl(
	*,
	company: str,
	scenario: str,
	matrix_lines: list[dict],
	posting_date: str | None = None,
	branch: str | None = None,
	reference: str | None = None,
	remarks: str | None = None,
) -> dict:
	"""Create Journal Entry from FS matrix preview lines when feature flag is ON."""
	preview = {"scenario": scenario, "lines": matrix_lines, "live_posting_enabled": is_fs_live_posting_enabled()
	}
	if not is_fs_live_posting_enabled():
		return {"posted": False, "reason": "feature_flag_off", **preview}

	ref = reference or f"FS:{scenario}"
	existing = _find_existing_posting_je(company, branch, ref)
	if existing:
		return {"posted": True, "journal_entry": existing, "idempotent": True, **preview}

	je_lines = matrix_lines_to_je_lines(company, matrix_lines)
	je_name = _make_je(
		company=company,
		branch=branch,
		posting_date=getdate(posting_date or today()),
		reference=ref,
		remarks=remarks or f"FS matrix {scenario}",
		lines=je_lines,
	)
	return {"posted": True, "journal_entry": je_name, "idempotent": False, **preview}
