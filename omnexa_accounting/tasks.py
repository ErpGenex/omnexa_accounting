# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

from __future__ import annotations

import frappe
from frappe.utils import getdate, today


def process_period_close_reminders():
	"""Mark accounting periods overdue when close deadline has passed."""
	current = getdate(today())
	rows = frappe.get_all(
		"Accounting Period",
		filters={"status": "Open", "period_end_date": ["<", current]},
		fields=["name"],
		limit_page_length=200,
	)
	for row in rows:
		frappe.db.set_value("Accounting Period", row.name, "status", "Overdue", update_modified=False)
