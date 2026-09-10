# BuildCore — Financials & Data Integrity Hardening Plan

## Purpose

You are working on the **BuildCore Infrastructure Pvt. Ltd. — Construction Project Resource Management System**.

The Financials module and unified `expense_ledger_view` have already been implemented. Do **not** rebuild the Financials module from scratch.

Perform a focused hardening pass that fixes correctness, integrity, and security issues while preserving the existing architecture and UI.

Repository:
`https://github.com/ishan-awas-13/buildcore-construction-manager`

---

## 1. Inspect Before Changing Anything

First inspect the current repository and implementation, especially:

- `routes/financials.py`
- `templates/financials/*`
- database schema / SQL files
- current `expense_ledger_view`
- purchase routes/templates
- worker assignment routes/templates
- equipment assignment routes/templates
- material routes/templates
- authentication/user creation code

Do not assume the previous implementation still matches the repository.

### Critical safety rules

- Preserve working functionality.
- **Do NOT wipe, truncate, or rebuild the database.**
- Do not replace the normalized financial architecture with a generic expenses table.
- Do not make destructive schema/data changes without a safe migration.

---

# 2. Financial Architecture — KEEP THIS

The current architecture is intentional:

```text
Purchases + Purchase Items ──→ Material Costs
Task Workers ────────────────→ Labour Costs
Equipment Assignments ───────→ Equipment Costs
Misc Expenses ───────────────→ Other Costs

                    ↓

             expense_ledger_view

                    ↓

             Financials UI
```

The ledger must remain a **database VIEW**, not a duplicated physical transaction table.

The existing source-of-truth tables remain authoritative.

Do not create duplicate financial records merely to make the Financials page easier to query.

---

# 3. FIX #1 — Cancelled Purchases Must NOT Become Project Costs

## Problem

The material branch of `expense_ledger_view` currently reads purchase items without adequately filtering purchase status.

A cancelled purchase must never contribute to:

- Material financial cost
- Total project cost
- Budget utilization
- Remaining budget
- Material category totals
- Financials ledger

## Required behavior

For the current project, treat **Delivered** and **Completed** purchase orders as actual material expenditure.

Do not count:

```text
Pending
Approved
Shipped
Cancelled
```

as actual expenditure.

Count:

```text
Delivered
Completed
```

as actual expenditure.

Use the exact status values/casing already used by the database.

## Implementation

Update `expense_ledger_view` so the material branch applies the correct status filter.

Conceptually:

```sql
FROM purchase_items pi
JOIN purchases p ON pi.purchase_id = p.purchase_id
...
WHERE p.status IN ('Delivered', 'Completed')
```

Inspect the real schema first and adapt this to the exact implementation.

Do not modify historical purchase records just to make the view work.

## Validation

Test with purchases in every status:

- Pending
- Approved
- Shipped
- Delivered
- Completed
- Cancelled

Verify only Delivered + Completed appear as material financial costs.

Verify project totals and budget utilization update accordingly.

---

# 4. FIX #2 — Remove the Hardcoded `admin/admin` Credential Problem

## Problem

The repository currently has an administrative setup path using the literal password:

```text
admin
```

The repository is public, so this must be removed from normal setup.

The existing Flask-Login and Werkzeug password hashing approach should remain.

## Required behavior

The CLI command may remain, but it must no longer silently create/overwrite an administrator using a known hardcoded password.

Preferred flow:

```text
flask create-admin
```

then securely prompt:

```text
Username: admin
Password:
Confirm password:
```

Use Python's `getpass` or another secure interactive mechanism.

The password must continue to be stored only as a Werkzeug password hash.

## Do NOT

- print the password
- commit a plaintext password
- put a password in source code
- silently reset the admin password every time setup runs

If a seed/demo SQL file contains a pre-hashed admin credential, inspect whether it is required. Prefer removing hardcoded credentials from normal setup. If a demo-only seed credential must remain for some reason, document it clearly and ensure normal setup does not depend on a publicly known password.

## Regression tests

Verify:

1. `flask create-admin` works.
2. Password is hashed.
3. Login works with the supplied password.
4. Wrong password is rejected.
5. Password is not printed.
6. Existing login/logout behavior remains intact.

---

# 5. LABOUR COST MODEL — DO NOT OVERENGINEER

The project intentionally uses:

```text
task_workers.assigned_hours
```

as the **actual hours worked recorded for that worker-task assignment**.

The calculation is:

