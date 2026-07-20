frappe.ui.form.on("Payment Entry", {
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
		frm.set_query("party", () => {
			const filters = {};
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
