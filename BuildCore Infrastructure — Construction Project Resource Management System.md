# BuildCore Infrastructure — Construction Project Resource Management System

## 1. Project Overview

BuildCore Infrastructure Pvt. Ltd. is a fictional mid-sized construction/EPC company that manages multiple construction projects such as commercial buildings, residential complexes, roads, bridges, and industrial facilities.

The goal of this project is to build a web-based **Construction Project Resource Management System** backed by PostgreSQL.

The system should allow the company to manage:

- Construction projects
- Workers
- Construction tasks
- Equipment
- Materials
- Suppliers
- Material purchases
- Material usage
- Worker assignments
- Equipment assignments
- Project expenses
- Project progress

The central objective is:

> Track what resources are being used on each project, who is using them, how much they cost, and how each project is progressing.

This is primarily a **DBMS academic project**, so the PostgreSQL database design and database functionality are more important than visual complexity.

---

# 2. Technology Stack

Use the following stack for the first iteration:

### Database
- PostgreSQL

### Backend
- Python
- Flask

### Frontend
- HTML
- CSS
- JavaScript

Do NOT introduce React, Node.js, Docker, microservices, or other unnecessary technologies unless specifically requested later.

The application should initially run locally.

Architecture:

Browser
→ Flask Backend
→ PostgreSQL Database

---

# 3. Core Database Schema

The database must contain the following 13 tables.

Do not add additional tables unless there is a strong technical reason and the change is explicitly documented.

---

## 3.1 projects

Stores all construction projects.

Fields:

- project_id — Primary Key
- project_name
- project_type
- client_name
- location
- start_date
- expected_end_date
- budget
- status

Suggested project status values:

- Planning
- Active
- Completed
- On Hold

---

## 3.2 workers

Stores company workers/employees involved in construction activities.

Fields:

- worker_id — Primary Key
- name
- role
- skill
- phone
- daily_rate
- status

Suggested worker status values:

- Available
- Assigned
- Inactive

---

## 3.3 materials

Stores construction materials.

Fields:

- material_id — Primary Key
- material_name
- unit
- unit_cost
- minimum_stock

Examples:

- Cement
- Steel
- Bricks
- Sand
- Concrete
- Electrical Wire
- Pipes

---

## 3.4 equipment

Stores construction machinery and equipment.

Fields:

- equipment_id — Primary Key
- equipment_name
- equipment_type
- status
- hourly_rate

Examples:

- Excavator
- Tower Crane
- Concrete Mixer
- Bulldozer
- Road Roller

Suggested equipment statuses:

- Available
- In Use
- Maintenance
- Retired

---

## 3.5 suppliers

Stores suppliers that provide materials or construction resources.

Fields:

- supplier_id — Primary Key
- supplier_name
- contact_person
- phone
- email
- address

---

## 3.6 project_workers

Many-to-many relationship between projects and workers.

A worker may work on multiple projects, and a project may have many workers.

Fields:

- project_worker_id — Primary Key
- project_id — Foreign Key → projects.project_id
- worker_id — Foreign Key → workers.worker_id
- assigned_date
- release_date
- role_on_project

---

## 3.7 tasks

Stores individual construction tasks belonging to projects.

Fields:

- task_id — Primary Key
- project_id — Foreign Key → projects.project_id
- task_name
- description
- start_date
- due_date
- status
- completion_percentage

Suggested task statuses:

- Not Started
- In Progress
- Completed
- Delayed

Examples:

- Foundation
- Structural Columns
- Brickwork
- Electrical Installation
- Plumbing
- Painting
- Road Surfacing

---

## 3.8 task_workers

Many-to-many relationship between tasks and workers.

A task may have multiple workers, and a worker may work on multiple tasks.

Fields:

- task_worker_id — Primary Key
- task_id — Foreign Key → tasks.task_id
- worker_id — Foreign Key → workers.worker_id
- assigned_hours

---

## 3.9 equipment_assignments

Records which equipment is assigned to which project.

Fields:

