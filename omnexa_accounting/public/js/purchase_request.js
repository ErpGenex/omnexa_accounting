frappe.ui.form.on("Purchase Request", {
	refresh(frm) {
		if (!frm.doc || frm.doc.docstatus === 2) return;

		frm.add_custom_button(__("Compare Quotations"), () => {
			frappe.set_route("query-report", "Purchase Quotation Comparison", {
				company: frm.doc.company,
				branch: frm.doc.branch,
				purchase_request: frm.doc.name,
			});
		});

		frm.add_custom_button(__("Create PO from Best Quotations"), async () => {
			const flags = await frappe.call({
				method: "omnexa_core.omnexa_core.procurement.api.is_purchase_enterprise_enabled",
			});
			if (!flags?.message?.purchase_quotation_auto_po) {
				frappe.msgprint(__("Auto PO creation is disabled (feature flag)."));
				return;
			}
			const r = await frappe.call({
				method: "omnexa_core.omnexa_core.procurement.api.make_purchase_orders_from_best_quotations",
				args: { purchase_request: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating Purchase Orders..."),
			});
			const created = r?.message?.created || [];
			if (!created.length) {
				frappe.msgprint(__(r?.message?.skipped || "No Purchase Orders created."));
				return;
			}
			frappe.msgprint(__("Created Purchase Orders: {0}", [created.join(", ")]));
		});
	},
});

