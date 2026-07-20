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


def balance_sheet_chart(assets: float, liabilities: float, equity: float) -> dict:
	return {
		"data": {
			"labels": [_("Assets"), _("Liabilities"), _("Equity")],
			"datasets": [{"name": _("Balance"), "values": [assets, liabilities, equity]}],
		},
		"type": "bar",
		"title": _("Assets vs Liabilities vs Equity"),
		"height": 280,
	}


def aging_bucket_chart(rows: list[dict], *, bucket_field: str = "aging_bucket", value_field: str = "outstanding") -> dict:
	totals: dict[str, float] = {}
	order = ["Current", "1-30 days", "31-60 days", "61-90 days", "90+ days"]
	for row in rows:
		bucket = str(row.get(bucket_field) or "")
		totals[bucket] = totals.get(bucket, 0.0) + float(row.get(value_field) or 0)
	labels = [b for b in order if b in totals] + [b for b in totals if b not in order]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Outstanding"), "values": [totals[b] for b in labels]}],
		},
		"type": "bar",
		"title": _("Outstanding by Aging Bucket"),
		"height": 280,
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
