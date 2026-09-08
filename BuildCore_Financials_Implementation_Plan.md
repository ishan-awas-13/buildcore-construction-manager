# BuildCore Financials Tab — Implementation Plan

## 1. Objective

Implement a **Financials** module/tab for the existing BuildCore Infrastructure construction management application.

The purpose is to answer:

> How much has each project spent, where is the money going, and how does total cost compare with the project budget?

The UI should provide one unified financial experience while preserving the existing normalized operational database design.

---

## 2. Inspect the Existing Application First

Before changing anything:

1. Inspect the complete repository.
2. Inspect the current PostgreSQL schema and actual data.
3. Inspect SQLAlchemy models and relationships.
4. Inspect existing purchase, purchase-item, material-usage, worker-assignment, equipment-assignment, and expense routes/templates.
5. Inspect the current Project Details page and navigation.
6. Inspect existing SQL views and financial calculations.
7. Search the codebase for all existing expense/cost calculations.
8. Do not create duplicate tables, routes, models, or calculations if equivalent functionality already exists.

This is an existing application. **Do not wipe or recreate the database.**

Preserve working functionality and make Financials fit the existing UI.

---

# 3. Financial Architecture — IMPORTANT

Do **not** create one giant physical `expenses` table containing materials, labour, equipment, and miscellaneous costs.

Instead, keep costs in the operational tables where they naturally originate and present them through one unified Financials module.

```text
                    PROJECT
                       |
        +--------------+--------------+
        |              |              |
    MATERIALS        LABOUR        EQUIPMENT
        |              |              |
 purchases +       task_workers   equipment_assignments
 purchase_items        |              |
        |              |              |
        +--------------+--------------+
                       |
                 FINANCIALS VIEW
                       |
              Unified Expense Ledger
                       |
                Financials UI
```

Recommended PostgreSQL view:

```text
expense_ledger_view
```

The exact implementation must be based on the actual existing schema after inspection.

---

# 4. Four Financial Categories

The Financials module consolidates:

1. **Materials**
2. **Labour**
3. **Equipment**
4. **Other / Miscellaneous**

---

## 5. Materials

### Source tables

- `purchases`
- `purchase_items`

Material procurement cost should come from purchase records.

Do **not** manually enter a material expense again inside Financials.

### IMPORTANT: Preserve Material Quantity Distinctions

The existing application already supports separate material concepts.

Keep these distinct:

```text
PURCHASED
ALLOCATED
USED
REMAINING
```

The existing `material_usage` structure contains:

- `quantity_allocated`
- `quantity_used`

Procurement is represented through:

- `purchases`
- `purchase_items`

Therefore:

### Purchased
How much material was bought through procurement.

### Allocated
How much material was allocated/reserved for a project.

### Used
How much material was actually consumed.

### Remaining

Where appropriate:

```text
Remaining = Allocated - Used
```

**Do not collapse purchased and used into the same amount.**

The Financials module should preserve the distinction.

### Important financial rule

Material quantity tracking and material financial cost are different concepts.

```text
Material Cost
    ↓
purchases + purchase_items
```

while:

```text
Material Usage
    ↓
quantity_allocated
quantity_used
```

Do not double-count material cost by treating material usage as another financial transaction.

---

# 6. Labour

## IMPORTANT DECISION: `assigned_hours` = ACTUAL HOURS WORKED

For this project, the existing:

```text
task_workers.assigned_hours
```

field will be treated as:

> **The actual number of hours the worker worked on that specific project task.**

Do **not** introduce a separate attendance/time-entry subsystem.

This is an intentional scope decision to keep the project manageable.

### Labour Cost

```text
Labour Cost =
(actual hours worked / 8) × worker daily rate
```

Example:

```text
Worker: Rajesh
Task: Bricklaying
Actual Hours Worked: 6
Daily Rate: ₹800

Labour Cost = (6 / 8) × 800
            = ₹600
```

The Financials UI should call this **Labour Cost** or **Actual Labour Cost**.

Do not describe these hours as planned or estimated hours.

The worker assignment remains tied to a specific `project_task`.

---

# 7. Equipment

