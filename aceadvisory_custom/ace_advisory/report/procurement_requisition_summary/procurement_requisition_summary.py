# Copyright (c) 2026, Abu Bakar and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Requisition No."),
			"fieldtype": "Link",
			"options": "Procurement Requisition",
			"width": 160,
		},
		{
			"fieldname": "request_date",
			"label": _("Request Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "requested_by",
			"label": _("Requested By"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{
			"fieldname": "requested_by_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 200,
		},
		{
			"fieldname": "estimated_budget",
			"label": _("Estimated Budget"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "status",
			"label": _("Current Status"),
			"fieldtype": "Data",
			"width": 180,
		},
	]


def get_data(filters):
	"""Fetched with `frappe.get_list` rather than a raw query so the report
	inherits the DocType's permissions: a Procurement Requester with `if_owner`
	read access sees only their own requisitions, without any extra code here."""
	conditions = {"docstatus": ["<", 2]}

	for fieldname in ("company", "department", "status"):
		if filters.get(fieldname):
			conditions[fieldname] = filters.get(fieldname)

	if filters.get("from_date") and filters.get("to_date"):
		conditions["request_date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.get("from_date"):
		conditions["request_date"] = [">=", filters.from_date]
	elif filters.get("to_date"):
		conditions["request_date"] = ["<=", filters.to_date]

	return frappe.get_list(
		"Procurement Requisition",
		filters=conditions,
		fields=[
			"name",
			"request_date",
			"requested_by",
			"requested_by_name",
			"department",
			"estimated_budget",
			"status",
		],
		order_by="request_date desc, name desc",
		limit_page_length=0,
	)
