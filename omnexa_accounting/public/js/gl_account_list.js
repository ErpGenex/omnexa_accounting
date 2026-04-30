frappe.listview_settings["GL Account"] = {
	hide_name_column: true,
	add_fields: ["account_name", "account_number", "balance_snapshot", "company", "branch"],

	formatters: {
		account_label(value, _df, doc) {
			const accountName = doc.account_name || "";
			return accountName || value || "";
		},
		tree_label(value, _df, doc) {
			// Keep title column as clean account name only.
			return doc.account_name || value || "";
		},
		balance_snapshot(value) {
			return format_currency(value || 0);
		},
	},
};

