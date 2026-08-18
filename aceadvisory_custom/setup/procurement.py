# Copyright (c) 2026, Abu Bakar and contributors
# For license information, please see license.txt

"""Idempotent setup of everything the Procurement Requisition needs but that
lives in *data* rather than in code: roles, the approval workflow, the link
field on Request for Quotation and the Administration notification.

Run automatically on `bench install-app` (after_install) and on `bench migrate`
(patch). Safe to re-run by hand:

    bench --site <site> execute aceadvisory_custom.setup.procurement.setup_procurement
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

WORKFLOW_NAME = "Procurement Requisition Approval"
DOCTYPE = "Procurement Requisition"

REQUESTER = "Procurement Requester"
DEPARTMENT_HEAD = "Department Head"
FINANCE_REVIEWER = "Finance Reviewer"
ADMINISTRATION = "Administration Officer"

ROLES = (REQUESTER, DEPARTMENT_HEAD, FINANCE_REVIEWER, ADMINISTRATION)

# Available to the approving user only when they are not the requester. This is
# the second half of the self-approval rule: `allow_self_approval = 0` covers the
# document owner, this covers the employee named in `requested_by`.
NOT_THE_REQUESTER = (
	'frappe.session.user == "Administrator" or '
	"(doc.requested_by_user != frappe.session.user and doc.owner != frappe.session.user)"
)

# state, docstatus, allow_edit, indicator style
STATES = (
	("Draft", "0", REQUESTER, ""),
	("Department Head Review", "0", DEPARTMENT_HEAD, "Warning"),
	("Finance Review", "0", FINANCE_REVIEWER, "Primary"),
	("Approved", "1", ADMINISTRATION, "Success"),
	("Rejected", "0", REQUESTER, "Danger"),
)

# state, action, next state, allowed role, allow_self_approval, condition
TRANSITIONS = (
	("Draft", "Submit for Review", "Department Head Review", REQUESTER, 1, None),
	("Department Head Review", "Approve", "Finance Review", DEPARTMENT_HEAD, 0, NOT_THE_REQUESTER),
	("Department Head Review", "Reject", "Rejected", DEPARTMENT_HEAD, 0, NOT_THE_REQUESTER),
	("Finance Review", "Approve", "Approved", FINANCE_REVIEWER, 0, NOT_THE_REQUESTER),
	("Finance Review", "Reject", "Rejected", FINANCE_REVIEWER, 0, NOT_THE_REQUESTER),
	("Rejected", "Reopen", "Draft", REQUESTER, 1, None),
)

RFQ_CUSTOM_FIELDS = {
	"Request for Quotation": [
		{
			"fieldname": "procurement_requisition",
			"fieldtype": "Link",
			"label": "Procurement Requisition",
			"options": DOCTYPE,
			"insert_after": "opportunity",
			"read_only": 1,
			"no_copy": 1,
			"search_index": 1,
			"translatable": 0,
		}
	]
}

NOTIFICATION_NAME = "Procurement Requisition Approved"


def setup_procurement():
	create_roles()
	create_custom_fields(RFQ_CUSTOM_FIELDS, ignore_validate=True)
	create_workflow()
	create_approval_notification()
	frappe.db.commit()


def create_roles():
	for role in ROLES:
		if frappe.db.exists("Role", role):
			continue

		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)


def create_workflow():
	"""(Re)build the approval workflow from the tables above.

	The child tables are cleared and rebuilt so this stays the single source of
	truth: editing the tuples above and re-running is the supported way to change
	the workflow, rather than hand-editing it in the UI where it would drift.
	"""
	ensure_workflow_masters()

	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
	else:
		workflow = frappe.new_doc("Workflow")
		workflow.workflow_name = WORKFLOW_NAME

	workflow.update(
		{
			"document_type": DOCTYPE,
			# Drive the doctype's own Select field instead of letting Frappe add a
			# second, hidden `workflow_state` custom field. One status, one source.
			"workflow_state_field": "status",
			"is_active": 1,
			"send_email_alert": 0,
		}
	)

	workflow.set("states", [])
	for state, doc_status, allow_edit, _style in STATES:
		workflow.append("states", {"state": state, "doc_status": doc_status, "allow_edit": allow_edit})

	workflow.set("transitions", [])
	for state, action, next_state, allowed, allow_self_approval, condition in TRANSITIONS:
		workflow.append(
			"transitions",
			{
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": allowed,
				"allow_self_approval": allow_self_approval,
				"condition": condition,
			},
		)

	workflow.save(ignore_permissions=True)


def ensure_workflow_masters():
	"""Workflow States and Actions are link targets; create the ones Frappe ships without."""
	for state, _doc_status, _allow_edit, style in STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)

	for _state, action, *_rest in TRANSITIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)


def create_approval_notification():
	"""Tell Administration that an approved requisition is waiting for an RFQ.

	Delivered as a desk (System) notification so it works on any site without an
	outgoing email account configured; switch `channel` to Email once one exists.
	"""
	if frappe.db.exists("Notification", NOTIFICATION_NAME):
		return

	notification = frappe.get_doc(
		{
			"doctype": "Notification",
			"name": NOTIFICATION_NAME,
			"subject": "Procurement Requisition {{ doc.name }} approved",
			"document_type": DOCTYPE,
			"channel": "System Notification",
			"event": "Submit",
			"condition_type": "Python",
			"condition": 'doc.status == "Approved"',
			"enabled": 1,
			"send_system_notification": 1,
			"message_type": "Markdown",
			"message": (
				"Procurement Requisition **{{ doc.name }}** has been approved and is ready "
				"for the RFQ process.\n\n"
				"- **Requested By:** {{ doc.requested_by_name or doc.requested_by }}\n"
				"- **Department:** {{ doc.department }}\n"
				"- **Item:** {{ doc.item_description }} ({{ doc.quantity }} {{ doc.uom or '' }})\n"
				"- **Estimated Budget:** {{ frappe.utils.fmt_money(doc.estimated_budget) }}\n"
				"- **Required By:** {{ frappe.utils.formatdate(doc.required_date) }}\n"
			),
		}
	)
	notification.append("recipients", {"receiver_by_role": ADMINISTRATION})
	notification.insert(ignore_permissions=True)
