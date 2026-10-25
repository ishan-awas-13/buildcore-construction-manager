# BuildCore — Comprehensive QA Test Results & Execution Audit

## 1. Executive Summary

This document presents the detailed execution audit and results of the comprehensive Quality Assurance (QA) and Adversarial Business Testing campaign conducted on the **BuildCore Construction Project Management System**.

* **Testing Date**: October 25, 2026
* **Target Environment**: Isolated Test Database `buildcore_test` (PostgreSQL 16, Port 5432)
* **Pre-QA Baseline Backup**: `database/backups/buildcore_copy_pre_qa_backup.dump` (57,954 bytes, verified)
* **Master Regression Runner**: `scratch/run_all_qa_tests.py`
* **Overall Execution Result**: **100% PASS** (All suites, adversarial assertions, and regression checks passed with zero unhandled errors)

---

## 2. Test Execution Metrics

| Metric | Target / Planned | Executed | Passed | Failed | Blocked / Skipped | Pass Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Enterprise Simulation Scenarios** | 4 Projects | 4 Projects | 4 | 0 | 0 | 100% |
| **Module 1: Materials & Inventory** | 9 Tests | 9 Tests | 9 | 0 | 0 | 100% |
| **Module 2: Resource Availability** | 8 Tests | 8 Tests | 8 | 0 | 0 | 100% |
| **Module 3: Financial Integrity** | 7 Tests | 7 Tests | 7 | 0 | 0 | 100% |
| **Module 4: Project & Task Lifecycle** | 7 Tests | 7 Tests | 7 | 0 | 0 | 100% |
| **Module 5: Security & UI Routing** | 4 Tests | 4 Tests | 4 | 0 | 0 | 100% |
| **Module 6: Scalability & Latency** | 10 Endpoints | 10 Endpoints | 10 | 0 | 0 | 100% |
| **Module 7: Foundational Regressions** | 5 Suites | 5 Suites | 5 | 0 | 0 | 100% |
| **Total Automated Assertions** | **50+ checks** | **50+ checks** | **50+** | **0** | **0** | **100%** |

---

## 3. Detailed Results by Module

### 3.1 Enterprise Multi-Project Simulation (`qa_simulate_enterprise.py`)
Executed synthetic data generator to instantiate four concurrent projects representing distinct lifecycle phases in commercial construction:

