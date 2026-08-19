# Manual Test Plan — Procurement Requisition

Step-by-step checks to verify each requirement in [requirements.md](requirements.md)
is actually met on a running site. Run after `bench --site <site> migrate` (or
`install-app`) has completed without error.

## 0. Test data setup

Create these once, before running the scenarios below.

### 0.1 Users

Create four test users (Desk User, no System Manager) so role behaviour is
tested for real instead of via an Administrator account, which is exempt from
the self-approval and role checks.

| User | Role to add |
|---|---|
| requester@test.com | Procurement Requester |
| depthead@test.com | Department Head |
| finance@test.com | Finance Reviewer |
| admin.officer@test.com | Administration Officer |

**User List → New**, set First Name + Email, save, open the **Roles** tab, add
the role from the table above (roles are created automatically by the app's
setup — if any is missing, re-run
`bench --site <site> execute aceadvisory_custom.setup.procurement.setup_procurement`).

### 0.2 Employees

Requester must be a real Employee linked to `requester@test.com` via the
Employee's **User ID** field, so `requested_by_user` fetches correctly:

**HR → Employee → New**
- Employee Name: `Test Requester`
- User ID: `requester@test.com`
- Department: pick or create one, e.g. `Operations - <Company Abbr>` (an
  existing Department under your default Company works fine)
- Company: your default Company
- Save.

### 0.3 Item

`item_code` is mandatory on every Procurement Requisition, so create at least
one Item before running any of the scenarios below.

**Stock → Item → New** — any purchasable Item with a Stock UOM, e.g. `Laptop`.

---

## 1. Task 1 — DocType shape

1. Log in as `requester@test.com`.
2. Go to **Procurement Requisition → New**.
3. Confirm these fields are present and behave as expected:
   - **Series**: shows `PR-.YYYY.-` pattern, read-only until save.
   - **Request Date**: defaults to today.
   - **Requested By**: Link to Employee; only Employees with `status = Active`
     are selectable (`frm.set_query` in the client script).
   - **Department**: auto-fills from the selected Employee's department once
     `Requested By` is set.
   - **Requested By (Name)** and **Requested By (User)**: read-only, fetched
     automatically from the Employee.
   - **Item**: Link to Item, marked mandatory; only Items with `disabled = 0`
     are selectable.
   - **Item Name**: read-only, auto-fills from the selected Item's
     `item_name` once **Item** is set — no free-text description to type or
     keep in sync with the Item master.
   - **Quantity** (defaults to 1), **Estimated Budget**, **Required Date**,
     **Justification**: all present and marked mandatory (red asterisk).
   - **Status**: read-only Select, shows `Draft`.
4. Save as `requester@test.com`. Expect: saves successfully, name becomes
   `PR-2026-00001` (or similar), Status shows `Draft`.

**Pass condition:** all fields from the requirements table exist, Requisition
No. is auto-generated, no fields need manual entry beyond what's expected.

---

## 2. Task 2 — Business validation

Do each of these both **in the browser** (client-side, instant) and **via API**
(server-side, authoritative) to prove neither layer alone is being relied on.

### 2.1 Quantity ≤ 0

- **Browser:** on a Procurement Requisition form, type `0` into Quantity and
  tab out. Expect an immediate red `msgprint` — "Quantity must be greater than
  zero." — and the field is cleared.
- **API (bypasses the client):**
  ```bash
  bench --site <site> execute frappe.get_doc --kwargs '{
    "doctype": "Procurement Requisition", "requested_by": "<employee-id>",
    "department": "<department>", "item_code": "Test Laptop", "quantity": 0,
    "estimated_budget": 100, "required_date": "2026-12-31",
    "justification": "test"}' 2>&1
  ```
  then call `.insert()` on it in a console (`bench --site <site> console`):
  ```python
  doc = frappe.get_doc({...same dict as above...})
  doc.insert()
  ```
  Expect a `frappe.ValidationError`: "Quantity must be greater than zero."

### 2.2 Estimated Budget ≤ 0

