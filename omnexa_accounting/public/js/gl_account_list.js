frappe.listview_settings["GL Account"] = {
	add_fields: ["account_name", "account_number", "balance_snapshot", "company", "branch"],

	formatters: {
		tree_label(value, _df, doc) {
			// Keep title column as clean account name only.
			return doc.account_name || value;
		},
		balance_snapshot(value) {
			return format_currency(value || 0);
		},
	},
};

