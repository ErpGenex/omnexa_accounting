frappe.query_reports["Warehouse Transfer Report"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch" },
		{ fieldname: "from_warehouse", label: __("From Warehouse"), fieldtype: "Link", options: "Warehouse" },
		{ fieldname: "to_warehouse", label: __("To Warehouse"), fieldtype: "Link", options: "Warehouse" },
		{ fieldname: "item", label: __("Item"), fieldtype: "Link", options: "Item" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
	],
};

