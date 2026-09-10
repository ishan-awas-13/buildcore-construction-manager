# BuildCore Infrastructure

BuildCore Infrastructure is a comprehensive, web-based database management system designed specifically for construction resource management. It replaces error-prone spreadsheets with a robust, dynamically validated PostgreSQL database accessed through a modern, responsive web application.

## Key Features

- **Project Management**: Track multiple construction projects simultaneously, complete with dynamic progress calculation based on task completion.
- **Dynamic Resource Allocation**: Allocate Workers, Heavy Equipment, and Raw Materials specifically to individual Project Tasks.
- **Automated Real-Time Status Tracking**: Using advanced SQL Views, the system dynamically calculates the availability status of Workers and Equipment based on their active task assignments. It is mathematically impossible for a resource's status to get "stuck".
- **Master-Detail Procurement Pipeline**: A robust Purchasing module allowing managers to track purchase orders from Suppliers, complete with dynamic total calculations handled directly by the database engine.
- **Relational Integrity**: Built on PostgreSQL utilizing strict Foreign Keys, `ON DELETE CASCADE` triggers, and `CHECK` constraints to absolutely guarantee data integrity and prevent orphaned records.

## Technology Stack

- **Backend Framework**: Flask (Python)
- **Database**: PostgreSQL
- **ORM / Query Interface**: SQLAlchemy (Leveraging `text()` for direct raw SQL execution to demonstrate advanced database concepts).
- **Frontend**: HTML5, CSS3, Bootstrap 5, Jinja2 Templating
- **Authentication**: Flask-Login and Werkzeug

## Database Architecture (ER Diagram)

The following diagram illustrates the strict relational schema of the PostgreSQL database, featuring extensive use of Many-to-Many junction tables to accurately reflect the complex real-world relationships of construction resource scaling.

```mermaid
erDiagram
    users {
        int user_id PK
        varchar username UK
        varchar password_hash
    }
    projects {
        int project_id PK
        varchar project_name
        varchar project_type
        varchar client_name
        text location
        date start_date
        date expected_end_date
        numeric budget
        varchar status
    }
    workers {
        int worker_id PK
        varchar name
        varchar role
        varchar skill
        varchar phone
        numeric daily_rate
        varchar status
    }
    equipment {
        int equipment_id PK
        varchar equipment_name
        varchar equipment_type
        varchar status
        numeric hourly_rate
    }
    materials {
        int material_id PK
        varchar material_name
        varchar unit
        numeric unit_cost
        numeric minimum_stock
    }
    suppliers {
        int supplier_id PK
        varchar supplier_name
        varchar contact_person
        varchar phone
        varchar email
        text address
    }
    task_types {
        int task_type_id PK
        varchar task_name UK
        text description
    }
    project_tasks {
        int project_task_id PK
        int project_id FK
        int task_type_id FK
        date start_date
        date due_date
        varchar status
        numeric completion_percentage
        text description
    }
    task_workers {
        int task_worker_id PK
        int project_task_id FK
        int worker_id FK
        numeric assigned_hours
    }
    equipment_assignments {
        int assignment_id PK
        int equipment_id FK
        int project_task_id FK
        date start_date
        date end_date
        numeric hours_used
    }
    material_usage {
        int usage_id PK
        int project_id FK
        int material_id FK
        numeric quantity_allocated
        numeric quantity_used
    }
    project_workers {
        int project_worker_id PK
        int project_id FK
        int worker_id FK
        date assigned_date
        date release_date
        varchar role_on_project
    }
    purchases {
        int purchase_id PK
        int supplier_id FK
        int project_id FK
        date purchase_date
        varchar status
    }
    purchase_items {
        int purchase_item_id PK
        int purchase_id FK
        int material_id FK
        numeric quantity
        numeric unit_price
    }
    expenses {
        int expense_id PK
        int project_id FK
        varchar expense_type
        numeric amount
        date expense_date
        text description
    }
    
    projects ||--o{ project_tasks : "contains"
    task_types ||--o{ project_tasks : "instantiated as"
    project_tasks ||--o{ task_workers : "requires"
    workers ||--o{ task_workers : "assigned to"
    project_tasks ||--o{ equipment_assignments : "utilizes"
    equipment ||--o{ equipment_assignments : "allocated to"
    projects ||--o{ material_usage : "consumes"
    materials ||--o{ material_usage : "used in"
    projects ||--o{ project_workers : "has legacy macro assignments"
    workers ||--o{ project_workers : "assigned to"
    suppliers ||--o{ purchases : "supplies"
    projects ||--o{ purchases : "orders for"
    purchases ||--o{ purchase_items : "contains"
    materials ||--o{ purchase_items : "bought as"
    projects ||--o{ expenses : "incurs"
```

## Running the Application Locally

1. **Clone the repository**
2. **Create a virtual environment**: `python -m venv venv`
3. **Activate the environment**: 
   - Windows: `.\venv\Scripts\activate`
4. **Install dependencies**: `pip install -r requirements.txt`
5. **Configure Environment Variables**:
   - Create a `.env` file in the root directory.
   - Add your database URI: `DATABASE_URL=postgresql://username:password@localhost:5432/buildcore`
6. **Initialize the Database**: `python setup_db.py`
7. **Create the Admin User**: Run `flask create-admin` and follow the interactive prompts to securely set up an administrator account.
8. **Run the Server**: `flask run --debug`
