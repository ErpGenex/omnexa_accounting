frappe.query_reports["Dead Stock Report"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1 },
		{ fieldname: "days", label: __("No Movement Days"), fieldtype: "Int", default: 120 },
	],
};

