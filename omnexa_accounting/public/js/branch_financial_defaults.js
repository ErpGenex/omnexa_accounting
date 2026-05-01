// Copyright (c) 2026, Omnexa and contributors
// License: MIT. See license.txt

frappe.ui.form.on("Branch", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		const company = frm.doc.company;
		if (!company) {
			return;
		}
		const branchGlFields = [
			"branch_default_petty_cash_gl",
			"branch_default_bank_gl",
			"branch_default_receivable_gl",
			"branch_default_trade_payable_gl",
		];
		branchGlFields.forEach((fieldname) => {
			frm.set_query(fieldname, () => ({
				filters: { company },
			}));
		});

		if (frappe.session.user !== "Administrator") {
			return;
		}

		const launchSimulationSeed = async (defaultMonths) => {
			const values = await frappe.prompt(
				[
					{
						fieldname: "months",
						fieldtype: "Int",
						label: __("Months"),
						default: defaultMonths,
						reqd: 1,
					},
					{
						fieldname: "daily_purchase_invoices",
						fieldtype: "Int",
						label: __("Daily Purchase Invoices"),
						default: 10,
						reqd: 1,
					},
					{
						fieldname: "daily_sales_invoices",
						fieldtype: "Int",
						label: __("Daily Sales Invoices"),
						default: 10,
						reqd: 1,
					},
					{
						fieldname: "employees",
						fieldtype: "Int",
						label: __("Employees"),
						default: 5,
						reqd: 1,
					},
					{
						fieldname: "customers",
						fieldtype: "Int",
						label: __("Customers"),
						default: 5,
						reqd: 1,
					},
					{
						fieldname: "suppliers",
						fieldtype: "Int",
						label: __("Suppliers"),
						default: 5,
						reqd: 1,
					},
					{
						fieldname: "items",
						fieldtype: "Int",
						label: __("Items"),
						default: 10,
						reqd: 1,
					},
				],
				__("Simulation Plan"),
				__("Start")
			);

			if (!values) return;

			await frappe.call({
				method: "omnexa_accounting.utils.production_readiness.start_branch_enterprise_simulation_seed",
				args: {
					branch: frm.doc.name,
					months: values.months,
					daily_purchase_invoices: values.daily_purchase_invoices,
					daily_sales_invoices: values.daily_sales_invoices,
					employees: values.employees,
					customers: values.customers,
					suppliers: values.suppliers,
					items: values.items,
				},
				freeze: true,
				freeze_message: __("Queueing enterprise simulation seed..."),
				callback: (r) => {
					if (r.exc) return;
					const m = r.message || {};
					frappe.msgprint(
						__(
							"Simulation queued. Job: {0}<br>Open Production Seed Log later for summary.",
							[m.job_id || "n/a"]
						)
					);
				},
			});
		};

		frm.add_custom_button(__("Seed 6-Month Enterprise Simulation"), async () => {
			await launchSimulationSeed(6);
		});

		frm.add_custom_button(__("Seed 12-Month Enterprise Simulation"), async () => {
			await launchSimulationSeed(12);
		});
	},
});
