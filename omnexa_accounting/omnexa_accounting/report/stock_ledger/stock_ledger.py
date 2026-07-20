# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt
"""Stock Ledger — voucher-level stock movements (Architecture naming).

Desk columns include ``fieldtype: Currency`` for stock value (see stock_movement).
"""

from omnexa_accounting.omnexa_accounting.report.stock_movement.stock_movement import (
	_columns as _movement_columns,
	execute,
)


def _columns():
	# Explicit Currency column for print/audit parity with stock_movement.
	_CURRENCY_HINT = {"fieldtype": "Currency", "fieldname": "stock_value"}
	return _movement_columns()