- assignment_id — Primary Key
- equipment_id — Foreign Key → equipment.equipment_id
- project_id — Foreign Key → projects.project_id
- start_date
- end_date
- hours_used

---

## 3.10 material_usage

Tracks materials allocated to and consumed by projects.

Fields:

- usage_id — Primary Key
- project_id — Foreign Key → projects.project_id
- material_id — Foreign Key → materials.material_id
- quantity_allocated
- quantity_used

The system should allow the remaining quantity to be derived as:

quantity_allocated - quantity_used

Avoid storing redundant derived values unless there is a clear reason.

---

## 3.11 purchases

Stores material/resource purchase transactions.

Fields:

- purchase_id — Primary Key
- supplier_id — Foreign Key → suppliers.supplier_id
- project_id — Foreign Key → projects.project_id
- purchase_date
- total_amount
- status

Suggested purchase statuses:

- Pending
- Ordered
- Delivered
- Cancelled

---

## 3.12 purchase_items

Stores individual materials included in each purchase.

Fields:

- purchase_item_id — Primary Key
- purchase_id — Foreign Key → purchases.purchase_id
- material_id — Foreign Key → materials.material_id
- quantity
- unit_price

A single purchase can contain multiple purchase items.

---

## 3.13 expenses

Stores project-related expenses.

Fields:

- expense_id — Primary Key
- project_id — Foreign Key → projects.project_id
- expense_type
- amount
- expense_date
- description

Suggested expense types:

- Labour
- Material
- Equipment
- Transportation
- Miscellaneous

---

# 4. Relationships

Implement the following relationships exactly.

### Project → Tasks

One project can have many tasks.

```text
projects 1 ─────── N tasks
```

### Project ↔ Worker

Many-to-many relationship through project_workers.

```text
projects 1 ─────── N project_workers N ─────── 1 workers
```

### Task ↔ Worker

Many-to-many relationship through task_workers.

```text
tasks 1 ─────── N task_workers N ─────── 1 workers
```

### Project ↔ Equipment

Many-to-many over time through equipment_assignments.

```text
projects 1 ─────── N equipment_assignments N ─────── 1 equipment
```

### Project ↔ Material

Many-to-many through material_usage.

```text
projects 1 ─────── N material_usage N ─────── 1 materials
```

### Supplier → Purchases

One supplier can have many purchases.

```text
suppliers 1 ─────── N purchases
```

### Project → Purchases

One project can have many purchases.

```text
projects 1 ─────── N purchases
```

### Purchase → Purchase Items

One purchase can contain many purchase items.

```text
purchases 1 ─────── N purchase_items
```

### Material → Purchase Items

One material can appear in many purchase items.

```text
materials 1 ─────── N purchase_items
```

### Project → Expenses

One project can have many expenses.

```text
projects 1 ─────── N expenses
```

---

# 5. Database Requirements

Use proper PostgreSQL constraints.

Every table must have a primary key.

Foreign keys must be properly enforced.

Use appropriate:

- NOT NULL constraints
- UNIQUE constraints where appropriate
- CHECK constraints
- DEFAULT values where appropriate
- Foreign-key constraints
- Numeric precision for monetary values

Money/cost fields should use an appropriate PostgreSQL numeric type rather than floating-point types.

Completion percentage must be restricted to:

```text
0–100
```

Quantities, rates, hours, budgets, and expenses must not accept negative values.

Email and phone fields should have reasonable validation at the application level.

---

# 6. Referential Integrity

Foreign-key relationships must protect database integrity.

For example:

- A task cannot exist without a valid project.
- A project-worker assignment cannot reference a nonexistent worker.
- A purchase cannot reference a nonexistent supplier.
- A purchase item cannot reference a nonexistent purchase.
- An expense cannot reference a nonexistent project.

Use appropriate ON DELETE behavior.

Do not blindly use CASCADE everywhere. Avoid accidental deletion of important historical records.

---

# 7. Application Features — First Iteration

Build a clean functional web application around the database.

The first iteration should contain:

## Dashboard

Display:

