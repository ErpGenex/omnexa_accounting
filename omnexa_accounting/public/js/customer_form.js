frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Customer Statement"), () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Company is required on Customer."));
				return;
			}
			frappe.route_options = {
				company: frm.doc.company,
				customer: frm.doc.name,
			};
			frappe.set_route("query-report", "Sales Register");
		});
	},
});

