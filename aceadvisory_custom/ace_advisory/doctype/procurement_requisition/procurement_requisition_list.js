frappe.listview_settings["Procurement Requisition"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colours = {
			Draft: "grey",
			"Department Head Review": "orange",
			"Finance Review": "blue",
			Approved: "green",
			Rejected: "red",
		};

		return [__(doc.status), colours[doc.status] || "grey", "status,=," + doc.status];
	},
};
