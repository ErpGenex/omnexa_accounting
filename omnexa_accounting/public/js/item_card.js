frappe.ui.form.on("Item", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Item Movements"), () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Set Company on the Item to filter movements."));
				return;
			}
			frappe.route_options = {
				company: frm.doc.company,
				item: frm.doc.name,
			};
			frappe.set_route("query-report", "Stock Movement");
		});

		frm.add_custom_button(__("Auto Reorder PR"), async () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Set Company on the Item first."));
				return;
			}
			const branch = frappe.defaults.get_user_default("Branch") || "";
			const r = await frappe.call({
				method: "omnexa_core.omnexa_core.inventory.api.create_purchase_request_from_reorder",
				args: {
					company: frm.doc.company,
					branch: branch,
					limit: 200,
					min_suggested_qty: 0.0001,
				},
				freeze: true,
				freeze_message: __("Creating Purchase Request from reorder suggestions..."),
			});
			if (r?.message?.created) {
				frappe.msgprint(__("Purchase Request created: {0}", [r.message.created]));
				return;
			}
			frappe.msgprint(__(r?.message?.skipped || "No Purchase Request created."));
		});
	},
});