- Total Projects
- Active Projects
- Completed Projects
- Total Workers
- Available Equipment
- Total Material Purchases
- Total Project Expenses

Also display a list of active projects with:

- Project name
- Type
- Location
- Budget
- Status
- Progress

---

# 8. Project Management

Users should be able to:

- View projects
- Add projects
- Edit projects
- View project details
- View project tasks
- View assigned workers
- View assigned equipment
- View material usage
- View purchases
- View expenses

The project detail page should act as the central page for understanding a project.

---

# 9. Worker Management

Users should be able to:

- View workers
- Add workers
- Edit workers
- View worker details
- Assign workers to projects
- Assign workers to tasks

Display useful information such as:

- Current assignment
- Role
- Skill
- Daily rate
- Status

---

# 10. Task Management

Users should be able to:

- Create tasks for projects
- Update task status
- Update completion percentage
- Assign workers
- View task deadlines

Tasks should clearly show whether they are:

- Not Started
- In Progress
- Completed
- Delayed

---

# 11. Equipment Management

Users should be able to:

- View equipment
- Add equipment
- Edit equipment
- Assign equipment to projects
- Record usage hours
- View current equipment status

---

# 12. Material Management

Users should be able to:

- View materials
- Add materials
- Edit materials
- View material usage by project
- Record allocated quantity
- Record used quantity

The system should highlight materials where stock/availability is approaching the minimum stock threshold.

For the first iteration, do not build a complicated warehouse/inventory subsystem.

---

# 13. Supplier and Purchase Management

Users should be able to:

- View suppliers
- Add suppliers
- Edit suppliers
- Create purchases
- Add multiple materials to a purchase
- View purchase details
- Associate purchases with projects

Purchase totals should be calculated from purchase items where appropriate.

---

# 14. Expense Management

Users should be able to:

- Add expenses
- Edit expenses
- Delete expenses where appropriate
- Filter expenses by project
- Filter expenses by type
- View total project expenses

---

# 15. Important Database Queries / Reports

The system should eventually support queries such as:

1. List all active projects.

2. Show all workers assigned to a particular project.

3. Show all tasks for a project.

4. Show project completion percentage.

5. Show equipment currently assigned to a project.

6. Show materials used by each project.

7. Show total material purchased for a project.

8. Show total expenses for each project.

9. Compare project budget with actual expenses.

10. Find workers who are currently available.

11. Find equipment currently available.

12. Find delayed tasks.

13. Find projects approaching their expected completion date.

14. Find materials below minimum stock level.

15. Calculate total spending by expense type.

These queries are important because they demonstrate the DBMS functionality of the project.

---

# 16. Advanced DBMS Features

The project should eventually demonstrate PostgreSQL features such as:

### Views

Create useful views such as:

- active_projects_view
- project_expense_summary
- project_progress_view
- material_usage_summary

### Functions / Stored Procedures

Use functions for useful operations such as:

- calculating project total expenses
- calculating project progress
- calculating purchase totals

### Triggers

Potential triggers:

- Automatically update equipment status when equipment is assigned.
- Prevent invalid material usage.
- Validate task completion percentage.
- Maintain appropriate resource states.

Do not add artificial triggers merely for the sake of having triggers. They should represent meaningful business rules.

### Transactions

Use transactions for multi-step operations such as creating a purchase and its purchase items.

### Indexes

Add indexes to frequently queried foreign-key/filter columns where justified.

---

# 17. Business Rules

Implement these rules where appropriate:

1. A task must belong to a valid project.

2. A worker assignment must reference a valid worker and project.

3. A worker cannot have an invalid negative daily rate.

4. Equipment cannot have a negative hourly rate.

5. Material quantities cannot be negative.

6. Task completion must be between 0 and 100.

7. A purchase must belong to a valid supplier and project.

8. A purchase item must belong to a valid purchase and material.

9. Expense amounts cannot be negative.

10. A project budget cannot be negative.

11. Expected project completion date should not be earlier than the start date.

12. Task due date should not be earlier than task start date.

13. Historical project expenses and purchases should not be accidentally deleted through cascading relationships.

---

