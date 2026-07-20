frappe.query_reports["Bank Reconciliation Suggestions"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1 },
		{ fieldname: "bank_account", label: __("Bank Account"), fieldtype: "Link", options: "Bank Account", reqd: 1 },
		{ fieldname: "statement_date", label: __("Statement Date"), fieldtype: "Date" },
		{ fieldname: "tolerance_days", label: __("Tolerance Days"), fieldtype: "Int", default: 7 },
		{ fieldname: "limit", label: __("Limit"), fieldtype: "Int", default: 200 },
	],
};

