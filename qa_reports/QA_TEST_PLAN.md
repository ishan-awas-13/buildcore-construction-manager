# BuildCore — Comprehensive QA Test Plan

## 1. Executive Summary & Purpose
This document outlines the master Quality Assurance (QA) and Adversarial Business Testing Plan for **BuildCore Infrastructure Manager**. Following the implementation of Phase 2 architectural corrections (Materials Isolation, Financial Consistency, Resource Availability, Task Consistency, and History Protection), this plan establishes an independent, adversarial verification protocol designed to evaluate whether BuildCore is robust, reliable, and production-safe for enterprise construction operations.

The objective is **not** to confirm happy-path assumptions, but to actively stress, interrogate, and attempt to break the system across boundary conditions, concurrent project isolations, financial accounting trails, and UI error-handling paths.

---

## 2. Test Environment & Safety Architecture

### 2.1 Database Isolation & Target Environment
Strict adherence to the database non-interference charter:
* **Production/Original DB (`buildcore`)**: STRICT READ-ONLY / FORBIDDEN. No test or script shall query or mutate this database.
* **Working DB (`buildcore_copy`)**: Preserved in its Phase 2 corrected state. Fresh verified backup created at `database/backups/buildcore_copy_pre_qa_backup.dump` (57,954 bytes).
* **Isolated QA Test DB (`buildcore_test`)**: A full, independent clone of `buildcore_copy` created specifically for adversarial testing. All destructive, edge-case, and high-volume test operations execute exclusively against `buildcore_test`.

### 2.2 Application Execution Architecture
* **Web UI Server (Port 5001)**: Flask application instance pointed to `buildcore_test` for browser-based automation and manual employee workflow walkthroughs.
* **Programmatic Test Harness**: Python-based test runner executing via Flask `test_client()` and raw `psycopg2` transactional assertions against `buildcore_test`.
* **Zero Contamination**: Clean-up scripts only operate within `buildcore_test`.

---

## 3. Business Simulation Scope: Multi-Project Construction Enterprise

The test harness models an active commercial contractor managing concurrent infrastructure projects across various lifecycle stages:

| Project Key | Project Name | Status | Lifecycle State | Planned Budget | Scope & Historical Profile |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PRJ-101** | *Greenfield Eco-Villas* | `Planning` | Barely Started | ₹12,500,000 | Newly created; 1 planning task; zero purchases; 0% progress; eligible for clean deletion. |
| **PRJ-102** | *Metro Skyway Phase 2* | `Active` | Mid-Construction | ₹45,000,000 | 4 active tasks; multiple worker & equipment assignments; delivered & pending POs; active material consumption. |
| **PRJ-103** | *Highland Medical Tower* | `Active` | Near Completion | ₹32,000,000 | 3 tasks (2 completed, 1 at 95%); high material consumption; extensive timesheets; near budget ceiling. |
| **PRJ-104** | *Coastal Marina Hub* | `Completed` | Post-Handover / Audit | ₹18,000,000 | 100% completed; closed POs; full historical timesheets; immutable financial records; protected from deletion. |

---

## 4. Test Modules & Scenario Matrix

