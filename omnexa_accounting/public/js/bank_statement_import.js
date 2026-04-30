frappe.ui.form.on("Bank Statement Import", {
	refresh(frm) {
		if (frm.doc.docstatus === 2) return;
		frm.add_custom_button(__("Auto Match Lines"), async () => {
			const r = await frappe.call({
				method: "omnexa_core.omnexa_core.finance.api.auto_match_bank_statement_import",
				args: { bank_statement_import: frm.doc.name },
				freeze: true,
				freeze_message: __("Auto-matching statement lines..."),
			});
			const m = r?.message || {};
			frappe.show_alert({
				message: __("Matched {0}/{1} lines", [m.matched || 0, m.total || 0]),
				indicator: "green",
			});
			frm.reload_doc();
		});
	},
});

