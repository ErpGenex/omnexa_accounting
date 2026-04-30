frappe.ui.form.on("Stock Transfer Request", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		if (frm.doc.executed_stock_entry) return;
		frm.add_custom_button(__("Execute Transfer"), async () => {
			const r = await frappe.call({
				method: "omnexa_core.omnexa_core.inventory.api.execute_stock_transfer_request",
				args: { transfer_request: frm.doc.name },
				freeze: true,
				freeze_message: __("Executing stock transfer..."),
			});
			if (r?.message?.stock_entry) {
				frappe.show_alert({
					message: __("Stock Entry created: {0}", [r.message.stock_entry]),
					indicator: "green",
				});
				frm.reload_doc();
			}
		});
	},
});