### Module 1: Multi-Project Material & Inventory Isolation (Adversarial)
* **TEST-MAT-01: Cross-Project Stock Leakage**: Purchase 500 bags of Cement on PRJ-102. Verify PRJ-101 and PRJ-103 show 0 available stock and cannot allocate from PRJ-102.
* **TEST-MAT-02: Over-Allocation Defense**: Attempt to allocate 600 units when only 500 are delivered. Verify request is rejected with clear error.
* **TEST-MAT-03: Over-Consumption Defense**: Attempt to consume 250 units when only 200 are allocated. Verify strict rejection.
* **TEST-MAT-04: Negative & Zero Value Attack**: Attempt allocating/consuming negative (`-50`) or zero (`0`) quantities via POST form submission.
* **TEST-MAT-05: Cross-Project Usage ID Tampering**: Submit a consumption request to PRJ-101 using a `usage_id` belonging to PRJ-102. Verify ownership mismatch rejection.
* **TEST-MAT-06: Procurement Status Boundary**: Create purchase orders in `Ordered`, `Shipped`, `Delivered`, `Completed`, and `Cancelled` states. Verify ONLY `Delivered` and `Completed` orders increase allocatable stock and appear on financial ledgers.
* **TEST-MAT-07: Purchase Modification & Inventory Corruption**: Attempt deleting or cancelling a purchase item after materials have already been allocated/consumed. Verify system prevents or flags inventory corruption.
* **TEST-MAT-08: Multi-Price Purchase Layering**: Purchase same material at different prices (e.g. ₹350/bag then ₹420/bag). Verify financial ledger accurately reflects actual purchase cost rather than catalog cost.

### Module 2: Resource Allocation, Scheduling & Availability (Adversarial)
* **TEST-RES-01: Concurrent Worker Conflict**: Assign Worker W to Task A on PRJ-102 (Dates: Nov 1 to Nov 15). Attempt assigning W to Task B on PRJ-103 with overlapping dates (Nov 10 to Nov 20). Verify collision rejection.
* **TEST-RES-02: Non-Overlapping Cross-Project Sharing**: Assign Worker W to Task C (Dates: Nov 16 to Nov 30). Verify assignment succeeds.
* **TEST-RES-03: Inactive & On-Leave Worker Guard**: Attempt assigning worker with status `On Leave` or `Inactive`. Verify rejection.
* **TEST-RES-04: Date Range Boundary (Same Day)**: Worker assigned to Task ending Nov 15; new task starting Nov 15 or Nov 16. Verify boundary schedule logic.
* **TEST-RES-05: Rate Snapshot Immutability**: Worker assigned at historical locked rate of ₹850/day. Later, admin changes catalog daily rate to ₹1,200/day. Verify historical assignment and financial ledger retain ₹850/day.
* **TEST-RES-06: Equipment Maintenance & Retired Guard**: Attempt assigning equipment currently marked `Maintenance` or `Retired`. Verify strict rejection.
* **TEST-RES-07: Equipment Overlapping Booking Guard**: Attempt double-booking equipment across overlapping dates. Verify rejection.
* **TEST-RES-08: Equipment Availability View**: Verify dashboard equipment counter matches count of truly available equipment.

### Module 3: Financial & Accounting Integrity (Adversarial)
* **TEST-FIN-01: Purchase Order Mathematical Reconciliation**: Verify line items `(quantity * unit_price)` strictly sum to PO total amount.
* **TEST-FIN-02: Labour Cost Formula Audit**: Independently calculate `(assigned_hours / 8.0) * locked_daily_rate` and verify against `expense_ledger_view` and Report 3.
* **TEST-FIN-03: Equipment Cost Formula Audit**: Independently calculate `hours_used * locked_hourly_rate` and verify against ledger and Report 3.
* **TEST-FIN-04: Operational Double-Counting Prevention**: Attempt adding miscellaneous expense with category `Labour`, `Equipment`, or `Materials`. Verify rejection.
* **TEST-FIN-05: Negative & Excessive Expense Injections**: Attempt logging negative expense (`-₹50,000`) or extreme overflow numbers. Verify validation.
* **TEST-FIN-06: Ledger-to-Report Reconciliation**: Verify that the sum of project ledger expenses across all individual projects exactly equals the company-wide total cost in Report 2.
* **TEST-FIN-07: Cancelled & Draft Order Exclusion**: Verify `Cancelled` purchase orders contribute ₹0 to expenses and ₹0 to dashboard purchase totals.