### Source tables

- `equipment_assignments`
- `equipment`

Equipment cost:

```text
Equipment Cost =
hours_used × equipment hourly_rate
```

Example:

```text
Equipment: Excavator #3
Task: Foundation
Hours Used: 12
Hourly Rate: ₹1,500

Equipment Cost = 12 × 1,500
               = ₹18,000
```

Do not manually enter equipment costs into Financials.

---

# 8. Other / Miscellaneous Expenses

### Source

Existing:

```text
expenses
```

This remains the source for costs that do not naturally originate from materials, labour, or equipment.

Examples:

- Building permits
- Legal fees
- Safety testing
- Site fines
- Utilities
- Insurance
- Security
- Transportation/delivery charges
- Other miscellaneous project expenses

Keep/add standard CRUD for these expenses according to the existing schema.

---

# 9. Source-of-Truth Rule

This is critical.

Financial costs must originate automatically from operational modules.

### Materials

```text
Purchase
   ↓
Purchase Items
   ↓
Material Financial Cost
```

### Labour

```text
Worker
   ↓
Project Task
   ↓
Actual Hours Worked
   ↓
Labour Cost
```

### Equipment

```text
Equipment
   ↓
Project Task
   ↓
Hours Used
   ↓
Equipment Cost
```

### Other

```text
Miscellaneous Expense
   ↓
Other Financial Cost
```

There should be **no second manual financial entry** for materials, labour, or equipment.

---

# 10. Unified Financial Ledger

Create a unified financial representation for the UI.

Prefer a PostgreSQL view such as:

```text
expense_ledger_view
```

Use appropriate:

- `UNION ALL`
- joins
- aggregations
- `SUM()`
- `GROUP BY`

The view should expose information similar to:

| Field | Purpose |
|---|---|
| transaction_id | Source transaction identifier |
| project_id | Project |
| transaction_date | Date of cost |
| category | Materials / Labour / Equipment / Other |
| description | Human-readable description |
| amount | Financial amount |
| source_type | Purchase / Labour / Equipment / Misc Expense |
| source_id | Original source record |

Example:

```text
02 Sep | Materials  | Cement - 500 bags      | ₹42,500 | Purchase
03 Sep | Labour     | Rajesh - Bricklaying   | ₹600    | Labour
04 Sep | Equipment  | Excavator - Foundation | ₹18,000 | Equipment
05 Sep | Other      | Building Permit        | ₹25,000 | Misc Expense
```

Do not duplicate these transactions into a second physical expense table merely for display.

---

# 11. Project Financial Dashboard

Add a **Financials** entry/button from the Project Details page.

Example:

```text
Project: Chennai IT Park

[Overview] [Tasks] [Resources] [Financials]
```

The Financials page should be project-specific.

---

# 12. Financial Summary

At the top display:

### Total Budget

From the existing project budget.

### Total Cost

```text
Materials
+ Labour
+ Equipment
+ Other
```

### Remaining Budget

```text
Remaining Budget =
Project Budget - Total Cost
```

### Budget Used

```text
Budget Used % =
(Total Cost / Project Budget) × 100
```

Use a progress bar or similar visual.

Handle zero/null budgets safely so the application cannot crash from division by zero.

---

# 13. Category Breakdown

Show four cards/sections:

```text
MATERIALS        LABOUR        EQUIPMENT        OTHER
₹1,20,000        ₹80,000       ₹1,10,000       ₹30,000
```

The exact visual design should follow the existing BuildCore UI.

---

# 14. Visualization

If the existing frontend setup allows it cleanly, add a simple category breakdown chart.

Possible categories:

- Materials
- Labour
- Equipment
- Other

A pie/doughnut chart is acceptable.

The chart must use the same calculated values shown in the category cards.

Do not introduce a heavy frontend dependency solely for one chart unless justified.

---

# 15. Unified Transaction Table

Below the summary, display the financial ledger.

Suggested columns:

| Date | Category | Description | Amount | Source |
|---|---|---|---:|---|
| 02 Sep | Materials | Cement | ₹42,500 | Purchase |
| 03 Sep | Labour | Rajesh - Bricklaying | ₹600 | Labour |
| 04 Sep | Equipment | Excavator - Foundation | ₹18,000 | Equipment |
| 05 Sep | Other | Building Permit | ₹25,000 | Misc Expense |

Keep the table consistent with the existing application.

---

# 16. Filtering

If practical within the existing UI, provide:

- Category filter
- Date range
- Source type

At minimum, category filtering should be available if straightforward.

Filtering must not modify financial records.

---

# 17. Miscellaneous Expense CRUD

Maintain standard CRUD for the existing `expenses` table.

Users should be able to:

- Add miscellaneous expense
- View miscellaneous expenses
- Edit miscellaneous expense
- Delete miscellaneous expense where safe
- Associate it with a project
- Enter date
- Enter amount
- Enter expense type/category
- Enter description

Follow the actual existing schema rather than blindly assuming fields.

### Do NOT create a generic financial entry form

Do not make users manually choose:

```text
Material
Worker
Equipment
```

and type financial amounts.

That would create a risk of duplicate/double-counted costs.

Only miscellaneous expenses should be manually entered.

---

# 18. Task-Level Financial Context

The worker/equipment architecture now associates resources with specific project tasks.

Financial calculations should preserve this context.

The system should be able to show:

```text
Project
   ↓
Project Task
   ↓
Worker / Equipment
   ↓
Hours
   ↓
Cost
```

Example:

```text
Chennai IT Park
    └── Bricklaying
          ├── Rajesh — 6 hrs — ₹600
          └── Kumar  — 8 hrs — ₹800

    └── Foundation
          └── Excavator #3 — 12 hrs — ₹18,000
```

This makes Financials consistent with the resource-assignment architecture.

---

# 19. Financial Calculations

Use database-level calculations where practical.

### Labour

```text
(hours worked / 8) × daily_rate
```

### Equipment

```text
(hours_used) × hourly_rate
```

### Materials

```text
SUM(purchase_items.quantity × purchase_items.unit_price)
```

### Other

```text
SUM(expenses.amount)
```

### Total Project Cost

```text
Material Cost
+ Labour Cost
+ Equipment Cost
+ Other Cost
```

### Remaining Budget

```text
Budget - Total Project Cost
```

Use the actual existing column names and relationships after inspection.

---

# 20. Avoid Double Counting

Explicitly verify that costs cannot be counted twice.

### Correct

```text
Purchase cost → financial cost

Material usage → quantity/consumption tracking
```

### Incorrect

```text
Purchase cost
+
Material usage cost
```

when they represent the same financial transaction.

Likewise:

### Correct

```text
task_workers actual hours → labour cost
```

not:

```text
task_workers labour cost
+
manual labour expense
```

---

# 21. Database / SQL Requirements

Use PostgreSQL properly.

Where appropriate use:

- `SUM()`
- `GROUP BY`
- `JOIN`
- `UNION ALL`
- SQL views
- appropriate indexes
- suitable numeric types

Use SQLAlchemy consistently with the existing application.

Raw SQL through SQLAlchemy `text()` is acceptable where useful.

Do not replace PostgreSQL with SQLite.

Do not replace SQLAlchemy.

---

# 22. Validation

Add appropriate validation.

### Labour hours

- Numeric
- Non-negative
- Associated with a valid worker/project-task assignment

### Equipment hours

- Numeric
- Non-negative

### Purchase quantities/prices

- Non-negative
- Appropriate numeric precision

### Misc expenses

- Amount must not be negative
- Valid project
- Valid date

### Budget

Handle:

```text
budget = 0
budget = NULL
```

without crashing.

---

# 23. Existing Database / Historical Data

This is an existing application.

Before modifying anything:

1. Inspect existing data.
2. Do not delete the existing database.
3. Do not wipe seed/demo data unnecessarily.
4. Determine whether existing records participate correctly in the Financials calculations.
5. Preserve historical records.

If an existing record cannot safely participate in a calculation, handle it explicitly rather than inventing values.

---

# 24. UI/UX

Keep the existing BuildCore visual style.

Prioritize:

