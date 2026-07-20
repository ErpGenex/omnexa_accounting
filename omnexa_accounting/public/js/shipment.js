frappe.ui.form.on("Shipment", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Open Invoice"), () => {
			if (!frm.doc.invoice_doctype || !frm.doc.invoice_name) {
				frappe.msgprint(__("Invoice link is missing."));
				return;
			}
			frappe.set_route("Form", frm.doc.invoice_doctype, frm.doc.invoice_name);
		});
		frm.add_custom_button(__("Update Tracking"), async () => {
			const values = await frappe.prompt(
				[
					{
						fieldname: "tracking_number",
						fieldtype: "Data",
						label: __("Tracking Number"),
						reqd: 1,
						default: frm.doc.tracking_number || "",
					},
				],
				() => {},
				__("Update Tracking"),
				__("Save")
			);
			if (!values?.tracking_number) return;
			await frappe.call({
				method: "omnexa_accounting.utils.shipment.update_shipment_tracking",
				args: {
					shipment: frm.doc.name,
					tracking_number: values.tracking_number,
				},
			});
			await frm.reload_doc();
		});
	},
});

