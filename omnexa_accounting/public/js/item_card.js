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
	},
});

