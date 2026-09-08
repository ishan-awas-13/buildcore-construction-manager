# BuildCore DB — Dynamic Resource Assignment & Status Engine

## OBJECTIVE

Modify the existing BuildCore DB application and PostgreSQL database so that worker and equipment assignments are fully consistent and cannot exist as vague "project-only" allocations.

Every active worker/equipment allocation must be associated with a **specific project task**.

The intended resource flow is:

    PROJECT
       ↓
    PROJECT TASK
       ↓
    WORKER / EQUIPMENT

Example:

    Worker: Rajesh
    Project: Chennai IT Park
    Task: Bricklaying

NOT:

    Worker: Rajesh
    Project: Chennai IT Park

without specifying what task Rajesh is performing.

The same principle applies to equipment.

---

# 1. INSPECT THE EXISTING PROJECT FIRST

Before modifying anything:

- Inspect the complete existing project structure.
- Inspect the current PostgreSQL schema.
- Inspect SQLAlchemy models.
- Inspect existing migrations, if any.
- Inspect worker assignment routes/forms/templates.
- Inspect equipment assignment routes/forms/templates.
- Inspect project/task routes and templates.
- Inspect `project_tasks`.
- Inspect `task_workers`.
- Inspect `equipment_assignments`.
- Search the entire codebase for worker/equipment status and assignment logic.
- Identify all places where "Assigned" or "In Use" is hardcoded or manually selected.

Do not blindly create duplicate models, tables, routes, or forms.

First understand the existing implementation and preserve working functionality wherever possible.

---

# 2. CORE DESIGN PRINCIPLE

A resource is not meaningfully "assigned" merely because it is associated with a project.

Every active assignment must identify:

1. The resource
2. The project
3. The specific project task
4. The assignment period where applicable

Worker relationship:

    WORKER
       ↓
    TASK_WORKERS
       ↓
    PROJECT_TASK
       ↓
    PROJECT

Equipment relationship:

    EQUIPMENT
       ↓
    EQUIPMENT_ASSIGNMENTS
       ↓
    PROJECT_TASK
       ↓
    PROJECT

The database must be able to answer:

> Who is working on what task, in which project?

and:

> What equipment is being used for what task, in which project?

---

# 3. WORKER ASSIGNMENT

The worker allocation flow must NOT allow:

    Worker → Project

as a complete assignment.

It must require:

    Worker → Project → Task

Example UI:

    Assign Worker

    Worker:
    [Rajesh]

    Project:
    [Chennai IT Park]

    Task:
    [Bricklaying]

    Assigned Hours:
    [8]

    Start Date:
    [01/09/2026]

    Release Date:
    [optional]

The selected task must belong to the selected project.

The backend must validate this as well.

Do NOT rely only on frontend dropdown filtering.

---

# 4. TASK_WORKERS TABLE

The worker/task relationship must reference the project-specific task.

Relevant structure should contain at minimum:

    task_worker_id       PRIMARY KEY
    project_task_id      FOREIGN KEY → project_tasks.project_task_id
    worker_id            FOREIGN KEY → workers.worker_id
    assigned_hours
    assigned_date
    release_date

If the existing schema already contains equivalent fields, preserve them where appropriate.

The critical requirement is:

    task_workers.project_task_id

must identify the exact project-specific task.

For example:

    Rajesh
      → Bricklaying
      → Chennai IT Park

must be different from:

    Rajesh
      → Bricklaying
      → Green Heights

---

# 5. WORKER STATUS

Worker status must be derived from actual assignments rather than manually setting "Assigned".

Use the base worker table for genuine manual states such as:

- Available
- On Leave
- Inactive

Do NOT allow users to manually select:

- Assigned

`Assigned` should be dynamically computed when the worker has an active project-task assignment.

Conceptually:

    If worker is On Leave → On Leave
    If worker is Inactive → Inactive
    If worker has an active task assignment → Assigned
    Otherwise → Available

---

# 6. WORKER STATUS VIEW

Create/update a SQL view such as:

    worker_status_view

It should expose worker information plus:

    computed_status

The active assignment check should use `task_workers` joined with `project_tasks`.

An assignment should count as active only when the relevant project-task assignment is active/valid according to the application's status and assignment dates.

Do not consider a worker assigned merely because a historical assignment exists.

