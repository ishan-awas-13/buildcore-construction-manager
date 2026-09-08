# BuildCore DB — Project/Task Many-to-Many Refactor

## OBJECTIVE

Modify the existing BuildCore DB application so that **Task Types and Projects have a proper many-to-many relationship**, with the relationship fully represented at both the PostgreSQL/database level and in the web UI.

The final user experience must allow:

1. Open the Tasks module.
2. Click a task name such as "Bricklaying".
3. See every project where Bricklaying is currently being performed.
4. See an independent progress bar for Bricklaying within each project.
5. Click a project name.
6. Navigate to that project's details page.
7. See every task being performed within that project, each with its own progress.
8. Click a task from the project page and return to that task's page showing all projects using that task.

The relationship must therefore work in BOTH directions:

    TASK TYPE
        ↓
    Projects using this task
        ↓
    PROJECT
        ↓
    Tasks within this project
        ↓
    TASK TYPE

This must be a genuine many-to-many relationship in PostgreSQL, not merely a UI simulation.

---

# 1. IMPORTANT: INSPECT THE EXISTING PROJECT FIRST

Before modifying anything:

- Inspect the complete existing project structure.
- Inspect the existing PostgreSQL/SQLAlchemy models.
- Inspect the existing database schema/migrations.
- Inspect all routes related to:
  - Projects
  - Tasks
  - Workers
- Inspect the existing project and task templates.
- Inspect existing SQL queries/views/functions.
- Inspect seed/demo data.
- Search the entire codebase for references to the existing `tasks` table/model.

Do not blindly create new files or duplicate existing functionality.

Determine exactly how the current implementation works before changing it.

---

# 2. CURRENT PROBLEM

The current system models:

    projects 1 ───── N tasks

Therefore, a task such as:

    Bricklaying

currently belongs directly to one project.

This is not the desired model.

Construction activities such as:

- Foundation
- Bricklaying
- Electrical Installation
- Plumbing
- Painting
- Asphalt Surfacing

are reusable types of construction work.

The same task type can occur across many projects.

For example:

    Bricklaying
        ├── Chennai IT Park → 80%
        ├── Green Heights → 45%
        └── Heritage Museum → 100%

The progress, status, dates, description, and worker assignments must be specific to the project.

There is NO single global progress value for "Bricklaying".

---

# 3. REQUIRED DATABASE MODEL

Replace the current direct Project → Task relationship with:

    PROJECTS
        ↕
    PROJECT_TASKS
        ↕
    TASK_TYPES

Conceptually:

    PROJECTS N ───── M TASK_TYPES

resolved through:

    PROJECT_TASKS

---

# 4. TASK_TYPES TABLE

Create/use a `task_types` table for reusable construction activities.

Suggested structure:

    task_type_id       PRIMARY KEY
    task_name          VARCHAR
    description        TEXT

Examples:

    Foundation
    Bricklaying
    Electrical Installation
    Plumbing
    Painting
    Asphalt Surfacing

Important:

`task_types` must NOT contain:

- project_id
- completion_percentage
- project-specific dates
- project-specific status

Those values belong to `project_tasks`.

---

# 5. PROJECT_TASKS TABLE

Create/use a `project_tasks` junction/entity table representing the execution of a task type within a specific project.

Suggested structure:

    project_task_id          PRIMARY KEY
    project_id               FOREIGN KEY → projects.project_id
    task_type_id             FOREIGN KEY → task_types.task_type_id
    start_date
    due_date
    status
    completion_percentage
    description

This is the most important table in the refactor.

Example:

    project_task_id | project_id | task_type_id | progress
    -------------------------------------------------------
    1               | 1          | 2            | 80
    2               | 2          | 2            | 45
    3               | 8          | 2            | 100

All three records represent:

    Bricklaying

but each is an independent project-specific task.

---

# 6. UNIQUE PROJECT/TASK COMBINATION

Normally, a project should not contain the same task type multiple times.

Therefore implement:

    UNIQUE(project_id, task_type_id)

unless the existing application contains a clearly documented reason why the same task type needs to occur multiple times within a single project.

If such a case exists, inspect it before deciding how to handle it.

---

# 7. WORKER RELATIONSHIP

The existing worker/task relationship must be updated.

Workers must be assigned to the PROJECT-SPECIFIC task execution, not to the generic task type.

The relationship should therefore become:

    PROJECT_TASKS 1 ───── N TASK_WORKERS N ───── 1 WORKERS

The existing `task_workers` table should reference:

    project_task_id

instead of:

    task_id / task_type_id

Example:

    Rajesh
        → Bricklaying
        → Chennai IT Park

is a different assignment from:

    Kumar
        → Bricklaying
        → Green Heights

---

# 8. MIGRATION OF EXISTING DATA

This is an existing application.

Do NOT simply delete the current `tasks` table and lose existing data.

First inspect the current data.

Migrate existing task records into:

    task_types
    project_tasks

For example, if the current database contains:

    Asphalt Surfacing
    → Delhi-Mumbai Expressway Phase 4
    → 0%
    → Not Started

