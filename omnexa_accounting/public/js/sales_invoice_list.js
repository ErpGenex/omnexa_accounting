frappe.listview_settings["Sales Invoice"] = {
	onload(listview) {
		const params = new URLSearchParams(window.location.search);
		const route_opts = frappe.route_options || {};
		if (params.get("is_return") === "1" || frappe.utils.cint(route_opts.is_return) === 1) {
			listview.filter_area.add([["Sales Invoice", "is_return", "=", 1]]);
		}
	},
};
