frappe.ui.form.on("Warehouse", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Warehouse Product Balances"), async () => {
			const r = await frappe.call({
				method: "omnexa_accounting.utils.warehouse_stock_metrics.get_warehouse_item_balances",
				args: {
					warehouse: frm.doc.name,
					company: frm.doc.company,
				},
			});
			const rows = r.message?.rows || [];
			if (!rows.length) {
				frappe.msgprint(__("No stock balances found for this warehouse."));
				return;
			}

			const tableRows = rows
				.map(
					(row) => `
					<tr>
						<td style="padding:6px 8px;border-bottom:1px solid #eee;">${frappe.utils.escape_html(row.item_code || row.item || "")}</td>
						<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;">${frappe.format(row.qty_balance || 0, { fieldtype: "Float" })}</td>
						<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;">${format_currency(row.value_balance || 0)}</td>
					</tr>
				`,
				)
				.join("");

			frappe.msgprint({
				title: __("Warehouse Product Balances"),
				wide: true,
				message: `
					<div style="max-height:420px;overflow:auto;">
						<table style="width:100%;border-collapse:collapse;">
							<thead>
								<tr>
									<th style="text-align:left;padding:8px;border-bottom:1px solid #ddd;">${__("Item")}</th>
									<th style="text-align:right;padding:8px;border-bottom:1px solid #ddd;">${__("Qty Balance")}</th>
									<th style="text-align:right;padding:8px;border-bottom:1px solid #ddd;">${__("Value Balance")}</th>
								</tr>
							</thead>
							<tbody>${tableRows}</tbody>
						</table>
					</div>
				`,
			});
		});
	},
});

