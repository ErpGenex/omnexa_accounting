frappe.ui.form.on("Purchase Invoice", {
	async onload(frm) {
		if (!frm.is_new()) return;
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
						doctype: "Purchase Invoice",
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
	},
	setup(frm) {
		frm.set_query("supplier", () => {
			const filters = { status: "Active" };
			if (frm.doc.company) filters.company = frm.doc.company;
			return { filters };
		});
		frm.set_query("item", "items", () => {
			const filters = { disabled: 0, is_purchase_item: 1 };
			if (frm.doc.company) filters.company = frm.doc.company;
			return { filters };
		});
	},
});

frappe.ui.form.on("Purchase Invoice Item", {
	async item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item) return;
		const itemData = await frappe.db.get_value("Item", row.item, ["item_code", "item_name"]);
		if (itemData?.message?.item_code) {
			await frappe.model.set_value(cdt, cdn, "item_code", itemData.message.item_code);
		}
		if (itemData?.message?.item_name) {
			await frappe.model.set_value(cdt, cdn, "item_name", itemData.message.item_name);
		}
	},
	async item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) return;
		const matches = await frappe.db.get_list("Item", {
			fields: ["name", "item_code", "item_name"],
			filters: { item_code: row.item_code, disabled: 0, is_purchase_item: 1 },
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
	if (defaultCompany && !frm.doc.company) await frm.set_value("company", defaultCompany);
	if (defaultBranch && !frm.doc.branch) await frm.set_value("branch", defaultBranch);
	if (!frm.doc.company || !frm.doc.branch) {
		const r = await frappe.call({
			method: "omnexa_accounting.permissions.get_logged_in_company_branch",
		});
		if (r?.message?.company && !frm.doc.company) await frm.set_value("company", r.message.company);
		if (r?.message?.branch && !frm.doc.branch) await frm.set_value("branch", r.message.branch);
	}
}