### Module 4: Project & Task Lifecycle Integrity (Adversarial)
* **TEST-TSK-01: Status vs Progress Auto-Synchronization**:
  * Set status to `Completed` with 50% progress -> Progress must auto-sync to 100%.
  * Set progress to `100%` with status `In Progress` -> Status must auto-sync to `Completed`.
  * Set status to `Not Started` with progress `25%` -> Status must auto-sync to `In Progress`.
* **TEST-TSK-02: Database Check Constraint Enforcement**: Direct SQL insert bypassing application layer with invalid status/progress. Verify database rejects with check constraint violation.
* **TEST-TSK-03: Task Date Timeline Boundaries**: Attempt assigning task with `start_date > due_date` or outside the project's start/end dates. Verify rejection.
* **TEST-TSK-04: Overdue Logic Audit**: Verify tasks past due date with status != 'Completed' are flagged overdue, while completed past-due tasks are NOT overdue.
* **TEST-TSK-05: Project Progress Aggregation**: Verify project progress view computes exact mathematical average of assigned tasks. Verify behavior when project has 0 tasks.
* **TEST-PRJ-01: History Protection on Project Deletion**:
  * Attempt deleting PRJ-104 (Completed, with historical POs, workers, equipment). Verify rejection with itemized audit trail reasons.
  * Attempt deleting PRJ-102 (Active, with transactions). Verify rejection.
  * Delete PRJ-101 (Planning, zero history). Verify successful clean deletion.
* **TEST-PRJ-02: Admin Password Verification on Deletion**: Attempt deleting eligible project with wrong admin password. Verify rejection.

### Module 5: UI, Routing, Error Handling & Security Boundary
* **TEST-SEC-01: Unauthenticated Endpoint Access**: Attempt accessing `/dashboard/`, `/projects/`, `/workers/`, `/financials/`, `/reports/` without session. Verify 302 redirect to `/login`.
* **TEST-SEC-02: Non-Existent Record Navigation (404/Flash)**: Navigate directly to `/projects/999999`, `/workers/999999`, `/purchases/999999`. Verify application gracefully flashes error without unhandled HTTP 500 crash.
* **TEST-UI-01: Character Encoding & Formatting**: Inspect dashboard and views for character glitches (e.g. currency symbols). Verify proper Indian Rupee (`₹`) formatting.

### Module 6: Performance & Enterprise Scalability
* **TEST-PERF-01: High-Volume Dataset Generation**: Ingest synthetic dataset of 25 projects, 150 tasks, 50 workers, 25 equipment units, 100 purchase orders, and 200 material usage rows.
* **TEST-PERF-02: Query Latency Profiling**: Measure load times for `/dashboard/`, `/projects/`, `/financials/`, and `/reports/` under synthetic load. Target: < 500ms per view.
* **TEST-PERF-03: N+1 Query Audit**: Profile SQL execution count per request.

### Module 7: Regression of Existing Phase 2 Test Suites
* **TEST-REG-01**: Execute all 5 foundational test suites against `buildcore_test`. Verify 100% pass rate.

---

## 5. Defect Severity & Classification Rubric

* **Critical**: Silent data corruption, cross-project data leakage, unauthorized data deletion, or unhandled crash preventing core operations.
* **High**: Materially incorrect financial/cost calculations, broken resource collision detection, invalid inventory reconciliation, or constraint bypass.
* **Medium**: Recoverable workflow defect, misleading report presentation, non-blocking UI validation omission, or missing redirect.
* **Low**: Cosmetic visual flaw, character encoding glitch, or minor formatting imperfection.

---

## 6. Execution Protocol & Verification Artifacts
1. **Automation Test Suites**: Python scripts executing structured batches with assert-level validation.
2. **Interactive UI Walkthrough**: Headless browser automation verifying real form submissions, modals, alerts, and navigation.
3. **Database Assertion Logs**: SQL snapshots before and after state transitions.
4. **Deliverables Generation**: All test results, defect records, data integrity reconciliations, and regression logs saved to `qa_reports/`.