Repeat 2.1 with `quantity=1, estimated_budget=0`. Expect: "Estimated Budget
must be greater than zero." on both the form and via console `insert()`.

### 2.3 Required Date in the past

Repeat with a `required_date` set to yesterday. Expect: on the form, a red
message and the field is cleared; via console, "Required Date ... cannot be
earlier than today ...".

### 2.4 Required Date is *not* re-validated when unchanged

- Create and submit a requisition with `required_date` = tomorrow.
- Wait a day (or, faster: temporarily set the system date forward, or just
  reason about it via code review) — the point to verify is behavioural: open
  the doc again as an approver and change the **Status** only (via workflow
  action). Confirm the save does **not** fail even though `required_date` is
  now "today" or in the past, because `has_value_changed("required_date")` is
  `False`. This proves an approval isn't blocked by a date that was valid at
  entry time.

**Pass condition:** all three validations fire server-side (cannot be
bypassed via API/console) and are mirrored client-side for instant feedback.

---

## 3. Task 3 — Approval workflow

Use the four test users from §0.1. Create one fresh Procurement Requisition as
`requester@test.com` for each scenario below (**Draft**, save, note the name).

### 3.1 Happy path, one stage at a time

1. As `requester@test.com`, open the Draft requisition → **Submit for Review**.
   Expect: Status → `Department Head Review`.
2. Log out, log in as `depthead@test.com` → open the requisition →
   **Approve**. Expect: Status → `Finance Review`, and on the **Approval
   Trail** section, `Department Head Approved By` = `depthead@test.com` with a
   timestamp.
3. Log out, log in as `finance@test.com` → **Approve**. Expect: Status →
   `Approved`, document becomes **submitted** (docstatus = 1), `Finance
   Approved By` = `finance@test.com` with a timestamp.

**Pass condition:** the requisition moves through all four stages in order,
with the workflow action buttons only offering the actions valid for the
current stage.

### 3.2 Stages cannot be skipped

1. As `requester@test.com`, create a new Draft requisition.
2. Confirm the only workflow action available is **Submit for Review** — there
   is no direct "Approve" or "Finance Review" action visible from Draft.
3. Attempt to shortcut via API — as `depthead@test.com`, try to set
   `status = "Approved"` directly and save (bypassing the workflow action):
   ```python
   # bench --site <site> console, logged in context simulated via frappe.set_user
   frappe.set_user("depthead@test.com")
   doc = frappe.get_doc("Procurement Requisition", "<name-still-in-Draft>")
   doc.status = "Approved"
   doc.save()
   ```
   Expect: this either fails permission checks, or if it somehow reaches
   `before_submit` (e.g. someone also calls `.submit()`), the requisition
   still isn't docstatus 1 unless status is exactly `Approved`, and
   `before_submit` throws "A Procurement Requisition can only be submitted
   through the approval workflow." if `.submit()` is called out of band.

**Pass condition:** there is no UI or API path that lands a requisition on
`Approved`/submitted without passing through `Department Head Review` and
`Finance Review` in order.

### 3.3 Only the correct role can act at each stage

1. Create a requisition, submit it to `Department Head Review`.
2. Log in as `finance@test.com` (wrong role for this stage) and open it.
   Expect: no workflow action buttons are available to them (Finance Reviewer
   is not the `allowed` role for the `Department Head Review` state).
3. Log in as `depthead@test.com`, **Approve** → now in `Finance Review`.
4. Log in as `requester@test.com` (wrong role) and open it. Expect: no
   Approve/Reject actions visible.

**Pass condition:** the action buttons shown are gated by role at every stage,
not just by document status.

### 3.4 Requester cannot approve their own request

1. As `requester@test.com`, create and submit a requisition to `Department
   Head Review`.
2. Now also grant `requester@test.com` the `Department Head` role temporarily
   (User → Roles), simulating one person wearing two hats.