```text
Labour Cost = actual hours worked / 8 × worker daily rate
```

Preserve this model.

Do NOT introduce:

- attendance system
- timesheet subsystem
- `worker_time_entries` table
- daily attendance calendar

for this fix.

## Terminology

This is an assignment-level actual-hours record, not a daily timesheet.

If the current UI says only:

```text
Assigned Hours
```

consider changing the label to:

```text
Actual Hours Worked
```

or:

```text
Hours Worked
```

Do not rename the database column unless genuinely necessary.

Do not create fake daily labour transactions.

---

# 6. EQUIPMENT COST MODEL — KEEP IT SIMPLE

The current model uses:

```text
equipment_assignments.hours_used
equipment.hourly_rate
```

with:

```text
Equipment Cost = hours_used × hourly_rate
```

Preserve this.

The ledger may continue using the assignment's existing relevant date as the transaction date.

The ledger represents the cost associated with an equipment assignment, not a daily accounting journal.

Do not introduce daily equipment timesheets.

---

# 7. MATERIAL DATA MODEL — PRESERVE THE DISTINCTION

Do NOT collapse material procurement and material usage.

Keep the distinction:

```text
Purchased
Allocated
Used
Remaining
```

Source tables:

```text
purchases + purchase_items
        ↓
procurement

material_usage
        ↓
allocation / consumption
```

Financial material cost comes from actual procurement records.

Material usage must NOT create another financial charge.

## Add reasonable integrity validation

Inspect material allocation/update functionality.

Prevent impossible values:

```text
quantity_allocated >= 0
quantity_used >= 0
quantity_used <= quantity_allocated
```

If practical within the current architecture, also prevent allocation from exceeding available purchased quantity.

Do not create a complicated warehouse/inventory subsystem.

Backend validation is required; do not rely only on HTML validation.

Use database constraints where they naturally fit.

---

# 8. RESOURCE ASSIGNMENT — HARDEN EXISTING LOGIC

The intended rule is:

```text
Resource → Project → Specific Project Task
```

A worker/equipment allocation must never be a void allocation with no task.

## Worker assignment

Verify:

- `project_task_id` is required.
- Submitted task exists.
- Worker exists.
- Assignment is valid for the selected project/task.
- `assigned_hours >= 0`.
- Obvious duplicate/impossible assignments are handled reasonably.
- Historical assignments are preserved.

If foreign keys already enforce existence, do not duplicate that unnecessarily; add business-rule validation where needed.

## Equipment assignment

Verify:

- `project_task_id` is required.
- `start_date` is required.
- `hours_used >= 0`.
- Equipment exists.
- Task exists.
- Assignment is valid.
- Obvious overlapping active assignments are prevented if the current model requires equipment to be in only one place at a time.

Do not build a large scheduling subsystem.

---

# 9. PREVENT FINANCIAL DOUBLE COUNTING

The unified ledger should have exactly these sources:

| Category | Source |
|---|---|
| Materials | `purchases` + `purchase_items` |
| Labour | `task_workers` |
| Equipment | `equipment_assignments` |
| Other | `expenses` |

Do NOT automatically insert operational costs into `expenses`.

Example:

```text
Equipment assignment = ₹20,000
```

must not produce both:

```text
Equipment = ₹20,000
Other = ₹20,000
```

Only genuinely miscellaneous costs belong in `expenses`.

---

# 10. LEDGER VIEW SAFETY

After modification, inspect the complete definition of:

```text
expense_ledger_view
```

Verify:

1. It is still a VIEW.
2. It uses the intended normalized source tables.
3. `UNION ALL` or an equivalent consolidation is correct.
4. All branches return compatible columns/types.
5. Project IDs and names are correct.
6. Category names are consistent.
7. Amounts are numeric and sensible.
8. Cancelled purchases are excluded.
9. Source transactions are not duplicated.
10. Existing Financials filters still work.

Do not replace the view with a duplicated physical expense table.

---

# 11. BUDGET CALCULATIONS

Verify:

```text
Total Cost
= Materials + Labour + Equipment + Other
```

```text
Remaining Budget
= Project Budget - Total Cost
```

```text
Budget Used %
= Total Cost / Project Budget × 100
```

Check:

- zero costs
- zero budget, if allowed by schema
- cost below budget
- cost equal to budget
- cost above budget
- project with no transactions

Cancelled purchases must not affect any of these totals.

---

# 12. INPUT VALIDATION PASS