# 18. Sample Data

Create realistic sample data for demonstration.

The database should contain enough data to make the application look populated.

Create approximately:

- 8–10 projects
- 20–30 workers
- 15–20 materials
- 10–15 equipment items
- 8–12 suppliers
- 30+ project-worker assignments
- 30+ tasks
- 30+ task-worker assignments
- 15+ equipment assignments
- 20+ material usage records
- 20+ purchases
- 40+ purchase items
- 30+ expenses

Use realistic Indian construction-company data and locations.

Do not use real people's personal information.

---

# 19. UI Requirements

The interface should look like a modern professional construction management dashboard.

Style:

- Clean
- Professional
- Minimal
- Desktop-first
- Responsive
- Easy to navigate

Suggested navigation:

```text
Dashboard

Projects
Workers
Tasks
Equipment
Materials
Suppliers
Purchases
Expenses
Reports
```

Use cards, tables, status badges, filters, and forms where appropriate.

Do not over-design the interface.

The database functionality should remain the priority.

---

# 20. Project Structure

Use a clean maintainable Flask structure.

Suggested structure:

```text
buildcore/
│
├── app.py
├── config.py
├── requirements.txt
│
├── database/
│   ├── schema.sql
│   ├── seed.sql
│   └── queries.sql
│
├── routes/
│   ├── dashboard.py
│   ├── projects.py
│   ├── workers.py
│   ├── tasks.py
│   ├── equipment.py
│   ├── materials.py
│   ├── suppliers.py
│   ├── purchases.py
│   └── expenses.py
│
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── projects/
│   ├── workers/
│   ├── tasks/
│   ├── equipment/
│   ├── materials/
│   ├── suppliers/
│   ├── purchases/
│   └── expenses/
│
├── static/
│   ├── css/
│   └── js/
│
└── docs/
```

This structure may be adjusted if necessary, but keep the project organized and modular.

---

# 21. Development Approach

Do NOT attempt to build the entire system blindly in one step.

Build the first iteration in this order:

### Phase 1 — Database

1. Create PostgreSQL database.
2. Create all 13 tables.
3. Add primary keys.
4. Add foreign keys.
5. Add constraints.
6. Insert seed/demo data.
7. Test relationships.

### Phase 2 — Backend

Implement Flask connection to PostgreSQL.

Then implement CRUD operations for the main entities.

### Phase 3 — Dashboard

Create the dashboard and project overview.

### Phase 4 — Core Modules

Implement:

1. Projects
2. Workers
3. Tasks
4. Equipment
5. Materials
6. Suppliers
7. Purchases
8. Expenses

### Phase 5 — Reports

Implement SQL-based reports and summaries.

### Phase 6 — DBMS Features

Add:

- Views
- Functions
- Triggers
- Transactions
- Indexes
- Complex joins
- Aggregate queries

---

# 22. Important Development Rules

The application must use PostgreSQL as the actual database.

Do not replace PostgreSQL with SQLite.

Do not hard-code database records into the frontend.

Do not use fake JSON data instead of the database.

All important information displayed by the application should come from PostgreSQL.

Use parameterized SQL queries to prevent SQL injection.

Keep database logic separate from presentation logic.

Do not introduce unnecessary technologies.

Prioritize correctness and maintainability over visual complexity.

---

# 23. First Iteration Goal

The first iteration does NOT need to implement every advanced feature.

The immediate goal is to produce a working application with:

- PostgreSQL database
- Complete 13-table schema
- Foreign-key relationships
- Realistic seed data
- Flask backend
- Dashboard
- Project CRUD
- Worker CRUD
- Task CRUD
- Equipment CRUD
- Material CRUD
- Supplier CRUD
- Purchase CRUD
- Expense CRUD
- Basic project detail page
- Basic reports

After this first iteration is working, stop and report:

1. What was implemented.
2. Database schema created.
3. Tables created.
4. Routes created.
5. Pages created.
6. SQL queries used.
7. Any problems encountered.
8. What remains to be implemented.

Do not silently redesign the database schema without explaining the reason.