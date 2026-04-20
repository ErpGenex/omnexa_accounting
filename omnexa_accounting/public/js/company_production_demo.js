// Copyright (c) 2026, Omnexa and contributors
// License: MIT. See license.txt

frappe.ui.form.on("Company", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		if (!frappe.user.has_role("System Manager")) {
			return;
		}

		frm.set_query("production_demo_branch", () => ({
			filters: { company: frm.doc.name },
		}));

		if (frm.__omnexa_production_demo_buttons_added) {
			return;
		}
		frm.__omnexa_production_demo_buttons_added = true;

		const company = frm.doc.name;
		const branch = () => {
			const v = (frm.doc.production_demo_branch || "").trim();
			return v || null;
		};
		const activity = () => {
			const v = (frm.doc.production_demo_activity || frm.doc.industry_sector || "").trim();
			return v || null;
		};

		const run = async (method, args, freeze_message) => {
			try {
				const r = await frappe.call({
					method,
					args,
					freeze: true,
					freeze_message,
				});
				const out = r.message || {};
				frappe.show_alert({
					indicator: out.ok ? "green" : "orange",
					message: `${freeze_message}: ${out.log_id || __("OK")}`,
				});
			} catch (e) {
				frappe.msgprint({
					title: __("Error"),
					message: e.message || String(e),
					indicator: "red",
				});
			}
		};

		const group = __("Production demo");

		frm.add_custom_button(
			__("Generate professional COA"),
			() =>
				run(
					"omnexa_accounting.utils.production_readiness.generate_professional_chart_of_accounts",
					{ company, branch: branch(), activity: activity() },
					__("Generate professional COA"),
				),
			group,
		);

		frm.add_custom_button(
			__("Resync COA labels (names from template)"),
			() =>
				run(
					"omnexa_accounting.utils.production_readiness.resync_chart_of_accounts_labels",
					{ company, branch: branch(), activity: activity() },
					__("Resync COA labels"),
				),
			group,
		);

		frm.add_custom_button(
			__("Seed demo data (masters)"),
			() =>
				run(
					"omnexa_accounting.utils.production_readiness.seed_activity_demo_data",
					{
						company,
						branch: branch(),
						activity: activity(),
						include_transactions: 0,
					},
					__("Seed demo data"),
				),
			group,
		);

		frm.add_custom_button(
			__("Seed demo data + transactions"),
			() =>
				run(
					"omnexa_accounting.utils.production_readiness.seed_activity_demo_data",
					{
						company,
						branch: branch(),
						activity: activity(),
						include_transactions: 1,
					},
					__("Seed demo data + transactions"),
				),
			group,
		);

		frm.add_custom_button(
			__("Reset transactions (dry run)"),
			() =>
				run(
					"omnexa_accounting.utils.production_readiness.reset_transactions",
					{ company, branch: branch(), dry_run: 1 },
					__("Reset transactions (dry run)"),
				),
			group,
		);

		frm.add_custom_button(
			__("Reset transactions (execute)"),
			() => {
				frappe.confirm(
					__(
						"This will cancel and delete matched transactions for this company (and branch if set). Continue?",
					),
					() =>
						run(
							"omnexa_accounting.utils.production_readiness.reset_transactions",
							{ company, branch: branch(), dry_run: 0 },
							__("Reset transactions (execute)"),
						),
					() => {},
				);
			},
			group,
		);
	},
});
