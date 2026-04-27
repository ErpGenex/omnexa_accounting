frappe.ui.form.on("Sales Invoice", {
	async onload(frm) {
		if (!frm.is_new()) {
			return;
		}
		await set_company_branch_defaults(frm);
	},

	async refresh(frm) {
		if (frm.is_new()) {
			if (!frm.doc.company || !frm.doc.branch) {
				await set_company_branch_defaults(frm);
			}
			return;
		}

		frm.add_custom_button(__("View Posting Journal Entry"), async () => {
			let je = frm.doc.posting_journal_entry;
			if (!je) {
				const r = await frappe.call({
					method: "omnexa_accounting.utils.ledger_tools.get_invoice_posting_journal_entry",
					args: {
						doctype: "Sales Invoice",
						docname: frm.doc.name,
						company: frm.doc.company,
						branch: frm.doc.branch,
					},
				});
				je = r.message;
			}
			if (je) {
				frappe.set_route("Form", "Journal Entry", je);
				return;
			}
			frappe.msgprint(__("No posting Journal Entry found for this invoice."));
		});

		frm.add_custom_button(__("Item Movements"), async () => {
			const first = (frm.doc.items || []).find((r) => r.item);
			if (!first?.item) {
				frappe.msgprint(__("No item rows found."));
				return;
			}
			frappe.route_options = {
				company: frm.doc.company,
				from_date: frm.doc.posting_date,
				to_date: frm.doc.posting_date,
				item: first.item,
			};
			frappe.set_route("query-report", "Stock Movement");
		});

		frm.add_custom_button(__("Create Shipment"), async () => {
			const r = await frappe.call({
				method: "omnexa_accounting.utils.shipment.create_shipment_from_invoice",
				args: {
					doctype: "Sales Invoice",
					docname: frm.doc.name,
					carrier: frm.doc.shipment_carrier || undefined,
				},
			});
			const shipment = r?.message?.shipment;
			if (!shipment) {
				return;
			}
			await frm.reload_doc();
			frappe.set_route("Form", "Shipment", shipment);
		});
	},

	setup(frm) {
		frm.set_query("project_reference", () => {
			const filters = {};
			if (frm.doc.company) filters.company = frm.doc.company;
			return { filters };
		});
		frm.set_query("project_task_reference", () => {
			const filters = {};
			if (frm.doc.company) filters.company = frm.doc.company;
			if (frm.doc.project_reference) filters.project = frm.doc.project_reference;
			return { filters };
		});

		frm.set_query("default_tax_rule", () => {
			const filters = {};
			if (frm.doc.company) filters.company = frm.doc.company;
			if (frm.doc.tax_category) filters.tax_category = frm.doc.tax_category;
			return { filters };
		});
		frm.set_query("shipment_carrier", () => {
			const filters = { is_active: 1 };
			if (frm.doc.company) filters.company = ["in", ["", frm.doc.company]];
			return { filters };
		});
		frm.set_query("shipment_record", () => ({
			filters: {
				invoice_doctype: "Sales Invoice",
				invoice_name: frm.doc.name || "",
			},
		}));
		frm.set_query("shipment_reference", () => {
			const filters = { invoice_doctype: "Sales Invoice" };
			if (frm.doc.name) filters.invoice_name = frm.doc.name;
			if (frm.doc.company) filters.company = frm.doc.company;
			return { filters };
		});

		frm.set_query("set_warehouse", () => {
			const filters = { disabled: 0 };
			if (frm.doc.company) filters.company = frm.doc.company;
			return { filters };
		});

		frm.set_query("customer", () => {
			const filters = { status: "Active" };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("item", "items", () => {
			const filters = {
				disabled: 0,
				is_sales_item: 1,
			};
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});
	},

	update_stock(frm) {
		frm.toggle_reqd("set_warehouse", !!frm.doc.update_stock);
	},
	payment_mode(frm) {
		if (frm.doc.payment_mode === "Cash") {
			frm.set_value("due_date", frm.doc.posting_date);
			frappe.show_alert({ message: __("Cash mode: Due Date = Posting Date"), indicator: "green" });
		} else if (frm.doc.payment_mode === "Installment") {
			frappe.show_alert({
				message: __("Installment mode: add at least 2 rows in Payment Schedule"),
				indicator: "orange",
			});
		}
	},
});

frappe.ui.form.on("Sales Invoice Item", {
	async item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item) {
			return;
		}
		const item_data = await frappe.db.get_value("Item", row.item, ["item_code", "item_name"]);
		const item_code = item_data?.message?.item_code || "";
		const item_name = item_data?.message?.item_name || "";
		if (item_code) {
			await frappe.model.set_value(cdt, cdn, "item_code", item_code);
		}
		if (item_name) {
			await frappe.model.set_value(cdt, cdn, "item_name", item_name);
		}
	},

	async item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}
		const matches = await frappe.db.get_list("Item", {
			fields: ["name", "item_code", "item_name"],
			filters: {
				item_code: row.item_code,
				disabled: 0,
				is_sales_item: 1,
			},
			limit: 2,
		});
		if (matches.length === 1) {
			await frappe.model.set_value(cdt, cdn, "item", matches[0].name);
			await frappe.model.set_value(cdt, cdn, "item_code", matches[0].item_code || "");
			await frappe.model.set_value(cdt, cdn, "item_name", matches[0].item_name || "");
		}
	},
});

async function set_company_branch_defaults(frm) {
	const defaultCompany = frappe.defaults.get_user_default("Company");
	const defaultBranch = frappe.defaults.get_user_default("Branch");
	if (defaultCompany && !frm.doc.company) {
		await frm.set_value("company", defaultCompany);
	}
	if (defaultBranch && !frm.doc.branch) {
		await frm.set_value("branch", defaultBranch);
	}
	if (!frm.doc.company || !frm.doc.branch) {
		const r = await frappe.call({
			method: "omnexa_accounting.permissions.get_logged_in_company_branch",
		});
		const company = r?.message?.company;
		const branch = r?.message?.branch;
		if (company && !frm.doc.company) {
			await frm.set_value("company", company);
		}
		if (branch && !frm.doc.branch) {
			await frm.set_value("branch", branch);
		}
	}
}