The view should conceptually implement:

    MANUAL STATE
        ↓
    On Leave / Inactive

    otherwise

    ACTIVE PROJECT-TASK ASSIGNMENT
        ↓
    Assigned

    otherwise

    Available

---

# 7. WORKER FORM CONSTRAINTS

Update Worker Add/Edit forms.

Users must NOT be able to manually choose:

    Assigned

The form should only allow appropriate manual states such as:

    Available
    On Leave
    Inactive

Displayed worker status should use the computed status where assignment state matters.

---

# 8. EQUIPMENT ASSIGNMENT

Apply the same principle to equipment.

The system must NOT allow:

    Equipment → Project

as a complete allocation.

It must require:

    Equipment → Project → Task

Example:

    Equipment:
    Excavator #3

    Project:
    Chennai IT Park

    Task:
    Foundation

    Start Date:
    01/09/2026

    End Date:
    15/09/2026

    Hours Used:
    120

The selected task must belong to the selected project.

The backend must validate this relationship.

---

# 9. EQUIPMENT_ASSIGNMENTS TABLE

Update equipment assignments so they reference the specific project task.

Relevant structure should contain at minimum:

    assignment_id
    equipment_id       FOREIGN KEY → equipment.equipment_id
    project_task_id    FOREIGN KEY → project_tasks.project_task_id
    start_date
    end_date
    hours_used

The critical requirement is:

    equipment_assignments.project_task_id

rather than only:

    equipment_assignments.project_id

The project can be obtained through:

    equipment_assignments
        → project_tasks
        → projects

If the existing table currently contains `project_id`, determine whether it is redundant after migration and remove it only after safely migrating existing data.

Do not maintain duplicate project references unless there is a clear reason.

---

# 10. EQUIPMENT STATUS

Equipment status must be dynamically derived.

Manual states may include:

- Available
- Maintenance
- Retired

Users must NOT manually select:

- In Use

`In Use` should be computed from active equipment assignments.

Conceptually:

    If equipment is Maintenance → Maintenance
    If equipment is Retired → Retired
    If equipment has an active project-task assignment → In Use
    Otherwise → Available

---

# 11. EQUIPMENT STATUS VIEW

Create/update:

    equipment_status_view

The view should expose:

    equipment information
    +
    computed_status

An equipment item should be considered "In Use" only when it has a currently active assignment.

Use assignment dates:

    start_date <= CURRENT_DATE

and:

    end_date IS NULL
    OR end_date >= CURRENT_DATE

Do not let an old/historical assignment keep equipment marked as "In Use".

---

# 12. EQUIPMENT FORM CONSTRAINTS

Update Equipment Add/Edit forms.

Users must NOT be able to manually select:

    In Use

Manual equipment states should be limited to:

    Available
    Maintenance
    Retired

The application should derive "In Use" from actual assignments.

---

# 13. PROJECT → TASK VALIDATION

This is extremely important.

When assigning a worker or equipment item:

1. User selects a project.
2. UI loads the project-specific tasks belonging to that project.
3. User selects one of those tasks.
4. Backend verifies that the selected `project_task_id` actually belongs to the selected project.
5. Only then should the assignment be created.

Never trust the frontend alone.

The backend must reject invalid combinations such as:

    Project = Chennai IT Park
    Task = Bricklaying belonging to Green Heights

---

# 14. TASK SELECTION UI

For worker and equipment assignment forms, use a dependent selection flow.

Example:

    Project:
    [Chennai IT Park ▼]

    Task:
    [Select a task ▼]

After selecting a project, show only its project-specific tasks.

Example:

    Project: Chennai IT Park

    Task:
    [Foundation]
    [Bricklaying]
    [Electrical Installation]
    [Painting]

Do not show tasks belonging to unrelated projects.

If the selected project has no tasks, clearly tell the user that a project task must be created before a worker/equipment resource can be assigned.

---

# 15. PREVENT VOID ALLOTMENTS

The system must prevent these invalid states:

### Invalid Worker Assignment

    Rajesh
    → Chennai IT Park
    → NO TASK

### Invalid Equipment Assignment

    Excavator
    → Chennai IT Park
    → NO TASK

These must not be creatable through the UI or backend.

Every active allocation must identify a valid `project_task_id`.

---

# 16. ASSIGNMENT DATE LOGIC

Worker assignments should support:

    assigned_date
    release_date

Equipment assignments should support:

    start_date
    end_date

The system must distinguish active assignments from historical assignments.