3. Still logged in as `requester@test.com`, open the requisition. Expect:
   the **Approve**/**Reject** actions are hidden (workflow `condition`
   evaluates `doc.requested_by_user != frappe.session.user` → `False`).
4. If the action is somehow still reachable (e.g. via `bench console`
   forcing the transition), confirm `validate_self_approval()` throws "You
   cannot approve a Procurement Requisition you raised yourself." Remove the
   extra role from the user afterwards to restore the clean test setup.

**Pass condition:** the requester — whether identified by document `owner` or
by the `requested_by_user` field — can never move their own request past
Draft.

### 3.5 Rejection path

1. As `depthead@test.com`, on a requisition in `Department Head Review`,
   choose **Reject**. Expect: Status → `Rejected`.
2. As `requester@test.com`, open the rejected requisition. Expect: only
   **Reopen** is available. Click it → Status → `Draft`, and the Approval
   Trail fields (`department_head_approved_by/on`, `finance_approved_by/on`)
   are cleared.

---

## 4. Task 4 — Procurement Requisition Summary report

1. As a user with report access (e.g. `finance@test.com` or System Manager),
   go to **Report → Procurement Requisition Summary**.
2. Confirm the columns shown: Requisition No. (link), Request Date, Requested
   By, Employee Name, Department, Estimated Budget, Current Status.
3. Set the **Department** filter to one specific department. Expect: only
   requisitions from that department are listed.
4. Clear Department, set the **Status** filter to `Approved`. Expect: only
   Approved/submitted requisitions are listed.
5. Set a **From Date**/**To Date** range that excludes today. Expect: today's
   test requisitions drop out of the list, confirming the date filter works.
6. Confirm the **Status** column renders as a coloured indicator pill
   (grey/orange/blue/green/red per status).
7. Log in as `requester@test.com` (who only has `if_owner` read access) and
   open the same report. Expect: only requisitions they personally own are
   listed — proving the report inherits DocType permissions rather than
   showing everyone's data.

**Pass condition:** all 5 required columns are present, both required filters
(Department, Status) work, and permission-scoping is respected per user.

---

## 5. Part B — Automation

### 5.1 Option A — Create RFQ button

1. Take the requisition from §3.1 (now `Approved`, submitted) — `item_code`
   is mandatory on the doctype, so every requisition already has one from
   creation; no extra setup needed here.
2. Log in as `admin.officer@test.com`, open the requisition.
3. Confirm a **Create RFQ** button (primary/blue) appears — and confirm it
   does **not** appear on a requisition that is still in Draft or any review
   stage.
4. Click it → confirm the `frappe.confirm` dialog text mentions the quantity,
   UOM and item name.
5. Confirm → a new **Request for Quotation** form opens, pre-filled with:
   - `procurement_requisition` = the source requisition's name
   - one item row with the correct item code, qty, UOM
   - `schedule_date` = the requisition's Required Date
   - `subject` and `message_for_supplier` populated
6. Save the RFQ (suppliers can be added manually — intentionally not
   pre-filled).
7. Go back to the requisition and click **Create RFQ** again. Expect: a
   "Request for Quotation ... has already been raised for this requisition."
   error — the duplicate guard.

### 5.2 Option B — Administration notification

1. Complete an approval flow (§3.1) through to `Approved`.
2. Log in as `admin.officer@test.com` → open the notification bell (top
   right). Expect: a new System Notification referencing the requisition
   number, with the message body showing Requested By, Department, Item,
   Estimated Budget and Required By, matching the template in
   `create_approval_notification`.
3. Confirm a requisition that reaches any other status (Draft, Rejected, etc.)
   does **not** trigger this notification — only the transition to `Approved`
   does.

**Pass condition:** both automations behave correctly and independently; the
duplicate-RFQ guard and the Approved-only notification condition both hold.

---

## 6. Regression checks

- Re-run `bench --site <site> migrate` a second time with no changes. Expect:
  no errors, and `setup_procurement()` makes no duplicate roles/workflow
  states/notification (idempotent — check counts before/after via
  `frappe.db.count("Role", {"role_name": ["in", [...]]})`).
- Confirm no Python/JS console errors appear in the browser dev tools while
  exercising the form and report.
