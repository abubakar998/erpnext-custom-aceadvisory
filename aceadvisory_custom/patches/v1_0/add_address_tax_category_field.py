# Copyright (c) 2026, Abu Bakar and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
	"""Add the 'tax_category' field on Address.

	ERPNext's get_address_tax_category() (erpnext/accounts/party.py) queries
	this column, but the installed Frappe version does not ship it on the
	Address doctype yet, causing "Unknown column 'tax_category'" errors
	(e.g. when creating a Supplier Quotation from a Request for Quotation).
	Adding it as a custom field keeps that query working until Frappe ships
	the field upstream. See also is_billing_contact on Contact
	(add_contact_is_billing_contact_field.py) for the same class of issue.
	"""
	if frappe.db.has_column("Address", "tax_category"):
		return

	create_custom_field(
		"Address",
		{
			"fieldname": "tax_category",
			"label": "Tax Category",
			"fieldtype": "Link",
			"options": "Tax Category",
			"insert_after": "country",
		},
	)
