frappe.provide("frappe.treeview_settings");

const existing = frappe.treeview_settings["GL Account"] || {};
const existingFilters = Array.isArray(existing.filters) ? existing.filters : [];
const hasDisplayModeFilter = existingFilters.some((f) => f && f.fieldname === "display_mode");

frappe.treeview_settings["GL Account"] = Object.assign({}, existing, {
	get_tree_nodes: "omnexa_accounting.omnexa_accounting.doctype.gl_account.gl_account_tree.get_children",
	filters: hasDisplayModeFilter
		? existingFilters
		: existingFilters.concat([
				{
					fieldname: "display_mode",
					label: __("Display Mode"),
					fieldtype: "Select",
					options: ["Show All", "Standard Only", "Advanced Only"].join("\n"),
					default: "Show All",
				},
		  ]),
	// Show title only to hide internal document id/hash suffix in tree.
	get_label(node) {
		return __(node.title || node.label);
	},
});

