# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import getdate, nowdate

from omnexa_core.omnexa_core.feature_flags import is_feature_enabled


_DEFAULT_DIGITS = 5


def _is_blank(value) -> bool:
	return value is None or (isinstance(value, str) and not value.strip())


def _build_regex(prefix: str, digits: int) -> re.Pattern:
	p = re.escape(prefix)
	return re.compile(rf"^{p}\d{{{digits}}}$")


def ensure_entity_code(
	doc,
	*,
	fieldname: str,
	prefix: str,
	digits: int = _DEFAULT_DIGITS,
	flag_name: str = "enterprise_auto_coding",
) -> None:
	"""
	Set and validate a stable entity code (e.g. ITM-00001) in a dedicated field.

	Safety rules (no-break):
	- Does nothing unless feature flag is enabled.
	- Generates code only when the field is empty.
	- Validation is permissive: it only enforces format if user chose our prefix.
	"""
	if not is_feature_enabled(flag_name, default=False):
		return

	current = doc.get(fieldname)
	if _is_blank(current):
		pattern = f"{prefix}.{'#' * digits}"
		doc.set(fieldname, make_autoname(pattern))
		return

	# Manual override validation (permissive).
	current = str(current).strip()
	if current.startswith(prefix):
		rx = _build_regex(prefix, digits)
		if not rx.match(current):
			frappe.throw(
				_("{0} must match format {1}{2} (example: {1}{3}).").format(
					doc.meta.get_label(fieldname) or fieldname,
					prefix,
					"0" * digits,
					"0" * (digits - 1) + "1",
				),
				title=_("Auto coding"),
			)

	# Always enforce uniqueness on the target doctype/field.
	filters = {fieldname: current}
	# Most master doctypes in this app are company-scoped; enforce per-company when field exists.
	if getattr(doc, "meta", None) and doc.meta.has_field("company") and doc.get("company"):
		filters["company"] = doc.get("company")
	existing = frappe.db.get_value(doc.doctype, filters, "name")
	if existing and existing != doc.name:
		label = doc.meta.get_label(fieldname) if getattr(doc, "meta", None) else fieldname
		frappe.throw(
			_("{0} must be unique. Existing record: {1}").format(label or fieldname, existing),
			title=_("Duplicate"),
		)


def ensure_invoice_name(
	doc,
	*,
	prefix: str,
	date_field: str = "posting_date",
	digits: int = _DEFAULT_DIGITS,
	flag_name: str = "enterprise_document_numbering",
) -> None:
	"""
	Set invoice/journal document name like SINV-YYYY-00001.

	Safety rules (no-break):
	- Does nothing unless feature flag is enabled.
	- Only sets name when inserting (name empty).
	- Resets yearly by baking year into series key.
	"""
	if not is_feature_enabled(flag_name, default=False):
		return
	if getattr(doc, "name", None):
		return

	raw_date = doc.get(date_field) or nowdate()
	year = getdate(raw_date).year
	pattern = f"{prefix}{year}-.{'#' * digits}"
	doc.name = make_autoname(pattern)


def ensure_simple_doc_name(
	doc,
	*,
	prefix: str,
	digits: int = _DEFAULT_DIGITS,
	flag_name: str = "enterprise_auto_coding",
) -> None:
	"""Set document name like AST-00001 (no year segment)."""
	if not is_feature_enabled(flag_name, default=False):
		return
	if getattr(doc, "name", None):
		return
	pattern = f"{prefix}.{'#' * digits}"
	doc.name = make_autoname(pattern)

