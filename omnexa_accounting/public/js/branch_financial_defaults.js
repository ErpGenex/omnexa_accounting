// Copyright (c) 2026, Omnexa and contributors
// License: MIT. See license.txt
//
// Branch demo simulation buttons live on Branch → Demo data tab (native Button fields).
// This script only filters branch GL link fields.

frappe.ui.form.on("Branch", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		const company = frm.doc.company;
		if (!company) {
			return;
		}
		const branchGlFields = [
			"branch_default_petty_cash_gl",
			"branch_default_bank_gl",
			"branch_default_receivable_gl",
			"branch_default_trade_payable_gl",
		];
		branchGlFields.forEach((fieldname) => {
			frm.set_query(fieldname, () => ({
				filters: { company },
			}));
		});
	},
});
