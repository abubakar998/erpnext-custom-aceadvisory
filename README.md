### Ace Advisory

Ace Advisory Custom App

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app aceadvisory_custom
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/aceadvisory_custom
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit

---

## Procurement Requisition — Implementation Notes

Implements the initial phase of the internal procurement workflow: an employee
raises a **Procurement Requisition**, it is reviewed by the Department Head and
Finance, and once Approved, Administration raises a Request for Quotation.

### Task 1 — DocType

`Procurement Requisition` ([doctype folder](aceadvisory_custom/ace_advisory/doctype/procurement_requisition))
is submittable and number itself via the naming series `PR-.YYYY.-`. Beyond the
required fields (Request Date, Requested By, Department, Item Description,
Quantity, Estimated Budget, Required Date, Justification, Status) it adds:

- `company`, `item_code`, `uom` — needed to raise a proper RFQ later; without an
  Item and UOM there's nothing valid to map onto the RFQ's item table.
- `requested_by_name`, `requested_by_user` — fetched read-only from the
  `Requested By` Employee (`employee_name`, `user_id`). `requested_by_user` is
  what the self-approval check and workflow condition compare against, since a
  requisition can be entered by someone else on the requester's behalf.
- `department_head_approved_by/on`, `finance_approved_by/on` — a lightweight
  audit trail stamped by the controller, so who-approved-what is visible on the
  form without digging into the version log.

`Status` is a plain Select field and doubles as the workflow's state field
(`workflow_state_field = "status"`) — this avoids Frappe's default of adding a
second, hidden `workflow_state` field, so there is exactly one source of truth
for where a requisition is in the process.

### Task 2 — Business Validation

Implemented as **both** a Server Script (the authority) and a Client Script
(a mirror, for immediate feedback):

- **Server** ([procurement_requisition.py](aceadvisory_custom/ace_advisory/doctype/procurement_requisition/procurement_requisition.py))
  — `validate_quantity`, `validate_estimated_budget`, `validate_required_date`
  run in `validate()`, so they're enforced no matter how the document is saved
  (Desk form, REST API, data import, console). This is the one that actually
  protects data integrity and cannot be bypassed by the client.
- **Client** ([procurement_requisition.js](aceadvisory_custom/ace_advisory/doctype/procurement_requisition/procurement_requisition.js))
  — the same three checks re-implemented on field-change events, so a user sees
  the error the moment they type a bad value instead of after a round trip to
  the server on save.

Why both, rather than just one: server-only is correct but gives no feedback
until save; client-only is fast but trivially bypassed (browser console, API
call) and would let bad data into the database. The comment at the top of the
`.js` file states this explicitly so the duplication reads as intentional, not
copy-paste drift.

One deliberate nuance on `Required Date`: the check only fires when that field
has actually changed (`has_value_changed`). Without that guard, an Approval
happening a few days after the requisition was raised would fail validation on
a date that was perfectly valid when the requester entered it.

### Task 3 — Approval Workflow

Built in [setup/procurement.py](aceadvisory_custom/setup/procurement.py) as data
(Workflow + Workflow State + Workflow Action Master + Role documents) rather
than hand-configured in the UI, and installed idempotently via `after_install`
and a `post_model_sync` patch — so the same setup reproduces identically on any
site (`bench --site <site> execute aceadvisory_custom.setup.procurement.setup_procurement`
also re-runs it by hand).

States and the role allowed to act at each one:

| State | Role | docstatus |
|---|---|---|
| Draft | Procurement Requester | 0 |
| Department Head Review | Department Head | 0 |
| Finance Review | Finance Reviewer | 0 |
| Approved | Administration Officer | 1 (submitted) |
| Rejected | Procurement Requester | 0 |

Transitions only go forward one stage at a time (Draft → Department Head
Review → Finance Review → Approved, with a Reject branch back to Draft at
either review stage) — there is no transition that skips a stage, so the
workflow itself enforces the required order.

**No self-approval**, enforced twice:
- `allow_self_approval = 0` on every transition past Draft — Frappe's built-in
  check, which compares the acting user against the document `owner`.
- A `condition` on each transition plus a matching check in
  `validate_self_approval()` also compares against `requested_by_user`. This
  is needed because the *owner* (whoever clicked Save) and the *requester*
  named on the form are not always the same person — e.g. an assistant filing
  a requisition on a manager's behalf. Both checks are exempted for
  Administrator so the account used for setup/testing isn't locked out.
  The server-side check is the one that actually matters (workflow conditions
  can't be trusted alone since `frappe.session.user` in a condition string
  only guards the transition button, not a direct API state change);
  `before_submit()` additionally refuses to let a document reach docstatus 1
  unless `status == "Approved"`, closing off a direct `doc.submit()` call as a
  bypass route.

DocType permissions (see the Roles and Permissions grid on the DocType) give
each role write access without submit, except Finance Reviewer and System
Manager, who can submit — matching where "Approved" sits in the flow (it's the
submitted state).

### Task 4 — Report

[Procurement Requisition Summary](aceadvisory_custom/ace_advisory/report/procurement_requisition_summary)
is a script report showing Requisition No., Requested By (+ Employee Name),
Department, Estimated Budget and Current Status, with filters for Department,
Status, Company and a request-date range. It fetches through
`frappe.get_list` rather than a raw SQL query so it inherits the DocType's own
permission rules for free — a Procurement Requester with `if_owner` access
only ever sees their own requisitions in the report, with no extra filtering
code needed here.

### Part B — Automation

Both options were implemented, since they cover the two natural points in the
process (immediate action vs. handoff notice) and neither duplicates the
other's work:

- **Option A — Create RFQ button**
  ([procurement_requisition.js](aceadvisory_custom/ace_advisory/doctype/procurement_requisition/procurement_requisition.js),
  `make_request_for_quotation` in the `.py` controller) — appears only once a
  requisition is submitted and Approved. It confirms with the user, then maps
  the requisition onto a draft Request for Quotation via `get_mapped_doc`
  (item, quantity, UOM, schedule date, subject, message for supplier all
  pre-filled). Suppliers are deliberately left blank — choosing who to invite
  to quote is Administration's judgment call, not something to guess at. A
  duplicate-RFQ guard stops a second RFQ being raised against the same
  requisition.
- **Option B — Administration notification** (`create_approval_notification`
  in `setup/procurement.py`) — a Notification doctype record, delivered as a
  System Notification (not email) so it works out of the box with no outgoing
  email account configured, sent to everyone with the Administration Officer
  role when a requisition's `event: Submit` fires with `status == "Approved"`.

### Installing / verifying

```bash
bench --site <site> install-app aceadvisory_custom
# or, on a site that already has the app:
bench --site <site> migrate
```

Both run `setup_procurement()`, which creates the four roles, the workflow,
the `procurement_requisition` link field on Request for Quotation, and the
Administration notification. It's safe to re-run by hand:

```bash
bench --site <site> execute aceadvisory_custom.setup.procurement.setup_procurement
```
