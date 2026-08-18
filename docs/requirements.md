# ERPNext / Frappe Developer Practical Assessment

## Candidate Prerequisites

Candidates are expected to have a working local development environment before the
assessment begins.

The environment should include:

- Latest stable version of Frappe Framework
- ERPNext installed
- Bench configured
- Developer Mode enabled
- A fresh test site

The interview panel will not provide an ERPNext instance or development environment.
Candidates are responsible for ensuring their environment is operational before the
assessment.

## Assessment Objective

This assessment is designed to evaluate your ability to analyze business requirements,
design ERPNext solutions, implement customizations, and explain your technical
decisions.

We encourage candidates to use modern development tools responsibly. We are interested
not only in the final solution but also in your problem-solving process, implementation
approach, and understanding of ERPNext/Frappe.

**Note:** During the technical discussion, you will be asked to explain your
implementation. The ability to understand, verify, and maintain your solution is more
important than simply producing working code.

## Business Scenario

A growing professional services company wants to strengthen its internal procurement
process using ERPNext.

The proposed workflow is:

```
Employee creates a Procurement Requisition
↓
Department Head reviews the request
↓
Finance verifies budget availability
↓
Administration receives the approved request
↓
Administration initiates the Request for Quotation (RFQ) process
```

Your task is to develop the initial phase of this workflow.

## Part A – Core Development

### Task 1 – Create Procurement Requisition

Create a new DocType named **Procurement Requisition**.

Include the following minimum fields:

| Field | Type |
|---|---|
| Requisition No. | Auto Generated |
| Request Date | Date |
| Requested By | Link (Employee/User) |
| Department | Link |
| Item Description | Data |
| Quantity | Float |
| Estimated Budget | Currency |
| Required Date | Date |
| Justification | Small Text |
| Status | Select |

You may add additional fields if you believe they improve the solution.

**Evaluation**
- Appropriate data model
- Correct field selection
- Naming conventions
- Overall design

### Task 2 – Business Validation (15 Marks)

Implement the following validations:

- Quantity must be greater than zero.
- Estimated Budget must be greater than zero.
- Required Date cannot be earlier than today's date.

After implementation, briefly explain:

- Whether you used a Client Script or Server Script.
- Why you selected that approach.

**Evaluation**
- Validation logic
- Error handling
- Choice of implementation

### Task 3 – Approval Workflow (20 Marks)

Configure the following approval workflow:

```
Draft
↓
Department Head Review
↓
Finance Review
↓
Approved
```

Requirements:

- Workflow stages must not be skipped.
- Only the appropriate role should approve each stage.
- The requester should not be able to approve their own request.

**Evaluation**
- Workflow configuration
- Role permissions
- Business logic

### Task 4 – Procurement Report (10 Marks)

Create a report displaying:

- Requisition Number
- Requested By
- Department
- Estimated Budget
- Current Status

Include filters for:

- Department
- Status

**Evaluation**
- Report accuracy
- Filters
- Readability

## Part B – Automation (20 Marks)

Choose **ONE** of the following options.

### Option A

Create a custom button named:

**Create RFQ**

When clicked:

- Display a confirmation message, or
- Create a Request for Quotation document populated with information from the
  Procurement Requisition.

### Option B

Automatically send a notification (email or system notification) to the
Administration team after the requisition reaches the **Approved** status.

### Option C

Implement another automation that you believe would improve this procurement
process.

Be prepared to explain your design decisions.

**Evaluation**
- Practical implementation
- Maintainability
- ERPNext best practices

## Deliverables

Please provide:

- Completed implementation within the ERPNext instance.
- Source code of any customizations created.
- Any custom scripts created.
- Any custom app code (if applicable).
- Exported customizations (if applicable).
- A brief explanation of their implementation.

## Candidate Reviews

This assessment simulates the type of work typically performed by an
ERPNext/Frappe developer in a production environment.

You are encouraged to use AI tools responsibly. We value candidates who can
understand business requirements, build maintainable solutions, verify
AI-generated output, and clearly explain their implementation decisions.

Producing clean, maintainable, and well-documented work is more important than
completing every feature.
