# Copyright (c) 2026, Abu Bakar and contributors
# For license information, please see license.txt

from aceadvisory_custom.setup.procurement import setup_procurement


def after_install():
	setup_procurement()
