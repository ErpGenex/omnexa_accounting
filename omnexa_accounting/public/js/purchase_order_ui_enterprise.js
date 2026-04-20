// Copyright (c) 2026, Omnexa
// Enterprise UX enhancement for Purchase Order (non-destructive).

(function () {
	"use strict";

	function mark_purchase_order_structure(frm) {
		if (!frm || !frm.wrapper) return;
		const wrapper = frm.wrapper;
		wrapper.classList.add("omnexa-po-enterprise");

		const coreFields = ["company", "supplier", "transaction_date", "schedule_date"];
		coreFields.forEach((fieldname) => {
			const control = wrapper.querySelector(`.frappe-control[data-fieldname='${fieldname}']`);
			if (!control) return;
			control.classList.add("omnexa-core-field");
			const section = control.closest(".form-section");
			if (section) section.classList.add("omnexa-core-section");
		});

		const itemsControl = wrapper.querySelector(".frappe-control[data-fieldname='items']");
		if (itemsControl) {
			itemsControl.classList.add("omnexa-items-grid-control");
			const section = itemsControl.closest(".form-section");
			if (section) section.classList.add("omnexa-items-section");
		}

		// Visual proof that enterprise enhancer is active on this screen.
		const title = wrapper.querySelector(".page-title .title-text, .title-area .title-text");
		if (title && !wrapper.querySelector(".omnexa-po-badge")) {
			const badge = document.createElement("span");
			badge.className = "indicator-pill blue omnexa-po-badge";
			badge.style.marginInlineStart = "8px";
			badge.textContent = "Enterprise Layout";
			title.appendChild(badge);
		}
	}

	function focus_first_action_on_new(frm) {
		if (!frm || !frm.is_new()) return;
		window.requestAnimationFrame(() => {
			const primaryButton = frm.wrapper.querySelector(".page-actions .btn-primary");
			if (primaryButton) primaryButton.classList.add("omnexa-primary-action");
		});
	}

	frappe.ui.form.on("Purchase Order", {
		onload_post_render(frm) {
			mark_purchase_order_structure(frm);
			focus_first_action_on_new(frm);
		},
		refresh(frm) {
			mark_purchase_order_structure(frm);
			focus_first_action_on_new(frm);
		},
	});
})();