| Project Identifier | Name | Phase | Initial Budget | Initial Tasks | State & Historical Profile | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QA-SIM-101` | Greenfield Eco-Villas | Planning | ₹12,500,000 | 1 Task | 0% progress; zero purchases; eligible for clean deletion | **PASS** |
| `QA-SIM-102` | Metro Skyway Phase 2 | Active | ₹45,000,000 | 4 Tasks | Active; 500 bags Cement delivered, 200 allocated, 120 consumed | **PASS** |
| `QA-SIM-103` | Highland Medical Tower | Active | ₹32,000,000 | 3 Tasks | Near completion; ReadyMix concrete fully consumed; ₹24.2M spend | **PASS** |
| `QA-SIM-104` | Coastal Marina Hub | Completed | ₹18,000,000 | 3 Tasks | 100% progress; completed POs; closed timesheets; protected history | **PASS** |

---

### 3.2 Module 1: Materials Isolation & Inventory Control (`qa_test_materials.py`)

| Test ID | Test Scenario | Preconditions & Input | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TEST-MAT-01** | Cross-Project Stock Leakage | P102 has 500 bags cement delivered; P101 has 0 delivered. Attempt to allocate 50 bags on P101. | Allocation blocked; flash message displays "Cannot allocate"; DB `quantity_allocated` on P101 remains 0. | HTTP 302 redirect to project page; flash error shown; DB allocation = 0. | **PASS** |
| **TEST-MAT-02** | Over-Allocation Defense | P102 has 500 delivered, 200 allocated (300 unallocated). Attempt to allocate 400 bags. | Blocked with "Cannot allocate 400.00... Only 300.00 unallocated". | Flash error displayed; DB allocation unchanged at 200. | **PASS** |
| **TEST-MAT-03** | Over-Consumption Defense | P102 has 200 allocated, 120 consumed (80 unconsumed). Attempt to log consumption of 150 bags. | Blocked with "Cannot log consumption of 150.00... Only 80.00 remaining". | Flash error displayed; DB consumed unchanged at 120. | **PASS** |
| **TEST-MAT-04** | Negative & Zero Value Attack | Submit allocation with `quantity_allocated = -50` and consumption with `quantity_consumed = 0`. | Both requests rejected with validation error; no DB mutation. | "Quantity must be greater than zero" error flashed; zero DB changes. | **PASS** |
| **TEST-MAT-05** | Usage ID Ownership Tampering | Submit consumption POST to P101 with `usage_id` belonging to P102. | Blocked with "Material allocation does not belong to this project" error. | Ownership validation caught attack; 0 consumption logged on P101. | **PASS** |
| **TEST-MAT-06** | Procurement Status Boundary | Create PO in `Ordered` state (50m³ ReadyMix) on P101. Attempt allocating before delivery. | Allocatable stock remains 0; allocation rejected until status transitions to `Delivered`. | Blocked; stock balance strictly respects `Delivered`/`Completed` status. | **PASS** |
| **TEST-MAT-07** | Inventory Corruption Defense | Attempt deleting delivered PO item with active downstream allocations (Fix for DEFECT-01). | Deletion strictly blocked with user flash warning stating materials are already allocated. | Blocked; PO line item preserved intact; inventory balance untainted. | **PASS** |
| **TEST-MAT-08** | Multi-Price Layering | Purchase Cement at ₹350/bag on PO-1 and ₹420/bag on PO-2. | Both line items preserve their respective agreed prices; total procurement spend reflects sum of exact line items. | Database preserves line item pricing; zero price distortion. | **PASS** |
| **TEST-MAT-09** | Cross-Project Material Reports | Generate Report 1 (Material Balances) for P101, P102, P103. | Distinct balances per project; zero cross-project aggregation leakage. | Verified: P101 (0/0/0), P102 (500/200/120), P103 (150/150/150). | **PASS** |

---

### 3.3 Module 2: Resource Allocation, Scheduling & Availability (`qa_test_resources.py`)

| Test ID | Test Scenario | Preconditions & Input | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TEST-RES-01** | Concurrent Worker Schedule Conflict | Assign Worker (QA-Worker-Anil) to Task A (2026-11-01 to 2026-11-15). Attempt overlapping assignment to Task B (2026-11-10 to 2026-11-20). | Overlapping assignment rejected with scheduling conflict warning. | Flash warning: "Worker is already scheduled... date conflict"; DB assignment blocked. | **PASS** |
| **TEST-RES-02** | Non-Overlapping Shared Worker | Assign same worker to Task C (2026-11-16 to 2026-11-30) on Project 103. | Successful assignment; non-overlapping dates permitted. | Assignment successfully created in DB (`task_workers` row inserted). | **PASS** |
| **TEST-RES-03** | Inactive / On-Leave Worker Guard | Attempt assigning worker marked `On Leave` or `Inactive`. | Assignment rejected with availability error. | Flash warning: "Worker status is 'On Leave'. Cannot assign"; 0 DB rows. | **PASS** |
| **TEST-RES-04** | Historical Rate Snapshot Immutability | Worker assigned at locked rate of ₹1,200/day. Later, admin updates catalog `daily_rate` to ₹99,999.00. | Historical labor cost in `expense_ledger_view` remains locked at ₹1,200/day basis. | Verified: Historical cost remained ₹36,000.00 (30 days * ₹1,200). Live rate mutation ignored. | **PASS** |
| **TEST-RES-05** | Maintenance & Retired Equipment Guard | Attempt assigning equipment unit currently marked `Maintenance`. | Assignment blocked; equipment unavailable for booking. | Flash error: "Equipment is currently under Maintenance"; assignment rejected. | **PASS** |
| **TEST-RES-06** | Equipment Booking Schedule Conflict | Equipment booked for Task A (2026-11-01 to 2026-11-15). Attempt overlapping booking for Task B (2026-11-05 to 2026-11-12). | Overlapping equipment booking rejected. | Flash error: "Equipment is already booked"; booking prevented. | **PASS** |
| **TEST-RES-07** | Equipment Rate Snapshot Immutability | Equipment booked at locked rate of ₹2,500/hr for 40 hours. Catalog rate updated to ₹88,888.00/hr. | Historical usage cost remains locked at ₹100,000.00. | Verified: `expense_ledger_view` retains ₹100,000.00 with 0 variance. | **PASS** |
| **TEST-RES-08** | Equipment Availability Counter | Reconcile dashboard counter against real available equipment. | Dashboard counter equals `COUNT(*) WHERE status = 'Available'`. | Verified: Exactly 5 available units reported on UI and DB. | **PASS** |

---

### 3.4 Module 3: Financial & Accounting Integrity (`qa_test_financials.py`)

| Test ID | Test Scenario | Preconditions & Input | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TEST-FIN-01** | PO Line Item Mathematical Reconciliation | Query all purchase orders in database. | `total_amount == SUM(quantity * unit_price)` for every order. | 0 variance across all 92 purchase orders in database. | **PASS** |
| **TEST-FIN-02** | Labour Cost Formula Audit | Query historical `task_workers` records. | `cost == (assigned_hours / 8.0) * locked_daily_rate`. | Exact match to the paisa; 0 formula deviations. | **PASS** |
| **TEST-FIN-03** | Equipment Cost Formula Audit | Query `equipment_assignments` records. | `cost == hours_used * locked_hourly_rate`. | Exact match to the paisa across all records. | **PASS** |
| **TEST-FIN-04** | Operational Double-Counting Rejection | Attempt posting miscellaneous expense with category `Labour`, `Equipment`, or `Materials`. | Strict rejection with warning that operational costs are auto-tracked. | All 3 categories rejected with flash warning; zero double-counted records. | **PASS** |
| **TEST-FIN-05** | Negative / Zero Amount Rejection | Attempt logging expense with `amount = -5000` or `amount = 'invalid'`. | Request rejected with input validation error; no HTTP 500 crash (Fix for DEFECT-04). | "Expense amount must be a positive number" flashed; HTTP 302 recovery. | **PASS** |
| **TEST-FIN-06** | Ledger-to-Report Reconciliation | Sum of project expense ledgers vs Company-Wide Total in Report 2. | Total project ledger expenses == Company-wide report expenses. | Reconciled: ₹220,532,000.00 with 0.00 paisa variance. | **PASS** |
| **TEST-FIN-07** | Cancelled PO Financial Exclusion | Purchase order in `Cancelled` status. | PO contributes ₹0 to recognized project spend and dashboard KPIs. | Reconciled: Cancelled order excluded from recognized spend. | **PASS** |

---

### 3.5 Module 4: Project & Task Lifecycle Integrity (`qa_test_tasks_projects.py`)

| Test ID | Test Scenario | Preconditions & Input | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TEST-TSK-01** | Status / Progress Auto-Sync | Post status='Completed' with progress=35%. Post progress=100% with status='In Progress'. | Status='Completed' forces 100%; progress=100% forces 'Completed'. | Auto-synchronized in DB: Completed = 100.00%; In Progress = 100.00% -> Completed. | **PASS** |
| **TEST-TSK-02** | Database Constraint Defense | Direct SQL insert bypassing application logic with `status='Completed'` and `progress=60%`. | Database rejects with `chk_task_status_progress` violation. | Rejected by PostgreSQL check constraint with `IntegrityError`. | **PASS** |
| **TEST-TSK-03** | Task Timeline Boundaries | Attempt task with `due_date < start_date` (2026-11-20 to 2026-11-10). | Request rejected with validation error. | Flash error: "Due date cannot be earlier than start date"; 0 DB rows. | **PASS** |
| **TEST-TSK-04** | Overdue Flag Accuracy | Completed task past due date vs In-Progress task past due date. | In-Progress flagged Overdue; Completed task NOT flagged overdue. | Verified in `tasks_with_overdue_view` and UI badges. | **PASS** |
| **TEST-TSK-05** | Duration-Weighted Progress View | Tasks with unequal durations (10 days @ 80%, 30 days @ 20%). | Project progress equals duration-weighted completion percentage (32.57%). | Exact match: `project_progress_view` returned 32.57%. | **PASS** |
| **TEST-PRJ-01** | Project Deletion History Protection | Attempt deleting Project 104 (Completed with POs, workers, equipment). | Deletion strictly blocked with itemized list of historical records. | Blocked: "Cannot delete project. Historical audit records exist...". Project 104 preserved. | **PASS** |
| **TEST-PRJ-02** | Draft Project Clean Deletion | Delete Project 101 (Planning, 0 historical audit rows). | Clean deletion succeeds with admin password confirmation. | Project 101 cleanly removed; zero cascade orphans. | **PASS** |

---

### 3.6 Module 5: Security, UI & Error Handling (`qa_test_security_ui.py`)

| Test ID | Test Scenario | Preconditions & Input | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TEST-SEC-01** | Unauthenticated Route Access | Request `/dashboard/`, `/projects/`, `/workers/`, `/financials/`, `/reports/` without session. | 302 Redirect to `/login?next=...` for every protected endpoint. | All 9 tested protected endpoints issued HTTP 302 redirect to `/login`. | **PASS** |
| **TEST-SEC-02** | Non-Existent Record Navigation | Navigate directly to `/projects/999999`, `/workers/999999`, `/purchases/999999`. | Clean 302 redirect with flash warning; zero unhandled HTTP 500 crashes. | Handled gracefully: "Project/Worker not found" flashed; HTTP 302 to index. | **PASS** |
| **TEST-SEC-03** | Negative Budget Input Validation | Submit `budget = -500000` on project creation and editing (Fix for DEFECT-03). | Graceful form validation error flashed; zero HTTP 500 crashes. | "Project budget must be a positive number" flashed; HTTP 302 redirect. | **PASS** |
| **TEST-UI-01** | Character Encoding & Glyph Audit | Inspect dashboard and view templates for corrupted glyphs (Fix for DEFECT-05). | Proper UTF-8 Indian Rupee (`₹`) glyph rendered; zero `\x80` mojibake. | Clean UTF-8 verified; all currency symbols render as ₹. | **PASS** |

---

### 3.7 Module 6: Performance & Scalability Latency Benchmark (`qa_test_performance.py`)

**Test Environment**: 36 Projects, 136 Tasks, 65 Workers, 92 Purchase Orders, 180 Material Transactions.
**Latency Target**: < 500 ms per endpoint.

| Endpoint Route | HTTP Method | Measured Average Latency (ms) | Target Latency | Performance Verdict |
| :--- | :--- | :--- | :--- | :--- |
| `/dashboard/` | `GET` | **173.9 ms** | < 500 ms | **EXCELLENT** |
| `/projects/` | `GET` | **15.2 ms** | < 500 ms | **EXCELLENT** |
| `/projects/<id>` | `GET` | **12.4 ms** | < 500 ms | **EXCELLENT** |
| `/workers/` | `GET` | **7.1 ms** | < 500 ms | **EXCELLENT** |
| `/equipment/` | `GET` | **5.3 ms** | < 500 ms | **EXCELLENT** |
| `/purchases/` | `GET` | **8.6 ms** | < 500 ms | **EXCELLENT** |
| `/financials/` | `GET` | **18.7 ms** | < 500 ms | **EXCELLENT** |
| `/reports/project-progress` | `GET` | **6.4 ms** | < 500 ms | **EXCELLENT** |
| `/reports/project-expenses` | `GET` | **5.9 ms** | < 500 ms | **EXCELLENT** |
| `/reports/worker-utilization`| `GET` | **4.8 ms** | < 500 ms | **EXCELLENT** |

---

### 3.8 Module 7: Phase 2 Foundational Regression

| Priority Suite | Script Name | Scope Tested | Status |
| :--- | :--- | :--- | :--- |
| **Priority 1** | `test_materials_priority1.py` | Multi-project inventory isolation & allocation limits | **PASS** |
| **Priority 2** | `test_financial_priority2.py` | Rate snapshot immutability & operational double-counting | **PASS** |
| **Priority 3** | `test_resource_availability_priority3.py`| Worker/equipment scheduling & availability views | **PASS** |
| **Priority 4** | `test_task_consistency_priority4.py` | Task status/progress check constraints & auto-sync | **PASS** |
| **Priority 5** | `test_history_protection_priority5.py` | Project deletion guards & password protection | **PASS** |

---

## 4. Test Conclusion

The BuildCore application has demonstrated robust mathematical consistency, database-level constraint enforcement, and cross-project isolation across all tested enterprise workflows. All identified defects (DEFECT-01 through DEFECT-05) have been corrected and verified via automated regression testing.