For example:

    Rajesh
    → Bricklaying
    → Chennai IT Park
    → 01/08/2026 to 15/08/2026

should NOT make Rajesh appear currently "Assigned" after the assignment period has ended.

Likewise:

    Excavator #3
    → Foundation
    → Chennai IT Park
    → 01/08/2026 to 15/08/2026

should become available after the assignment ends, assuming it is not in another active assignment or maintenance state.

---

# 17. OVERLAPPING ASSIGNMENTS

Where appropriate, prevent impossible resource conflicts.

A worker/equipment item should not be simultaneously assigned to incompatible overlapping assignments.

At minimum, inspect existing assignment logic and add validation to prevent obvious duplicate active assignments.

For this project, assume a worker/equipment item cannot be actively assigned to two unrelated tasks at the same time.

---

# 18. BACKEND CHANGES

Update all relevant backend logic.

At minimum inspect/update:

    routes/workers.py
    routes/equipment.py
    routes/projects.py
    routes/tasks.py

and any other relevant modules discovered during inspection.

Update:

- Assignment creation
- Assignment editing
- Assignment deletion
- Status display
- Validation
- Project/task filtering
- SQLAlchemy relationships
- Dashboard calculations
- Reports

No route should continue assuming that an assignment only contains:

    project_id

when the actual assignment must identify:

    project_task_id

---

# 19. UI DISPLAY

The UI should clearly show the full allocation context.

## Worker details/list

Instead of simply:

    Rajesh
    Status: Assigned

show useful information such as:

    Rajesh
    Status: Assigned
    Project: Chennai IT Park
    Task: Bricklaying

If multiple current assignments are possible according to the existing design, show all relevant active assignments.

## Equipment details/list

Instead of:

    Excavator #3
    Status: In Use

show:

    Excavator #3
    Status: In Use
    Project: Chennai IT Park
    Task: Foundation

---

# 20. PROJECT DETAILS

On the Project Details page, resource allocations should be understandable in context.

Example:

    Chennai IT Park

    Project Tasks

    Bricklaying
       Workers:
       - Rajesh
       - Kumar

       Equipment:
       - Concrete Mixer #2

    Foundation
       Workers:
       - Arjun
       - Suresh

       Equipment:
       - Excavator #3

Follow the existing application's design. Do not redesign unrelated parts.

---

# 21. TASK DETAILS

A project-specific task should be able to show:

- Project
- Task Type
- Progress
- Status
- Dates
- Assigned Workers
- Assigned Equipment

This provides complete context for resource allocation.

---

# 22. DATABASE CONSTRAINTS

Use appropriate PostgreSQL constraints.

At minimum:

- Primary keys
- Foreign keys
- NOT NULL where appropriate
- CHECK constraints
- Appropriate UNIQUE constraints
- Appropriate indexes

Worker assignment:

    project_task_id NOT NULL

Equipment assignment:

    project_task_id NOT NULL

Do not allow an assignment record to exist without a specific project task.

Prevent negative:

- assigned hours
- equipment hours
- rates

Use suitable numeric types.

---

# 23. REFERENTIAL INTEGRITY

Do not blindly use `ON DELETE CASCADE`.

Be careful with historical assignments.

If a project/task is deleted, do not accidentally erase important historical worker/equipment records unless that behavior is explicitly justified.

Prefer safe deletion rules consistent with the existing project.

---

# 24. DATA MIGRATION

This is an existing application.

Do NOT simply wipe the database.

Before migration:

1. Inspect existing data.
2. Back up/export the database if appropriate.
3. Identify existing worker assignments.
4. Identify existing equipment assignments.
5. Determine whether each existing assignment can be linked to a valid project task.
6. Migrate valid records.
7. Flag or safely handle records that cannot be mapped.

For an existing assignment such as:

    Rajesh → Chennai IT Park

if the appropriate task can be identified from existing data, convert it to:

    Rajesh → Chennai IT Park → Bricklaying

If an existing assignment genuinely has no task information, do not invent a task silently.

Instead, handle it safely and report it so it can be resolved.

---

# 25. SEED / DEMO DATA

Update seed data so the system visibly demonstrates correct resource allocation.

Example:

    Chennai IT Park
        Foundation
            Workers: Arjun, Suresh
            Equipment: Excavator #3

        Bricklaying
            Workers: Rajesh, Kumar
            Equipment: Concrete Mixer #2

        Electrical Installation
            Workers: Vikram
            Equipment: None

