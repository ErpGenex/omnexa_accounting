frappe.provide("frappe.form.link_formatters");

function formatCodeName(code, name, fallback) {
	const c = (code || "").toString().trim();
	const n = (name || "").toString().trim();
	const f = (fallback || "").toString().trim();
	if (c && n) return `${c} - ${n}`;
	if (n) return n;
	if (c) return c;
	return f;
}

frappe.form.link_formatters.Item = function (value, doc) {
	const itemCode = doc?.item_code || value || "";
	const itemName = doc?.item_name || "";
	return formatCodeName(itemCode, itemName, value);
};

frappe.form.link_formatters.Customer = function (value, doc) {
	const customerCode = doc?.customer_code || "";
	const customerName = doc?.customer_name || value || "";
	return formatCodeName(customerCode, customerName, value);
};

frappe.form.link_formatters.Supplier = function (value, doc) {
	const supplierCode = doc?.supplier_code || "";
	const supplierName = doc?.supplier_name || value || "";
	return formatCodeName(supplierCode, supplierName, value);
};

frappe.form.link_formatters["GL Account"] = function (value, doc) {
	const accountNumber = doc?.account_number || "";
	const accountName = doc?.account_name || value || "";
	return formatCodeName(accountNumber, accountName, value);
};