- Clean dashboard
- Clear monetary values
- Category breakdown
- Transaction history
- Useful filters
- Minimal unnecessary complexity
- Responsive Bootstrap-based layout if that is already used

Do not introduce React.

Do not rewrite the frontend architecture.

Do not redesign unrelated pages.

---

# 25. Suggested Page Layout

```text
========================================================
                  PROJECT FINANCIALS
                  Chennai IT Park
========================================================

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ TOTAL BUDGET │ │ TOTAL COST   │ │ REMAINING    │
│ ₹10,00,000   │ │ ₹3,40,000    │ │ ₹6,60,000    │
└──────────────┘ └──────────────┘ └──────────────┘

Budget Used
██████████░░░░░░░░░░ 34%

--------------------------------------------------------

MATERIALS        LABOUR        EQUIPMENT        OTHER
₹1,20,000        ₹80,000       ₹1,10,000       ₹30,000

--------------------------------------------------------

Cost Breakdown
[Chart]

--------------------------------------------------------

Financial Transactions

Filter: [All Categories ▼]  Date: [From] [To]

Date | Category | Description | Amount | Source
------------------------------------------------
...

========================================================
```

Antigravity may improve the visual design, but must preserve the underlying architecture and calculations.

---

# 26. Testing Requirements

After implementation, test at least:

### Test 1 — Material Cost

Create a purchase with multiple purchase items.

Verify:

```text
quantity × unit_price
```

is reflected correctly in Material Cost.

---

### Test 2 — Labour Cost

Record actual hours worked for a worker on a project task.

Verify:

```text
(hours / 8) × daily_rate
```

Example:

```text
8 hours × ₹800/day = ₹800
4 hours × ₹800/day = ₹400
```

---

### Test 3 — Equipment Cost

Verify:

```text
10 hours × ₹1,500/hour = ₹15,000
```

---

### Test 4 — Misc Expense

Add:

```text
Building Permit — ₹25,000
```

Verify it appears under Other.

---

### Test 5 — Total Cost

Verify:

```text
Materials
+ Labour
+ Equipment
+ Other
=
Total Cost
```

---

### Test 6 — Budget

Verify:

```text
Remaining = Budget - Total Cost
```

and the progress bar is correct.

---

### Test 7 — Zero Budget

Test a project with zero/null budget.

The page must not crash or divide by zero.

---

### Test 8 — Material Quantity Distinction

Verify that:

```text
Purchased
Allocated
Used
Remaining
```

remain distinct.

Verify that material usage does not create a second financial charge.

---

### Test 9 — No Duplicate Costs

Verify that purchases, worker hours, and equipment usage are not counted twice.

---

### Test 10 — Project Isolation

Verify that Project A's costs never appear in Project B's Financials page.

---

# 27. Final Success Criteria

The Financials module is successful when a manager can open a project and immediately see:

```text
PROJECT
   ↓
BUDGET
   ↓
TOTAL COST
   ↓
┌─────────────────────────────────┐
│ Materials                       │
│ Labour — actual hours worked    │
│ Equipment                       │
│ Other                           │
└─────────────────────────────────┘
   ↓
Remaining Budget
   ↓
Unified Financial Ledger
```

The database remains normalized while the UI provides one unified financial experience.

Most importantly:

> **Do not create a giant generic expenses table.**

Use the existing operational tables as sources of truth and consolidate them into the Financials view/dashboard.

---

# 28. Final Implementation Instruction

Proceed with implementation only after inspecting the existing BuildCore application and database.

Do not blindly assume table/column names.

Do not wipe the database.

Do not introduce unnecessary tables.

Do not add a worker attendance/time-entry subsystem.

Treat:

```text
task_workers.assigned_hours
```

as:

> **actual hours worked**

Preserve the distinction between:

```text
material purchased
material allocated
material used
material remaining
```

Keep Financials focused, polished, and consistent with the existing application.

After implementation, provide a concise implementation report containing:

1. Files created/modified
2. Database changes
3. SQL views/queries added
4. Financial calculation logic
5. UI changes
6. Validation added
7. Tests performed
8. Existing-data issues discovered
9. Assumptions made
10. Any unresolved issues
