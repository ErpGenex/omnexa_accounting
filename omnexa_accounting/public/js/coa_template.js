frappe.ui.form.on("COA Template", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Seed from curated dataset"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Seed COA Template"),
				fields: [
					{
						fieldname: "template_name",
						label: __("Template Name"),
						fieldtype: "Data",
						reqd: 1,
						default: frm.doc.template_name,
					},
					{
						fieldname: "industry_tag",
						label: __("Industry Tag"),
						fieldtype: "Select",
						options: "All\nTrading\nManufacturing\nHealthcare\nAgriculture\nProjects\nService",
						reqd: 1,
						default: frm.doc.industry_tag || "All",
					},
				],
				primary_action_label: __("Seed"),
				primary_action(values) {
					frappe.call({
						method: "omnexa_accounting.utils.coa_template_service.seed_coa_template",
						args: values,
						callback: () => frm.reload_doc(),
					});
					d.hide();
				},
			});
			d.show();
		});

		frm.add_custom_button(__("Export CSV"), () => {
			frappe.call({
				method: "omnexa_accounting.utils.coa_template_service.export_coa_template_csv",
				args: { template: frm.doc.name },
				callback(r) {
					const csv_text = r.message || "";
					const d = new frappe.ui.Dialog({
						title: __("COA Template CSV"),
						size: "large",
						fields: [
							{
								fieldname: "csv_text",
								label: __("CSV"),
								fieldtype: "Text",
								read_only: 1,
								default: csv_text,
							},
						],
						primary_action_label: __("Close"),
						primary_action() {
							d.hide();
						},
					});
					d.show();
				},
			});
		});

		frm.add_custom_button(__("Import CSV"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Import COA Template CSV"),
				size: "large",
				fields: [
					{
						fieldname: "replace",
						label: __("Replace existing lines"),
						fieldtype: "Check",
						default: 1,
					},
					{
						fieldname: "csv_text",
						label: __("CSV"),
						fieldtype: "Text",
						reqd: 1,
					},
				],
				primary_action_label: __("Import"),
				primary_action(values) {
					frappe.call({
						method: "omnexa_accounting.utils.coa_template_service.import_coa_template_csv",
						args: {
							template: frm.doc.name,
							csv_text: values.csv_text,
							replace: values.replace ? 1 : 0,
						},
						callback: () => frm.reload_doc(),
					});
					d.hide();
				},
			});
			d.show();
		});

		frm.add_custom_button(__("Apply to Company"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Apply COA to Company"),
				fields: [
					{
						fieldname: "company",
						label: __("Company"),
						fieldtype: "Link",
						options: "Company",
						reqd: 1,
					},
					{
						fieldname: "branch",
						label: __("Branch (optional)"),
						fieldtype: "Link",
						options: "Branch",
					},
					{
						fieldname: "lang",
						label: __("Account name language"),
						fieldtype: "Select",
						options: "en\nar",
						default: frappe.boot.lang && frappe.boot.lang.startsWith("ar") ? "ar" : "en",
					},
					{
						fieldname: "overwrite_names",
						label: __("Overwrite existing account names"),
						fieldtype: "Check",
						default: 0,
					},
				],
				primary_action_label: __("Apply"),
				primary_action(values) {
					frappe.call({
						method: "omnexa_accounting.utils.coa_template_service.apply_coa_template_to_company",
						args: {
							template: frm.doc.name,
							company: values.company,
							branch: values.branch || null,
							lang: values.lang || null,
							overwrite_names: values.overwrite_names ? 1 : 0,
						},
						callback(r) {
							const msg = r.message || {};
							frappe.msgprint(
								__("COA applied. Created: {0}, Updated: {1}", [msg.created || 0, msg.updated || 0])
							);
						},
					});
					d.hide();
				},
			});
			d.show();
		});

		frm.add_custom_button(__("Reset COA (Danger)"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Reset COA (Danger)"),
				fields: [
					{
						fieldname: "company",
						label: __("Company"),
						fieldtype: "Link",
						options: "Company",
						reqd: 1,
					},
					{
						fieldname: "branch",
						label: __("Branch (optional)"),
						fieldtype: "Link",
						options: "Branch",
					},
					{
						fieldname: "confirm_text",
						label: __("Type RESET COA to confirm"),
						fieldtype: "Data",
						reqd: 1,
					},
				],
				primary_action_label: __("Reset"),
				primary_action(values) {
					frappe.call({
						method: "omnexa_accounting.utils.coa_reset_service.reset_coa",
						args: {
							company: values.company,
							branch: values.branch || null,
							confirm_text: values.confirm_text,
						},
						callback(r) {
							const msg = r.message || {};
							frappe.msgprint(
								__("Reset completed. Backup File: {0}, Audit Log: {1}", [msg.backup_file, msg.audit_log])
							);
						},
					});
					d.hide();
				},
			});
			d.show();
		});
	},
});