While working on the affected modules, fix obvious correctness problems involving:

- negative monetary amounts
- negative quantities
- negative hours
- missing required foreign keys
- invalid IDs
- impossible dates
- malformed numeric input

Do not turn this into a massive security rewrite.

Continue using parameterized SQL such as:

```sql
WHERE id = :id
```

rather than string interpolation.

---

# 13. DATABASE SAFETY

**CRITICAL:**

Do not run destructive commands such as:

```sql
TRUNCATE ...
DROP TABLE ...
DROP DATABASE ...
DELETE FROM ...
```

against the user's existing working database.

If a view must be recreated, use a safe migration/update approach.

Existing data must be preserved.

---

# 14. REQUIRED TESTING

Perform an end-to-end sanity check after implementation.

## Test A — Purchase status

Expected:

```text
Pending     → not counted
Approved    → not counted
Shipped     → not counted
Delivered   → counted
Completed   → counted
Cancelled   → not counted
```

## Test B — Labour

Example:

```text
Daily rate = ₹800
Hours worked = 8
Expected = ₹800
```

```text
Daily rate = ₹800
Hours worked = 4
Expected = ₹400
```

## Test C — Equipment

```text
Hourly rate = ₹1,500
Hours used = 10
Expected = ₹15,000
```

## Test D — Miscellaneous

```text
Other expense = ₹5,000
Expected Other = ₹5,000
```

## Test E — Material quantity integrity

Verify:

```text
allocated >= 0
used >= 0
used <= allocated
```

## Test F — Budget

Verify Financials correctly updates:

```text
Total Cost
Remaining Budget
Budget Used %
```

after adding/removing valid transactions.

## Test G — Double counting

Create one valid example of each category and verify:

```text
Grand Total = Material + Labour + Equipment + Other
```

with no duplicate contribution.

## Test H — Authentication

Verify:

```text
correct password → login succeeds
wrong password → login fails
logout → protected pages require login
```

Also verify no password is printed or stored in plaintext.

---

# 15. DOCUMENTATION

Update relevant documentation where necessary.

Clearly document:

### Labour

```text
task_workers.assigned_hours represents actual hours worked recorded for the worker-task assignment.

Labour cost = actual hours worked / 8 × worker daily rate.
```

### Equipment

```text
Equipment cost = hours_used × hourly_rate.
```

### Materials

```text
Procurement and usage are separate.
Financial cost comes from actual purchase records.
Purchased, allocated, used, and remaining quantities are tracked separately.
```

### Ledger

```text
expense_ledger_view is a unified database VIEW that presents financial costs from normalized operational tables without duplicating the underlying transactions.
```

---

# 16. FINAL REPORT

When finished, report:

1. Files changed.
2. Database objects changed.
3. Exact fixes made.
4. Assumptions made.
5. Tests performed.
6. Test results.
7. Any remaining known limitations.

Do not simply say "implemented successfully."

Give a concise technical summary.

---

# 17. DEFINITION OF DONE

The task is complete only when:

- [ ] Financials architecture remains intact.
- [ ] `expense_ledger_view` remains a database VIEW.
- [ ] Cancelled purchases do not contribute to financial totals.
- [ ] Only intended purchase statuses contribute to actual material cost.
- [ ] Labour uses actual hours worked.
- [ ] Labour remains `hours / 8 × daily_rate`.
- [ ] Equipment remains `hours_used × hourly_rate`.
- [ ] Material purchased/allocated/used/remaining distinction remains intact.
- [ ] Impossible material quantities are rejected.
- [ ] Worker/equipment assignments require a specific project task.
- [ ] Negative hours/quantities are rejected.
- [ ] Financial categories are not double-counted.
- [ ] Budget calculations remain correct.
- [ ] Hardcoded `admin/admin` credential is removed from normal setup.
- [ ] Admin passwords are never printed or stored in plaintext.
- [ ] Login/logout still works.
- [ ] Existing data is preserved.
- [ ] No destructive database reset is performed.
- [ ] Relevant documentation is updated.
- [ ] End-to-end sanity tests pass.

## Most Important Instruction

**Do not overengineer.**

This is a 3rd-year DBMS academic project. Fix correctness, integrity, security, and obvious anomalies while keeping the current architecture understandable and demonstrable.

Do not introduce unnecessary subsystems such as attendance, timesheets, inventory management, accounting journals, or complex scheduling merely to solve small edge cases.

**Preserve what already works.**
