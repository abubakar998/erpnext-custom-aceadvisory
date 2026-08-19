// Copyright (c) 2026, Abu Bakar and contributors
// For license information, please see license.txt

// The checks below duplicate `procurement_requisition.py` on purpose: the server
// is the authority, the client only gives the user immediate feedback instead of
// making them wait for a failed save.

frappe.ui.form.on("Procurement Requisition", {
	setup(frm) {
		frm.set_query("requested_by", () => ({
			filters: { status: "Active" },
		}));

		frm.set_query("department", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));

		frm.set_query("item_code", () => ({
			filters: { disabled: 0 },
		}));
	},

	refresh(frm) {
		frm.trigger("add_create_rfq_button");
	},

	add_create_rfq_button(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status !== "Approved") return;
		if (!frappe.user.has_role("Administration Officer") && !frappe.user.has_role("System Manager")) return;

		frm.add_custom_button(__("Create RFQ"), () => {
			frappe.confirm(
				__("Raise a Request for Quotation for {0} {1} of {2}?", [
					format_number(frm.doc.quantity),
					frm.doc.uom || "",
					frm.doc.item_name.bold(),
				]),
				() => {
					frappe.model.open_mapped_doc({
						method: "aceadvisory_custom.ace_advisory.doctype.procurement_requisition.procurement_requisition.make_request_for_quotation",
						frm: frm,
					});
				}
			);
		}).addClass("btn-primary");
	},

	quantity(frm) {
		reject_non_positive(frm, "quantity", __("Quantity must be greater than zero."));
	},

	estimated_budget(frm) {
		reject_non_positive(frm, "estimated_budget", __("Estimated Budget must be greater than zero."));
	},

	required_date(frm) {
		if (!frm.doc.required_date) return;

		if (frappe.datetime.get_diff(frm.doc.required_date, frappe.datetime.get_today()) < 0) {
			frappe.msgprint({
				title: __("Invalid Required Date"),
				message: __("Required Date cannot be earlier than today."),
				indicator: "red",
			});
			frm.set_value("required_date", "");
		}
	},
});

function reject_non_positive(frm, fieldname, message) {
	if (frm.doc[fieldname] === undefined || frm.doc[fieldname] === null || frm.doc[fieldname] === "") return;

	if (flt(frm.doc[fieldname]) <= 0) {
		frappe.msgprint({ title: __("Invalid Value"), message: message, indicator: "red" });
		frm.set_value(fieldname, null);
	}
}
