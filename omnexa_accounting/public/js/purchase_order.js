frappe.ui.form.on("Purchase Order", {
	async onload(frm) {
		if (!frm.is_new()) return;
		await set_company_branch_defaults(frm);
	},
	async refresh(frm) {
		if (!frm.is_new()) return;
		if (!frm.doc.company || !frm.doc.branch) {
			await set_company_branch_defaults(frm);
		}
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

frappe.ui.form.on("Purchase Order Item", {
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
		await maybe_apply_contract_rate(frm, cdt, cdn);
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
		await maybe_apply_contract_rate(frm, cdt, cdn);
	},
	async qty(frm, cdt, cdn) {
		await maybe_apply_contract_rate(frm, cdt, cdn);
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

async function maybe_apply_contract_rate(frm, cdt, cdn) {
	try {
		if (!frm || frm.is_new() === false) {
			// still allow on new+existing, but avoid heavy calls on every refresh
		}
		const row = locals[cdt][cdn];
		if (!row) return;
		if (!frm.doc.company || !frm.doc.supplier) return;
		if (!row.item && !row.item_code) return;
		if (row.rate && row.rate > 0) return; // don't override user-entered rate

		const r = await frappe.call({
			method: "omnexa_core.omnexa_core.procurement.api.get_best_purchase_rate",
			args: {
				company: frm.doc.company,
				supplier: frm.doc.supplier,
				item: row.item,
				item_code: row.item_code,
				qty: row.qty || 1,
				posting_date: frm.doc.posting_date,
				currency: frm.doc.currency,
			},
		});
		const best = r?.message;
		if (!best || !best.rate) return;

		await frappe.model.set_value(cdt, cdn, "rate", best.rate);
		if (best.discount_percentage && frappe.meta.has_field(cdt, "discount_percentage")) {
			await frappe.model.set_value(cdt, cdn, "discount_percentage", best.discount_percentage);
		}
	} catch (e) {
		// best-effort only
	}
}
