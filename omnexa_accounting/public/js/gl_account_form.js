frappe.ui.form.on("GL Account", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Open General Ledger"), () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Company is required."));
				return;
			}
			frappe.route_options = {
				company: frm.doc.company,
				account: frm.doc.name,
				branch: frm.doc.branch || undefined,
			};
			frappe.set_route("query-report", "General Ledger");
		});

		frm.add_custom_button(__("Show Balance"), async () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Company is required."));
				return;
			}
			const r = await frappe.call({
				method: "omnexa_accounting.utils.ledger_tools.get_gl_account_balance",
				args: {
					company: frm.doc.company,
					account: frm.doc.name,
					branch: frm.doc.branch || null,
				},
			});
			const out = r.message || {};
			if (!out.ok) return;
			frappe.msgprint(
				__(
					"Debit: {0}<br>Credit: {1}<br><b>Balance:</b> {2}",
					[out.debit || 0, out.credit || 0, out.balance || 0],
				),
			);
		});
	},
});

