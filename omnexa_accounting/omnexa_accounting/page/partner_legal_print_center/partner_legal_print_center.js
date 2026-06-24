frappe.pages["partner-legal-print-center"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "مركز طباعة المستندات القانونية للشركاء",
		single_column: true,
	});

	const $root = $(`
		<div class="partner-legal-print-center" dir="rtl">
			<div class="alert alert-info mb-3">
				أضف الشركاء ونسب الملكية لأي شركة، ثم اطبع جميع المستندات القانونية
				(الميزانية العمومية، قائمة الدخل، كشوف المديونية، والتقرير النهائي) في ملف PDF واحد.
			</div>
			<div class="row g-2 mb-3">
				<div class="col-md-4">
					<label class="form-label small text-muted">الشركة</label>
					<select class="form-select form-select-sm" data-field="company"></select>
				</div>
				<div class="col-md-3">
					<label class="form-label small text-muted">من تاريخ</label>
					<input type="date" class="form-control form-control-sm" data-field="from_date" />
				</div>
				<div class="col-md-3">
					<label class="form-label small text-muted">إلى تاريخ</label>
					<input type="date" class="form-control form-control-sm" data-field="to_date" />
				</div>
				<div class="col-md-2">
					<label class="form-label small text-muted">الفرع</label>
					<select class="form-select form-select-sm" data-field="branch">
						<option value="">جميع الفروع</option>
					</select>
				</div>
			</div>
			<div class="d-flex gap-2 flex-wrap mb-3">
				<button class="btn btn-primary btn-sm" data-action="preview">معاينة الحزمة</button>
				<button class="btn btn-success btn-sm" data-action="print-all">طباعة كل المستندات القانونية (PDF)</button>
				<button class="btn btn-outline-secondary btn-sm" data-action="open-setup">إعداد الشركاء القانوني</button>
			</div>
			<div data-section="summary" class="mb-3"></div>
			<div class="card">
				<div class="card-header"><b>المستندات ضمن الحزمة</b></div>
				<div class="card-body p-0">
					<table class="table table-sm mb-0">
						<thead>
							<tr>
								<th>م</th>
								<th>اسم المستند</th>
								<th>عدد الصفوف</th>
								<th>الحالة</th>
							</tr>
						</thead>
						<tbody data-section="reports">
							<tr><td colspan="4" class="text-muted">اضغط «معاينة الحزمة» لعرض المستندات.</td></tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>
	`);

	$(page.body).append($root);

	const val = (k) => String($root.find(`[data-field="${k}"]`).val() || "").trim();

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
		const $sel = $root.find('[data-field="company"]').empty();
		(r.message || []).forEach((c) => {
			$sel.append(`<option value="${c.name}">${frappe.utils.escape_html(c.company_name || c.name)}</option>`);
		});
		if ($sel.children().length) {
			$sel.val($sel.children().first().val());
			await loadSetupDefaults();
		}
	};

	const loadBranches = async (company) => {
		const $sel = $root.find('[data-field="branch"]').empty().append(`<option value="">جميع الفروع</option>`);
		if (!company) return;
		const r = await frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Branch",
				filters: { company },
				fields: ["name"],
				limit_page_length: 100,
			},
		});
		(r.message || []).forEach((b) => $sel.append(`<option value="${b.name}">${b.name}</option>`));
	};

	const loadSetupDefaults = async () => {
		const company = val("company");
		if (!company) return;
		await loadBranches(company);
		const r = await frappe.call({
			method: "omnexa_accounting.omnexa_accounting.doctype.company_partner_legal_setup.company_partner_legal_setup.get_setup_for_company",
			args: { company },
		});
		const data = r.message || {};
		if (!data.found) {
			$root.find('[data-section="summary"]').html(
				`<div class="alert alert-warning mb-0">لا يوجد إعداد قانوني للشركاء. أنشئ «Company Partner Legal Setup» لهذه الشركة.</div>`
			);
			return;
		}
		if (data.default_from_date) $root.find('[data-field="from_date"]').val(data.default_from_date);
		if (data.default_to_date) $root.find('[data-field="to_date"]').val(data.default_to_date);
		if (data.branch) $root.find('[data-field="branch"]').val(data.branch);
		const partners = (data.partners || [])
			.map(
				(p) =>
					`${frappe.utils.escape_html(p.partner_name_ar || p.partner_name)} (${p.ownership_percent}%)` +
					(p.is_funding_partner ? " — ممول" : "")
			)
			.join(" · ");
		$root.find('[data-section="summary"]').html(
			`<div class="alert alert-light mb-0"><b>الشركاء:</b> ${partners || "—"}</div>`
		);
	};

	const renderPreview = (data) => {
		if (!data.ok) {
			frappe.msgprint({ message: data.error || "فشلت المعاينة", indicator: "red" });
			return;
		}
		const cert = data.certificate || {};
		$root.find('[data-section="summary"]').html(`
			<div class="alert alert-light mb-0">
				<b>الشركة:</b> ${frappe.utils.escape_html(data.company_display || data.company)}
				&nbsp;|&nbsp; <b>الشريك المدين:</b> ${frappe.utils.escape_html(cert.debtor_partner || "—")}
				&nbsp;|&nbsp; <b>الشريك الممول:</b> ${frappe.utils.escape_html(cert.funding_partner || "—")}
				&nbsp;|&nbsp; <b>المديونية المستحقة:</b> ${format_currency(cert.final_amount_due || 0)}
				&nbsp;|&nbsp; <b>عدد المستندات:</b> ${data.document_count || "—"}
			</div>
		`);
		const rows = (data.reports || [])
			.map((r) => {
				const status = r.ok
					? `<span class="text-success">جاهز</span>`
					: `<span class="text-danger">${frappe.utils.escape_html(r.error || "خطأ")}</span>`;
				return `<tr>
					<td>${r.doc_no || "—"}</td>
					<td>${frappe.utils.escape_html(r.title_ar || "")}</td>
					<td>${r.row_count != null ? r.row_count : "—"}</td>
					<td>${status}</td>
				</tr>`;
			})
			.join("");
		$root.find('[data-section="reports"]').html(rows || `<tr><td colspan="4">لا توجد مستندات</td></tr>`);
	};

	const preview = async () => {
		const company = val("company");
		if (!company || !val("from_date") || !val("to_date")) {
			frappe.msgprint("الشركة وتاريخ البداية والنهاية مطلوبة.");
			return;
		}
		frappe.dom.freeze("جاري تحميل المعاينة...");
		try {
			const r = await frappe.call({
				method: "omnexa_accounting.utils.partner_legal_batch_print.get_partner_legal_print_preview",
				args: {
					company,
					from_date: val("from_date"),
					to_date: val("to_date"),
					branch: val("branch") || null,
				},
			});
			renderPreview(r.message || {});
		} finally {
			frappe.dom.unfreeze();
		}
	};

	const printAll = () => {
		const company = val("company");
		if (!company || !val("from_date") || !val("to_date")) {
			frappe.msgprint("الشركة وتاريخ البداية والنهاية مطلوبة.");
			return;
		}
		const qs = new URLSearchParams({
			company,
			from_date: val("from_date"),
			to_date: val("to_date"),
		});
		const branch = val("branch");
		if (branch) qs.set("branch", branch);
		window.open(
			"/api/method/omnexa_accounting.utils.partner_legal_batch_print.download_partner_legal_package?" +
				qs.toString(),
			"_blank"
		);
	};

	$root.on("change", '[data-field="company"]', () => loadSetupDefaults());
	$root.on("click", '[data-action="preview"]', () => preview());
	$root.on("click", '[data-action="print-all"]', () => printAll());
	$root.on("click", '[data-action="open-setup"]', () => {
		const company = val("company");
		if (!company) return frappe.msgprint("اختر الشركة أولاً.");
		frappe.set_route("Form", "Company Partner Legal Setup", company);
	});

	loadCompanies();
};
