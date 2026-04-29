(() => {
	function getDefaultCompany() {
		return (
			frappe.defaults.get_user_default("company") ||
			frappe.defaults.get_user_default("Company") ||
			(frappe.boot?.user?.defaults?.company || "")
		);
	}

	function getDefaultBranch() {
		return (
			frappe.defaults.get_user_default("branch") ||
			frappe.defaults.get_user_default("Branch") ||
			(frappe.boot?.user?.defaults?.branch || "")
		);
	}

	function applyDefaultsToCurrentReport() {
		const route = frappe.get_route() || [];
		if (route[0] !== "query-report") return;
		const qr = frappe.query_report;
		if (!qr || !Array.isArray(qr.filters)) return;

		const today = frappe.datetime.get_today();
		const company = getDefaultCompany();
		const branch = getDefaultBranch();

		const byName = {};
		(qr.filters || []).forEach((f) => {
			if (f?.df?.fieldname) byName[f.df.fieldname] = f;
		});

		const setIfEmpty = (fieldname, value) => {
			if (!value || !byName[fieldname]) return;
			const current = byName[fieldname].get_value?.();
			if (!current) {
				qr.set_filter_value(fieldname, value);
			}
		};

		const setDateIfFromToFilter = () => {
			(qr.filters || []).forEach((f) => {
				const df = f?.df || {};
				if (df.fieldtype !== "Date") return;

				const fieldname = (df.fieldname || "").toLowerCase();
				const label = (df.label || "").toLowerCase();
				const isFrom = fieldname.includes("from") || label.includes("from");
				const isTo = fieldname.includes("to") || label.includes("to");

				if (!isFrom && !isTo) return;
				const current = f.get_value?.();
				if (!current) {
					qr.set_filter_value(df.fieldname, today);
				}
			});
		};

		setIfEmpty("company", company);
		setIfEmpty("branch", branch);
		setIfEmpty("from_date", today);
		setIfEmpty("to_date", today);
		setDateIfFromToFilter();
	}

	function scheduleApply(attempt = 0) {
		applyDefaultsToCurrentReport();
		if (attempt < 20) {
			setTimeout(() => scheduleApply(attempt + 1), 200);
		}
	}

	frappe.router.on("change", () => {
		scheduleApply();
	});

	frappe.ready(() => {
		scheduleApply();
	});
})();
