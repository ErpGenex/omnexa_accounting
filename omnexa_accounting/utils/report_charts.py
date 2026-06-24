# Copyright (c) 2026, Omnexa and contributors
# License: MIT

"""Chart helpers for financial Script Reports."""

from __future__ import annotations

from frappe import _


def currency_bar_chart(rows: list[dict], *, label_field: str, value_field: str, title: str) -> dict:
	labels = [str(r.get(label_field) or "") for r in rows[:12]]
	values = [float(r.get(value_field) or 0) for r in rows[:12]]
	return {
		"data": {"labels": labels, "datasets": [{"name": title, "values": values}]},
		"type": "bar",
		"title": _(title),
		"height": 260,
	}


def trial_balance_chart(rows: list[dict]) -> dict:
	"""Top accounts by closing balance magnitude."""
	scored = []
	for row in rows:
		closing = float(row.get("closing_debit") or 0) - float(row.get("closing_credit") or 0)
		scored.append((abs(closing), row.get("account_name") or row.get("account"), closing))
	scored.sort(reverse=True)
	top = scored[:8]
	return {
		"data": {
			"labels": [t[1] for t in top],
			"datasets": [{"name": _("Closing Balance"), "values": [t[2] for t in top]}],
		},
		"type": "bar",
		"title": _("Top Accounts by Closing Balance"),
		"height": 280,
	}
