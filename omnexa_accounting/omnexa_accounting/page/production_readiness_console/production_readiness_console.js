frappe.pages["production-readiness-console"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Production Readiness Console"),
		single_column: true,
	});

	const $root = $(`
		<div class="production-readiness-console">
			<div class="mb-3 row g-2">
				<div class="col-md-4">
					<select class="form-select form-select-sm" data-field="company"></select>
				</div>
				<div class="col-md-4">
					<select class="form-select form-select-sm" data-field="branch">
						<option value="">${__("All Branches")}</option>
					</select>
				</div>
				<div class="col-md-4">
					<select class="form-select form-select-sm" data-field="activity">
						<option value="">${__("Auto from company")}</option>
						<option>General</option>
						<option>Construction</option>
						<option>Engineering Consulting</option>
						<option>Healthcare</option>
						<option>Education</option>
						<option>Manufacturing</option>
						<option>Agriculture</option>
						<option>Tourism</option>
						<option>Hotel Assets (إدارة أصول الفنادق)</option>
						<option>Trading</option>
						<option>Services</option>
						<option>Financial Services</option>
						<option>Statutory Audit</option>
					</select>
				</div>
			</div>

			<div class="mb-3 d-flex gap-2 flex-wrap align-items-center">
				<button class="btn btn-primary btn-sm" data-action="generate-coa">${__("Generate Professional COA")}</button>
				<button class="btn btn-outline-primary btn-sm" data-action="resync-coa-labels">${__("Resync COA Labels")}</button>
				<button class="btn btn-info btn-sm" data-action="seed-demo">${__("Seed Demo Data")}</button>
				<div class="form-check ms-1">
					<input class="form-check-input" type="checkbox" id="prc-include-tx" data-field="include_transactions" />
					<label class="form-check-label" for="prc-include-tx">${__("Include submitted transactions")}</label>
				</div>
				<button class="btn btn-warning btn-sm" data-action="reset-dry">${__("Reset Transactions (Dry Run)")}</button>
				<button class="btn btn-danger btn-sm" data-action="reset-exec">${__("Reset Transactions (Execute)")}</button>
				<button class="btn btn-secondary btn-sm" data-action="refresh-logs">${__("Refresh Logs")}</button>
			</div>

			<div class="alert alert-light mb-3" data-section="result">${__("No operation executed yet.")}</div>

			<div class="card">
				<div class="card-header"><b>${__("Latest Production Seed Logs")}</b></div>
				<div class="card-body p-0">
					<table class="table table-sm mb-0">
						<thead>
							<tr>
								<th>${__("When")}</th>
								<th>${__("Operation")}</th>
								<th>${__("Company")}</th>
								<th>${__("Branch")}</th>
								<th>${__("Activity")}</th>
								<th>${__("Dry Run")}</th>
								<th>${__("Status")}</th>
								<th>${__("By")}</th>
								<th>${__("Open")}</th>
							</tr>
						</thead>
						<tbody data-section="logs">
							<tr><td colspan="9" class="text-muted">${__("Loading...")}</td></tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>
	`);

	$(page.body).append($root);

	const getVal = (k) => String($root.find(`[data-field="${k}"]`).val() || "").trim();
	const company = () => getVal("company");
	const branch = () => getVal("branch");
	const activity = () => getVal("activity");
	const includeTransactions = () => ($root.find('[data-field="include_transactions"]').is(":checked") ? 1 : 0);

	const setResult = (msg, tone = "light") => {
		$root.find('[data-section="result"]').attr("class", `alert alert-${tone} mb-3`).html(msg);
	};

	const loadCompanies = async () => {
		const r = await frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Company",
				fields: ["name", "company_name"],
				limit_page_length: 200,
				order_by: "company_name asc",
			},
		});
		const rows = (r && r.message) || [];
		const $el = $root.find('[data-field="company"]');
		$el.empty();
		rows.forEach((x) => {
			$el.append(`<option value="${frappe.utils.escape_html(x.name)}">${frappe.utils.escape_html(x.company_name || x.name)}</option>`);
		});
	};

	const loadBranches = async () => {
		const c = company();
		const $el = $root.find('[data-field="branch"]');
		$el.empty().append(`<option value="">${__("All Branches")}</option>`);
		if (!c) return;
		const r = await frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Branch",
				fields: ["name", "branch_name"],
				filters: { company: c },
				limit_page_length: 500,
				order_by: "branch_name asc",
			},
		});
		const rows = (r && r.message) || [];
		rows.forEach((x) => {
			$el.append(`<option value="${frappe.utils.escape_html(x.name)}">${frappe.utils.escape_html(x.branch_name || x.name)}</option>`);
		});
	};

	const renderLogs = (rows) => {
		const html = (rows || []).map(
			(x) => `
			<tr>
				<td>${frappe.utils.escape_html(frappe.datetime.str_to_user((x.executed_on || "").slice(0, 10) || "") || "")}</td>
				<td>${frappe.utils.escape_html(x.operation || "")}</td>
				<td>${frappe.utils.escape_html(x.company || "")}</td>
				<td>${frappe.utils.escape_html(x.branch || "")}</td>
				<td>${frappe.utils.escape_html(x.activity || "")}</td>
				<td>${x.dry_run ? "Yes" : "No"}</td>
				<td>${frappe.utils.escape_html(x.status || "")}</td>
				<td>${frappe.utils.escape_html(x.executed_by || "")}</td>
				<td><button class="btn btn-xs btn-outline-primary" data-open="${frappe.utils.escape_html(x.name)}">${__("Open")}</button></td>
			</tr>`
		);
		$root
			.find('[data-section="logs"]')
			.html(html.length ? html.join("") : `<tr><td colspan="9" class="text-muted">${__("No logs yet.")}</td></tr>`);
	};

	const refreshLogs = async () => {
		const c = company();
		const filters = c ? { company: c } : {};
		const r = await frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Production Seed Log",
				fields: ["name", "operation", "company", "branch", "activity", "executed_by", "executed_on", "dry_run", "status"],
				filters,
				limit_page_length: 30,
				order_by: "creation desc",
			},
		});
		renderLogs((r && r.message) || []);
	};

	const runApi = async (method, args, label) => {
		try {
			const r = await frappe.call({ method, args, freeze: true, freeze_message: __("Executing {0}...", [label]) });
			const msg = (r && r.message) || {};
			setResult(
				`<b>${__("Operation")}:</b> ${frappe.utils.escape_html(label)}<br>` +
					`<b>${__("Status")}:</b> ${frappe.utils.escape_html(msg.ok ? "Success" : "Failed")}<br>` +
					`<b>${__("Log ID")}:</b> ${frappe.utils.escape_html(msg.log_id || "n/a")}`,
				msg.ok ? "success" : "danger"
			);
			await refreshLogs();
		} catch (e) {
			setResult(`${__("Execution failed.")} ${frappe.utils.escape_html((e && e.message) || "")}`, "danger");
		}
	};

	$root.on("change", '[data-field="company"]', async () => {
		await loadBranches();
		await refreshLogs();
	});
	$root.on("click", '[data-action="refresh-logs"]', async () => refreshLogs());

	$root.on("click", '[data-action="generate-coa"]', async () => {
		await runApi(
			"omnexa_accounting.utils.production_readiness.generate_professional_chart_of_accounts",
			{ company: company(), branch: branch() || null, activity: activity() || null },
			__("Generate Professional COA")
		);
	});

	$root.on("click", '[data-action="resync-coa-labels"]', async () => {
		await runApi(
			"omnexa_accounting.utils.production_readiness.resync_chart_of_accounts_labels",
			{ company: company(), branch: branch() || null, activity: activity() || null },
			__("Resync COA Labels")
		);
	});

	$root.on("click", '[data-action="seed-demo"]', async () => {
		await runApi(
			"omnexa_accounting.utils.production_readiness.seed_activity_demo_data",
			{
				company: company(),
				branch: branch() || null,
				activity: activity() || null,
				include_transactions: includeTransactions(),
			},
			__("Seed Demo Data")
		);
	});

	$root.on("click", '[data-action="reset-dry"]', async () => {
		await runApi(
			"omnexa_accounting.utils.production_readiness.reset_transactions",
			{ company: company(), branch: branch() || null, dry_run: 1 },
			__("Reset Transactions (Dry Run)")
		);
	});

	$root.on("click", '[data-action="reset-exec"]', async () => {
		frappe.confirm(
			__("This will delete transactions for selected scope. Continue?"),
			async () =>
				runApi(
					"omnexa_accounting.utils.production_readiness.reset_transactions",
					{ company: company(), branch: branch() || null, dry_run: 0 },
					__("Reset Transactions (Execute)")
				),
			() => null
		);
	});

	$root.on("click", "[data-open]", function () {
		const name = $(this).attr("data-open");
		if (name) frappe.set_route("Form", "Production Seed Log", name);
	});

	(async () => {
		await loadCompanies();
		await loadBranches();
		await refreshLogs();
	})();
};

