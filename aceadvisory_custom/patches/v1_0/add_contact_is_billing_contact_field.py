# Copyright (c) 2026, Abu Bakar and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
	"""Add the 'is_billing_contact' field on Contact.

	ERPNext's get_default_contact() (erpnext/accounts/party.py) queries this
	column, but the installed Frappe version does not ship it on the Contact
	doctype yet, causing "Unknown column 'tabContact.is_billing_contact'"
	errors (e.g. when creating a Supplier Quotation from a Request for
	Quotation). Adding it as a custom field keeps that query working until
	Frappe ships the field upstream.
	"""
	if frappe.db.has_column("Contact", "is_billing_contact"):
		return

	create_custom_field(
		"Contact",
		{
			"fieldname": "is_billing_contact",
			"label": "Is Billing Contact",
			"fieldtype": "Check",
			"insert_after": "is_primary_contact",
			"default": "0",
		},
	)
