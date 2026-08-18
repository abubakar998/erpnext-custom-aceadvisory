# Copyright (c) 2026, Abu Bakar and contributors
# For license information, please see license.txt

from aceadvisory_custom.setup.procurement import setup_procurement


def execute():
	"""Create the procurement roles, workflow, RFQ link field and notification
	on sites where the app was already installed before this feature existed."""
	setup_procurement()
