frappe.ui.form.on("Purchase Receipt", {
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
		frm.set_query("purchase_order", () => {
			const filters = {};
			if (frm.doc.company) filters.company = frm.doc.company;
			if (frm.doc.branch) filters.branch = frm.doc.branch;
			return { filters };
		});
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
