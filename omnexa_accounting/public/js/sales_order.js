frappe.ui.form.on("Sales Order", {
	async onload(frm) {
		if (!frm.is_new()) {
			return;
		}
		await set_company_branch_defaults(frm);
	},

	async refresh(frm) {
		if (!frm.is_new()) {
			return;
		}
		if (!frm.doc.company || !frm.doc.branch) {
			await set_company_branch_defaults(frm);
		}
	},

	setup(frm) {
		frm.set_query("customer", () => {
			const filters = { status: "Active" };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});
		frm.set_query("delivery_terms", () => ({
			query: "omnexa_accounting.permissions.delivery_terms_query",
		}));

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

frappe.ui.form.on("Sales Order Item", {
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

		if (row.item) {
			const linked_code = await frappe.db.get_value("Item", row.item, "item_code");
			if (linked_code?.message?.item_code === row.item_code) {
				return;
			}
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
			await frappe.model.set_value(cdt, cdn, "item_name", matches[0].item_name || "");
			await frappe.model.set_value(cdt, cdn, "item_code", matches[0].item_code || "");
		}
	},
});