convert this into something equivalent to:

    task_types:
        Asphalt Surfacing

    project_tasks:
        project = Delhi-Mumbai Expressway Phase 4
        task_type = Asphalt Surfacing
        progress = 0%
        status = Not Started

Preserve existing:

- task names
- descriptions
- dates
- statuses
- completion percentages
- project relationships
- worker relationships

where possible.

Do not destroy useful existing data.

---

# 9. PROJECT PROGRESS

Project overall progress must remain dynamically calculated.

Do NOT add/store a manually maintained `progress` column in `projects`.

Calculate project progress from its `project_tasks`.

For the first iteration, use the average completion percentage of the project's project-specific tasks.

Example:

    Foundation       100%
    Bricklaying       80%
    Painting           0%

Overall:

    (100 + 80 + 0) / 3 = 60%

Handle projects with zero tasks safely.

Prefer SQL/View/query logic for this calculation.

Do not duplicate derived data unnecessarily.

---

# 10. TASK MODULE UI

The Tasks module should now represent TASK TYPES.

Example:

    Tasks

    Foundation
    Bricklaying
    Electrical Installation
    Plumbing
    Painting
    Asphalt Surfacing

When the user clicks:

    Bricklaying

open a Task Type Details page.

---

# 11. TASK TYPE DETAILS PAGE

The page should display:

    Bricklaying

    Description:
    [task description]

Then show:

    Projects Using This Task

Example:

    Chennai IT Park
    ████████░░ 80%
    In Progress

    Green Heights
    ████░░░░░░ 45%
    In Progress

    Heritage Museum
    ██████████ 100%
    Completed

Each project MUST have its own:

- Progress percentage
- Progress bar
- Status
- Relevant dates

Do NOT display one global progress value for Bricklaying.

---

# 12. PROJECT NAME MUST BE CLICKABLE

Every project shown on the Task Type Details page must be clickable.

Example:

    Chennai IT Park

When clicked:

    → redirect to the existing Project Details page
      for Chennai IT Park

Do not create a separate unrelated project page.

Reuse the existing project details functionality.

---

# 13. PROJECT DETAILS PAGE

Update the existing Project Details page so it displays all `project_tasks` belonging to that project.

Example:

    Chennai IT Park

    Overall Progress
    ████████░░ 80%

    Project Tasks

    Foundation
    ██████████ 100%
    Completed

    Bricklaying
    ████████░░ 80%
    In Progress

    Electrical Installation
    █████░░░░░ 50%
    In Progress

    Painting
    ░░░░░░░░░░ 0%
    Not Started

Each task name must be clickable.

---

# 14. TASK NAME ON PROJECT PAGE

If the user clicks:

    Bricklaying

from the Chennai IT Park Project Details page:

    → redirect to the Bricklaying Task Type Details page

That page must then show:

    All projects currently using Bricklaying

Therefore the user can navigate in both directions.

---

# 15. COMPLETE UI RELATIONSHIP

The final UI should clearly demonstrate:

    TASK TYPE
        │
        ├── PROJECT A → progress
        ├── PROJECT B → progress
        └── PROJECT C → progress
                  │
                  ↓
             PROJECT PAGE
                  │
                  ├── TASK TYPE 1 → progress
                  ├── TASK TYPE 2 → progress
                  └── TASK TYPE 3 → progress

This is an important academic requirement because the many-to-many relationship should be visible and understandable through the UI.

---

# 16. TASK CRUD

Separate TASK TYPE management from PROJECT TASK management.

## Task Type

The user should be able to:

- Create a task type
- Edit a task type
- View a task type
- Delete a task type only when safe

Examples:

    Bricklaying
    Painting
    Plumbing

## Project Task

The user should be able to:

- Add an existing task type to a project
- Select project-specific dates
- Set status
- Set completion percentage
- Add a description
- Assign workers
- Edit project-specific task information

For example:

    Add "Bricklaying" to "Chennai IT Park"

This creates a `project_tasks` record.

Do NOT create duplicate task types such as:

    Bricklaying - Chennai
    Bricklaying - Delhi
    Bricklaying - Jaipur

There should be one reusable:

    Bricklaying

task type.

---

# 17. UI DESIGN

I have provided reference screenshots of the current:

1. Task Details page
2. Project Details page

Use those screenshots as the visual reference.

Preserve the existing application's:

- Header
- Sidebar
- Typography
- Cards
- Buttons
- Status badges
- Progress bars
- General spacing/layout
- Overall visual style

Do NOT redesign the entire application.

Make only the changes necessary to support the new relationship.

The new Task Type Details page should visually fit into the existing application.

---

# 18. DATABASE INTEGRITY

Implement appropriate PostgreSQL constraints.

Required:

- Primary keys
- Foreign keys
- NOT NULL where appropriate
- UNIQUE constraints
- CHECK constraints
- Appropriate indexes

Completion percentage:

    0 <= completion_percentage <= 100

Prevent negative:

- quantities
- hours
- rates
- budgets
- expenses

Use appropriate numeric types for money.

Do not use floating-point types for monetary values.

Do not blindly use `ON DELETE CASCADE` everywhere.