Another project can independently use the same task types:

    Green Heights
        Bricklaying
            Workers: Mahesh
            Equipment: Concrete Mixer #1

This demonstrates that the same task type can exist across projects while resources are assigned to specific project-task instances.

---

# 26. VERIFICATION TESTS

After implementation, perform these tests.

## Test 1 — Worker assignment requires task

Attempt:

    Worker → Project

without selecting a task.

Expected:

    Assignment rejected.

## Test 2 — Worker assignment succeeds

Create:

    Rajesh
    → Chennai IT Park
    → Bricklaying

Expected:

    Assignment succeeds.

Worker status becomes:

    Assigned

## Test 3 — Worker status returns to Available

End the assignment.

Expected:

    Rajesh → Available

provided he has no other active assignment and is not in a manual state such as On Leave.

## Test 4 — Equipment assignment requires task

Attempt:

    Excavator #3
    → Chennai IT Park

without selecting a task.

Expected:

    Assignment rejected.

## Test 5 — Equipment assignment succeeds

Create:

    Excavator #3
    → Chennai IT Park
    → Foundation

Expected:

    Assignment succeeds.

Equipment status becomes:

    In Use

## Test 6 — Equipment status returns to Available

End the assignment.

Expected:

    Excavator #3 → Available

provided there is no other active assignment and it is not in Maintenance/Retired state.

## Test 7 — Invalid project/task combination

Attempt:

    Project = Chennai IT Park
    Task = Bricklaying belonging to Green Heights

Expected:

    Backend rejects the request.

## Test 8 — Historical assignment

Create an assignment whose end/release date has passed.

Expected:

    It remains visible in historical records,
    but does NOT make the worker/equipment appear currently assigned.

## Test 9 — Independent task allocation

Verify:

    Bricklaying
        → Chennai IT Park
            → Rajesh
        → Green Heights
            → Mahesh

Changing one project's assignment must not modify the other project's assignment.

---

# 27. IMPORTANT STATUS RULE

The following principle must remain true throughout the application:

> A worker cannot be displayed as "Assigned" unless an actual active `task_workers` record connects that worker to a valid `project_task`.

Likewise:

> Equipment cannot be displayed as "In Use" unless an actual active `equipment_assignments` record connects that equipment to a valid `project_task`.

Do not use hardcoded status changes in application code when the state can be derived from the database.

---

# 28. IMPLEMENTATION PRIORITY

Implement this consistency engine before unrelated modules.

Priority:

1. Inspect existing implementation.
2. Inspect existing database/data.
3. Plan migration.
4. Fix worker assignment schema.
5. Fix equipment assignment schema.
6. Require project + task in worker assignment UI.
7. Require project + task in equipment assignment UI.
8. Add backend validation.
9. Implement dynamic worker status.
10. Implement dynamic equipment status.
11. Update project/task resource displays.
12. Update seed/demo data.
13. Test all flows.
14. Fix discovered issues.
15. Provide an implementation report.

---

# 29. DO NOT

Do NOT:

- Replace PostgreSQL with SQLite.
- Replace SQLAlchemy.
- Delete the existing database without explicit approval.
- Wipe existing data unnecessarily.
- Allow project-only worker assignments.
- Allow project-only equipment assignments.
- Allow manually setting "Assigned".
- Allow manually setting "In Use".
- Trust frontend validation without backend validation.
- Invent task assignments for existing records without evidence.
- Introduce unrelated features.
- Redesign the entire UI.
- Create unnecessary tables.

---

# 30. FINAL SUCCESS CONDITION

The implementation is successful when the database and UI enforce:

    PROJECT
       ↓
    PROJECT TASK
       ↓
    ┌───────────────┐
    │               │
    WORKERS      EQUIPMENT
    │               │
    └──── specific task ────┘

A user must be able to answer:

> "Which worker is doing what task, in which project?"

and:

> "Which equipment is being used for what task, in which project?"

The system must never show a worker as "Assigned" or equipment as "In Use" based solely on a vague project association.

After implementation, provide a concise report containing:

1. Existing issues discovered.
2. Database changes.
3. Tables modified.
4. Relationships changed.
5. Migration performed.
6. Backend changes.
7. UI changes.
8. Status calculation logic.
9. Validation added.
10. Tests performed.
11. Any unresolved records/issues.

Do not make unrelated changes.
