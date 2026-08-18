// Copyright (c) 2026, Abu Bakar and contributors
// For license information, please see license.txt

const STATUS_COLOURS = {
	Draft: "gray",
	"Department Head Review": "orange",
	"Finance Review": "blue",
	Approved: "green",
	Rejected: "red",
};

frappe.query_reports["Procurement Requisition Summary"] = {
	filters: [
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Draft", "Department Head Review", "Finance Review", "Approved", "Rejected"],
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && data && STATUS_COLOURS[data.status]) {
			value = `<span class="indicator-pill ${STATUS_COLOURS[data.status]}">${value}</span>`;
		}

		return value;
	},
};
