frappe.ui.form.on("GL Account", {
	setup(frm) {
		frm.set_query("parent_account", () => ({
			filters: {
				company: frm.doc.company || "",
				is_group: 1,
			},
		}));
	},
	account_class(frm) {
		apply_class_defaults(frm);
	},
	posting_type(frm) {
		apply_posting_defaults(frm);
	},
	refresh(frm) {
		apply_dynamic_visibility(frm);
		if (frm.is_new()) return;

		frm.add_custom_button(__("Open General Ledger"), () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Company is required."));
				return;
			}
			frappe.route_options = {
				company: frm.doc.company,
				account: frm.doc.name,
				branch: frm.doc.branch || undefined,
			};
			frappe.set_route("query-report", "General Ledger");
		});

		frm.add_custom_button(__("Show Balance"), async () => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Company is required."));
				return;
			}
			const r = await frappe.call({
				method: "omnexa_accounting.utils.ledger_tools.get_gl_account_balance",
				args: {
					company: frm.doc.company,
					account: frm.doc.name,
					branch: frm.doc.branch || null,
				},
			});
			const out = r.message || {};
			if (!out.ok) return;
			frappe.msgprint(
				__(
					"Debit: {0}<br>Credit: {1}<br><b>Balance:</b> {2}",
					[out.debit || 0, out.credit || 0, out.balance || 0],
				),
			);
		});
	},
});

function apply_posting_defaults(frm) {
	const postingType = (frm.doc.posting_type || "").trim();
	if (postingType === "Header") {
		frm.set_value("is_group", 1);
		frm.set_value("allow_direct_posting", 0);
	} else if (postingType) {
		frm.set_value("is_group", 0);
	}
	apply_dynamic_visibility(frm);
}

function apply_class_defaults(frm) {
	const cls = (frm.doc.account_class || "").trim();
	if (!cls) return;
	if (!frm.doc.account_type || frm.doc.account_type === "Income") {
		frm.set_value("account_type", cls);
	}
	if (!frm.doc.account_number && !frm.doc.manual_number_override) {
		frappe.show_alert({
			message: __("Account number will be auto-generated from class mask on save."),
			indicator: "blue",
		});
	}
	if ((frm.doc.is_bank_account || frm.doc.is_cash_account) && !frm.doc.cash_flow_section) {
		frm.set_value("cash_flow_section", "Operating Activities");
	}
}

function apply_dynamic_visibility(frm) {
	const postingType = (frm.doc.posting_type || "").trim();
	const isHeader = postingType === "Header" || Number(frm.doc.is_group || 0) === 1;
	frm.toggle_enable("allow_direct_posting", !isHeader);
	frm.set_df_property(
		"allow_direct_posting",
		"description",
		__("Allow direct manual journal posting to this account."),
	);
	frm.set_df_property(
		"requires_cost_center",
		"description",
		__("If enabled, each posting row must include a Cost Center."),
	);
	frm.set_df_property(
		"requires_project",
		"description",
		__("If enabled, each posting row must include a Project."),
	);
	frm.set_df_property(
		"group_reporting_tag",
		"description",
		__("Tag used for group and consolidation reporting packs."),
	);
	frm.set_df_property(
		"working_capital_bucket",
		"description",
		__("Mapping used in indirect cash flow and working-capital analytics."),
	);
}

