frappe.listview_settings["Customer"] = {
	add_fields: ["customer_name", "status", "company", "balance_snapshot"],

	formatters: {
		balance_snapshot(value) {
			return format_currency(value || 0);
		},
	},
};

