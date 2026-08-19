# Copyright (c) 2026, Abu Bakar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, now_datetime, nowdate

#: Workflow states, kept in one place so the controller and the workflow
#: definition (aceadvisory_custom/setup/procurement.py) cannot drift apart.
DRAFT = "Draft"
DEPARTMENT_HEAD_REVIEW = "Department Head Review"
FINANCE_REVIEW = "Finance Review"
APPROVED = "Approved"
REJECTED = "Rejected"


class ProcurementRequisition(Document):
	def validate(self):
		self.validate_quantity()
		self.validate_estimated_budget()
		self.validate_required_date()
		self.validate_self_approval()
		self.set_approval_trail()

	def before_submit(self):
		# The workflow is the only sanctioned route to submission. This guard makes
		# a direct `doc.submit()` (REST/API/console) fail instead of silently
		# producing an approved requisition that never passed the reviews.
		if self.status != APPROVED:
			frappe.throw(
				_("A Procurement Requisition can only be submitted through the approval workflow."),
				title=_("Workflow Required"),
			)

	# ---------------------------------------------------------------- validations

	def validate_quantity(self):
		if flt(self.quantity) <= 0:
			frappe.throw(
				_("Quantity must be greater than zero."),
				title=_("Invalid Quantity"),
				exc=frappe.ValidationError,
			)

	def validate_estimated_budget(self):
		if flt(self.estimated_budget) <= 0:
			frappe.throw(
				_("Estimated Budget must be greater than zero."),
				title=_("Invalid Estimated Budget"),
				exc=frappe.ValidationError,
			)

	def validate_required_date(self):
		"""Required Date may not be in the past.

		Only enforced while the value is actually being set or changed. Without
		this guard an approval done a few days after the requisition was raised
		would fail on a date that was perfectly valid when it was entered.
		"""
		if not self.required_date or not self.has_value_changed("required_date"):
			return

		if getdate(self.required_date) < getdate(nowdate()):
			frappe.throw(
				_("Required Date {0} cannot be earlier than today ({1}).").format(
					frappe.bold(frappe.format(self.required_date, {"fieldtype": "Date"})),
					frappe.bold(frappe.format(nowdate(), {"fieldtype": "Date"})),
				),
				title=_("Invalid Required Date"),
			)

	def validate_self_approval(self):
		"""Block the requester from moving their own request forward.

		The workflow already carries `allow_self_approval = 0`, but that check
		only compares the document *owner*. A requisition can legitimately be
		entered by someone else on the requester's behalf, so the approving user
		is also compared against the employee named in `requested_by`.
		"""
		if not self.has_value_changed("status"):
			return

		if self.status not in (FINANCE_REVIEW, APPROVED):
			return

		user = frappe.session.user
		# Mirrors frappe.model.workflow.has_approval_access: Administrator is exempt.
		if user == "Administrator":
			return

		if user in (self.requested_by_user, self.owner):
			frappe.throw(
				_("You cannot approve a Procurement Requisition you raised yourself."),
				title=_("Self Approval Not Allowed"),
			)

	# ------------------------------------------------------------- approval trail

	def set_approval_trail(self):
		"""Stamp who cleared each stage, so the audit is readable without the version log."""
		if not self.has_value_changed("status"):
			return

		if self.status == FINANCE_REVIEW:
			self.department_head_approved_by = frappe.session.user
			self.department_head_approved_on = now_datetime()
		elif self.status == APPROVED:
			self.finance_approved_by = frappe.session.user
			self.finance_approved_on = now_datetime()
		elif self.status == DRAFT:
			# Reopened after a rejection: the previous sign-offs no longer apply.
			self.department_head_approved_by = None
			self.department_head_approved_on = None
			self.finance_approved_by = None
			self.finance_approved_on = None


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	"""Map an approved Procurement Requisition onto a draft Request for Quotation.

	Suppliers are deliberately left empty: choosing whom to invite is the
	Administration team's decision and belongs on the RFQ form.
	"""
	frappe.only_for(("Administration Officer", "System Manager"))

	source = frappe.get_doc("Procurement Requisition", source_name)
	source.check_permission("read")

	existing = frappe.db.get_value(
		"Request for Quotation",
		{"procurement_requisition": source_name, "docstatus": ["<", 2]},
		"name",
	)
	if existing:
		frappe.throw(
			_("Request for Quotation {0} has already been raised for this requisition.").format(
				frappe.utils.get_link_to_form("Request for Quotation", existing)
			),
			title=_("Already Raised"),
		)

	def set_missing_values(source, target):
		item_defaults = frappe.db.get_value(
			"Item", source.item_code, ["item_name", "description", "stock_uom"], as_dict=True
		)
		uom = source.uom or item_defaults.stock_uom

		target.procurement_requisition = source.name
		target.transaction_date = nowdate()
		target.schedule_date = source.required_date
		target.subject = _("Request for Quotation: {0}").format(item_defaults.item_name)
		target.message_for_supplier = source.justification

		target.append(
			"items",
			{
				"item_code": source.item_code,
				"item_name": item_defaults.item_name,
				"description": item_defaults.description,
				"qty": source.quantity,
				"uom": uom,
				"stock_uom": item_defaults.stock_uom,
				"conversion_factor": get_conversion_factor(source.item_code, uom),
				"schedule_date": source.required_date,
			},
		)

	return get_mapped_doc(
		"Procurement Requisition",
		source_name,
		{
			"Procurement Requisition": {
				"doctype": "Request for Quotation",
				"field_map": {"company": "company"},
				"validation": {"docstatus": ["=", 1], "status": ["=", APPROVED]},
			}
		},
		target_doc,
		set_missing_values,
	)


def get_conversion_factor(item_code, uom):
	from erpnext.stock.get_item_details import get_conversion_factor as _get_conversion_factor

	return flt(_get_conversion_factor(item_code, uom).get("conversion_factor")) or 1.0
