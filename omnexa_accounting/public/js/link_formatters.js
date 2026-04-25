frappe.provide("frappe.form.link_formatters");

frappe.form.link_formatters.Item = function (value, doc) {
	const itemCode = doc?.item_code || value || "";
	const itemName = doc?.item_name || "";

	if (itemCode && itemName) {
		return `${itemCode} - ${itemName}`;
	}

	return itemCode || itemName || value;
};

frappe.form.link_formatters.Customer = function (value, doc) {
	const customerCode = doc?.customer_code || "";
	const customerName = doc?.customer_name || value || "";

	if (customerCode && customerName) {
		return `${customerCode} - ${customerName}`;
	}

	return customerName;
};

frappe.form.link_formatters.Supplier = function (value, doc) {
	const supplierCode = doc?.supplier_code || "";
	const supplierName = doc?.supplier_name || value || "";

	if (supplierCode && supplierName) {
		return `${supplierCode} - ${supplierName}`;
	}

	return supplierName;
};

frappe.form.link_formatters["GL Account"] = function (value, doc) {
	const accountNumber = doc?.account_number || "";
	const accountName = doc?.account_name || value || "";

	if (accountNumber && accountName) {
		return `${accountName} - ${accountNumber}`;
	}

	return accountNumber || accountName || value;
};
