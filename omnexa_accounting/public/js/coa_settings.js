frappe.ui.form.on("CoA Settings", {
	refresh(frm) {
		frm.set_df_property(
			"default_consolidation_view",
			"description",
			__("If enabled, financial reports open in consolidation grouping by default."),
		);
		frm.set_df_property(
			"manual_number_override_roles",
			"description",
			__("Roles allowed to manually override account numbering (one role per line)."),
		);
	},
});
