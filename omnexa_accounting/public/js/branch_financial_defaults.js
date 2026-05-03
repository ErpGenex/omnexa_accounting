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

		/** Full business demo: aligned workspace seed (SO→DN→SI, PO→PR→PI, stock, JE) + enterprise daily volume. */
		const launchIntegratedDemo = async (mode) => {
			const values = await frappe.prompt(
				[
					{
						fieldname: "include_workspace_seed",
						fieldtype: "Check",
						label: __("Include full document chains (orders, receipts, workspace demo)"),
						default: 1,
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
				mode === "6m" ? __("6-Month integrated demo plan") : __("12-Month integrated demo plan"),
				__("Queue job")
			);

			if (!values) return;

			await frappe.call({
				method: "omnexa_accounting.utils.production_readiness.enqueue_integrated_demo_simulation",
				args: {
					branch: frm.doc.name,
					mode,
					include_workspace_seed: values.include_workspace_seed ? 1 : 0,
					daily_purchase_invoices: values.daily_purchase_invoices,
					daily_sales_invoices: values.daily_sales_invoices,
					employees: values.employees,
					customers: values.customers,
					suppliers: values.suppliers,
					items: values.items,
				},
				freeze: true,
				freeze_message: __("Queueing full business simulation (workspace + transactional volume)..."),
				callback: (r) => {
					if (r.exc) return;
					const m = r.message || {};
					frappe.msgprint(
						__(
							"Integrated demo queued (document chains when enabled + daily invoices, stock, payroll path). Job: {0}<br>Open Production Seed Log for summary when the job completes.",
							[m.job_id || "n/a"]
						)
					);
				},
			});
		};

		frm.add_custom_button(__("Seed 6-Month Full Business Simulation"), async () => {
			await launchIntegratedDemo("6m");
		});

		frm.add_custom_button(__("Seed 12-Month Full Business Simulation"), async () => {
			await launchIntegratedDemo("12m");
		});
	},
});
