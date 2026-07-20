frappe.listview_settings["Warehouse"] = {
	add_fields: ["warehouse_name", "company", "stock_qty_snapshot", "stock_value_snapshot"],
	formatters: {
		stock_qty_snapshot(value) {
			return frappe.format(value || 0, { fieldtype: "Float" });
		},
		stock_value_snapshot(value) {
			return format_currency(value || 0);
		},
	},
};

