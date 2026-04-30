frappe.query_reports["Stock Aging Report"] = {
	filters: [{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1 }],
};