Historical purchases, expenses, and other records should not disappear accidentally when a project/task is deleted.

---

# 19. SQLALCHEMY / BACKEND

The application uses:

    Flask
    SQLAlchemy
    PostgreSQL

Continue using SQLAlchemy.

Update:

- Models
- Relationships
- Queries
- Routes
- Forms
- Validation
- Templates
- Reports
- Dashboard calculations

so that everything consistently uses:

    task_types
    project_tasks

There must be no remaining application logic incorrectly assuming:

    projects 1 → N tasks

---

# 20. REPORTS / QUERIES

Update relevant reports so they use the new relationship.

The system should support queries such as:

### All projects using a particular task

    Find all projects currently performing Bricklaying.

### Task progress by project

    Show Bricklaying progress for every project.

### All tasks in a project

    Show every project-specific task for Chennai IT Park.

### Project progress

    Calculate overall progress from project_tasks.

### Worker assignments

    Show workers assigned to a particular project-specific task.

Use proper SQL joins and aggregation.

---

# 21. TEST DATA

Ensure the seed/demo data actually demonstrates the many-to-many relationship.

This is VERY IMPORTANT.

Do not create data where every task exists in only one project.

At minimum, several task types should appear in multiple projects.

For example:

    Bricklaying
        → Chennai IT Park: 80%
        → Green Heights: 45%
        → Heritage Museum: 100%

    Painting
        → Chennai IT Park: 20%
        → Green Heights: 70%

    Electrical Installation
        → Chennai IT Park: 50%
        → Heritage Museum: 100%

This makes the many-to-many relationship obvious during demonstration.

---

# 22. ACCEPTANCE TEST

After implementation, verify the following exact workflow.

## Test A — Task → Projects

1. Open Tasks.
2. Click "Bricklaying".
3. Task Type Details opens.
4. See multiple projects.
5. Each project has an independent progress bar.
6. Progress values are different where appropriate.

Expected:

    Bricklaying

    Chennai IT Park       80%
    Green Heights         45%
    Heritage Museum       100%

---

## Test B — Task → Project

1. From Bricklaying Task Details,
2. Click "Chennai IT Park".
3. Navigate to Chennai IT Park Project Details.

---

## Test C — Project → Tasks

On Chennai IT Park Project Details:

See:

    Foundation
    Bricklaying
    Electrical Installation
    Painting
    ...

Each has its own project-specific progress.

---

## Test D — Project → Task

Click:

    Bricklaying

from the Chennai IT Park page.

It should return to:

    Bricklaying Task Type Details

where all projects using Bricklaying are shown.

---

## Test E — Independent Progress

Change:

    Bricklaying → Chennai IT Park

from 80% to 90%.

Verify that:

    Bricklaying → Green Heights

remains 45%.

Changing a project-specific task MUST NOT modify the task's progress in other projects.

---

# 23. IMPLEMENTATION PROCESS

Work in the following order.

### Step 1

Inspect the existing implementation.

### Step 2

Explain the current task/project schema briefly.

### Step 3

Plan the database migration.

### Step 4

Implement:

    task_types
    project_tasks

and update the relevant relationships.

### Step 5

Migrate/preserve existing task data.

### Step 6

Update SQLAlchemy models and backend logic.

### Step 7

Update Task module UI.

### Step 8

Update Project Details UI.

### Step 9

Update worker/task relationships.

### Step 10

Update project progress calculation.

### Step 11

Update seed/demo data.

### Step 12

Run the application.

### Step 13

Test the complete navigation flow.

### Step 14

Fix any errors discovered during testing.

---

# 24. DO NOT

Do NOT:

- Replace PostgreSQL with SQLite.
- Replace SQLAlchemy.
- Introduce React unless absolutely necessary.
- Introduce unnecessary frameworks.
- Create duplicate task types.
- Store global progress on task types.
- Store manually maintained project progress.
- Delete existing project/task data unnecessarily.
- Break existing project functionality.
- Redesign the entire UI.
- Add unrelated features.
- Create unnecessary tables.

Keep the implementation focused on this relationship refactor.

---

# 25. FINAL EXPECTED DATABASE CONCEPT

The final design should conceptually be:

    PROJECTS
       │
       │ 1:N
       ↓
    PROJECT_TASKS
       ↑
       │ N:1
       │
    TASK_TYPES


Which represents:

    PROJECTS N:M TASK_TYPES

with `PROJECT_TASKS` acting as the association/entity table.

Workers should connect to:

    PROJECT_TASKS

rather than generic task types.

---

# 26. FINAL SUCCESS CONDITION

The implementation is complete when the following statement is true:

> A reusable task type such as "Bricklaying" can exist across multiple projects, each project has an independent instance of that task with its own progress/status/dates/workers, and the user can navigate seamlessly from Task → Projects → Project → Tasks → Task through the UI.

After implementation, provide a concise implementation report containing:

1. Database changes made.
2. Tables added/modified.
3. Relationships changed.
4. Migration performed.
5. Backend changes.
6. UI changes.
7. Queries/views/functions changed.
8. Test results.
9. Any remaining issues.

Do not make unrelated changes.