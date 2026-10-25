from datetime import datetime
from sqlalchemy import text
from extensions import db

def validate_and_assign_task(project_id, task_type_id, start_date_str, due_date_str, status, completion_percentage_raw, description):
    """
    Validates task assignment parameters against project timeline, ensures date order,
    auto-synchronizes status and completion percentage, and inserts a project_tasks record.
    Returns (success: bool, message: str, project_task_id: int or None)
    """
    try:
        completion_percentage = float(completion_percentage_raw if completion_percentage_raw is not None else 0)
    except (ValueError, TypeError):
        return False, "Invalid completion percentage.", None

    if completion_percentage < 0 or completion_percentage > 100:
        return False, "Completion percentage must be between 0 and 100.", None

    project = db.session.execute(
        text("SELECT project_id, project_name, start_date, expected_end_date FROM projects WHERE project_id = :id"),
        {'id': project_id}
    ).fetchone()

    if not project:
        return False, "Project not found.", None

    try:
        sd = datetime.strptime(str(start_date_str).strip(), '%Y-%m-%d').date()
        dd = datetime.strptime(str(due_date_str).strip(), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return False, "Invalid date format. Expected YYYY-MM-DD.", None

    if sd > dd:
        return False, "Start date cannot be after due date.", None

    if (project.start_date and sd < project.start_date) or (project.expected_end_date and dd > project.expected_end_date):
        sd_fmt = project.start_date.strftime('%d %b %Y') if project.start_date else 'N/A'
        ed_fmt = project.expected_end_date.strftime('%d %b %Y') if project.expected_end_date else 'N/A'
        return False, f"Task dates must fall within the project timeline ({sd_fmt} to {ed_fmt}).", None

    # Status and Progress Synchronization
    status = (status or 'Not Started').strip()
    if status == 'Completed' or completion_percentage >= 100.0:
        status = 'Completed'
        completion_percentage = 100.0
    elif status == 'Not Started':
        if completion_percentage > 0:
            status = 'In Progress'
        else:
            completion_percentage = 0.0

    result = db.session.execute(text("""
        INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
        VALUES (:project_id, :task_type_id, :start_date, :due_date, :status, :completion_percentage, :description)
        RETURNING project_task_id
    """), {
        'project_id': project_id,
        'task_type_id': task_type_id,
        'start_date': sd,
        'due_date': dd,
        'status': status,
        'completion_percentage': completion_percentage,
        'description': (description or '').strip()
    })
    new_id = result.fetchone()[0]
    db.session.commit()
    return True, "Task assigned to project successfully!", new_id


def validate_and_assign_worker(project_task_id, worker_id, assigned_hours_raw):
    """
    Validates worker eligibility, checks for duplicate assignments and schedule conflicts,
    snapshots the locked daily rate, and inserts a task_workers record.
    Returns (success: bool, message: str, is_warning: bool)
    """
    try:
        assigned_hours = float(assigned_hours_raw)
    except (ValueError, TypeError):
        return False, "Invalid assigned hours format.", False

    if assigned_hours <= 0:
        return False, "Assigned hours must be greater than 0.", False

    worker = db.session.execute(
        text("SELECT worker_id, name, daily_rate, status FROM workers WHERE worker_id = :id"),
        {'id': worker_id}
    ).fetchone()

    if not worker:
        return False, "Worker not found.", False

    # 1. Reject inactive or on-leave workers
    if worker.status in ('On Leave', 'Inactive'):
        return False, f"Cannot assign {worker.name}: Worker status is currently '{worker.status}'.", False

    # 2. Check if worker is already assigned to this exact task
    existing = db.session.execute(text("""
        SELECT 1 FROM task_workers 
        WHERE worker_id = :w_id AND project_task_id = :pt_id
    """), {'w_id': worker_id, 'pt_id': project_task_id}).fetchone()
    if existing:
        return False, "Worker is already assigned to this task.", True

    # 3. Check for schedule conflicts with other active tasks
    target_task = db.session.execute(text("""
        SELECT pt.project_task_id, pt.start_date, pt.due_date, tt.task_name, p.project_name
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        JOIN projects p ON pt.project_id = p.project_id
        WHERE pt.project_task_id = :pt_id
    """), {'pt_id': project_task_id}).fetchone()

    if target_task and target_task.start_date and target_task.due_date:
        conflict = db.session.execute(text("""
            SELECT tt.task_name, p.project_name, pt.start_date, pt.due_date
            FROM task_workers tw
            JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
            JOIN task_types tt ON pt.task_type_id = tt.task_type_id
            JOIN projects p ON pt.project_id = p.project_id
            WHERE tw.worker_id = :worker_id
              AND pt.project_task_id != :target_id
              AND pt.status IN ('In Progress', 'Not Started')
              AND pt.start_date <= :target_due_date
              AND pt.due_date >= :target_start_date
            LIMIT 1
        """), {
            'worker_id': worker_id,
            'target_id': project_task_id,
            'target_start_date': target_task.start_date,
            'target_due_date': target_task.due_date
        }).fetchone()

        if conflict:
            return False, (
                f"Schedule conflict: {worker.name} is already assigned to '{conflict.task_name}' on '{conflict.project_name}' "
                f"({conflict.start_date.strftime('%Y-%m-%d')} to {conflict.due_date.strftime('%Y-%m-%d')})."
            ), False

    db.session.execute(text("""
        INSERT INTO task_workers (project_task_id, worker_id, assigned_hours, locked_daily_rate)
        VALUES (:project_task_id, :worker_id, :assigned_hours, :locked_daily_rate)
    """), {
        'project_task_id': project_task_id,
        'worker_id': worker_id,
        'assigned_hours': assigned_hours,
        'locked_daily_rate': worker.daily_rate
    })
    db.session.commit()
    return True, "Worker assigned to task successfully!", False


def validate_and_assign_equipment(project_task_id, equipment_id, start_date_str, end_date_str, hours_used_raw):
    """
    Validates equipment availability, status (not Maintenance/Retired), overlapping bookings,
    snapshots the locked hourly rate, and inserts an equipment_assignments record.
    Returns (success: bool, message: str)
    """
    if not project_task_id or not start_date_str:
        return False, "Task and Start Date are required."

    try:
        hours_used = float(hours_used_raw if hours_used_raw is not None else 0)
    except (ValueError, TypeError):
        return False, "Invalid hours used format."

    if hours_used < 0:
        return False, "Hours used cannot be negative."

    try:
        sd = datetime.strptime(str(start_date_str).strip(), '%Y-%m-%d').date()
        ed = datetime.strptime(str(end_date_str).strip(), '%Y-%m-%d').date() if end_date_str else None
    except (ValueError, TypeError):
        return False, "Invalid date format. Expected YYYY-MM-DD."

    if ed and sd > ed:
        return False, "Start date cannot be after end date."

    equipment = db.session.execute(
        text("SELECT equipment_name, status, hourly_rate FROM equipment WHERE equipment_id = :id"),
        {'id': equipment_id}
    ).fetchone()

    if not equipment:
        return False, "Equipment not found."

    if equipment.status in ('Maintenance', 'Retired'):
        return False, f"Cannot assign {equipment.equipment_name}: Equipment is currently in '{equipment.status}' status."

    # Overlap Check
    if ed:
        overlap_sql = text("""
            SELECT 1 FROM equipment_assignments ea
            JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
            WHERE ea.equipment_id = :eq_id
              AND ea.start_date <= :end_date
              AND (
                  (ea.end_date IS NOT NULL AND ea.end_date >= :start_date)
                  OR (ea.end_date IS NULL AND pt.status != 'Completed' AND (pt.due_date >= :start_date OR pt.due_date IS NULL))
                  OR (ea.end_date IS NULL AND pt.status = 'Completed' AND pt.due_date >= :start_date)
              )
            LIMIT 1
        """)
        overlap = db.session.execute(overlap_sql, {'eq_id': equipment_id, 'start_date': sd, 'end_date': ed}).fetchone()
    else:
        overlap_sql = text("""
            SELECT 1 FROM equipment_assignments ea
            JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
            WHERE ea.equipment_id = :eq_id
              AND (
                  (ea.end_date IS NOT NULL AND ea.end_date >= :start_date)
                  OR (ea.end_date IS NULL AND pt.status != 'Completed')
                  OR (ea.end_date IS NULL AND pt.status = 'Completed' AND pt.due_date >= :start_date)
              )
            LIMIT 1
        """)
        overlap = db.session.execute(overlap_sql, {'eq_id': equipment_id, 'start_date': sd}).fetchone()

    if overlap:
        return False, "This equipment is already assigned during the specified overlapping period."

    db.session.execute(text("""
        INSERT INTO equipment_assignments (equipment_id, project_task_id, start_date, end_date, hours_used, locked_hourly_rate)
        VALUES (:equipment_id, :project_task_id, :start_date, :end_date, :hours_used, :locked_hourly_rate)
    """), {
        'equipment_id': equipment_id,
        'project_task_id': project_task_id,
        'start_date': sd,
        'end_date': ed,
        'hours_used': hours_used,
        'locked_hourly_rate': equipment.hourly_rate
    })
    db.session.commit()
    return True, "Equipment assigned to task successfully!"


def validate_and_allocate_material(project_id, material_id, quantity_raw):
    """
    Validates delivered purchase stock for project, checks allocation limits,
    and upserts into material_usage.
    Returns (success: bool, message: str)
    """
    try:
        quantity = float(quantity_raw if quantity_raw is not None else 0)
    except (ValueError, TypeError):
        return False, "Invalid allocation quantity."

    if not material_id or quantity <= 0:
        return False, "Please select a valid material and enter a quantity greater than zero."

    delivered_stock = db.session.execute(text("""
        SELECT COALESCE(SUM(pi.quantity), 0)
        FROM purchase_items pi
        JOIN purchases p ON pi.purchase_id = p.purchase_id
        WHERE p.project_id = :project_id
          AND pi.material_id = :material_id
          AND p.status IN ('Delivered', 'Completed')
    """), {'project_id': project_id, 'material_id': material_id}).scalar() or 0

    existing_alloc = db.session.execute(text("""
        SELECT quantity_allocated FROM material_usage
        WHERE project_id = :project_id AND material_id = :material_id
    """), {'project_id': project_id, 'material_id': material_id}).scalar() or 0

    material_info = db.session.execute(
        text("SELECT material_name, unit FROM materials WHERE material_id = :id"),
        {'id': material_id}
    ).fetchone()

    if not material_info:
        return False, "Material not found."

    new_total_alloc = float(existing_alloc) + quantity
    if new_total_alloc > float(delivered_stock):
        available = max(0.0, float(delivered_stock) - float(existing_alloc))
        return False, f"Cannot allocate {quantity} {material_info.unit}. Only {available:.2f} {material_info.unit} of delivered stock is available for allocation on this project."

    db.session.execute(text("""
        INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
        VALUES (:project_id, :material_id, :qty, 0)
        ON CONFLICT (project_id, material_id)
        DO UPDATE SET quantity_allocated = material_usage.quantity_allocated + EXCLUDED.quantity_allocated
    """), {'project_id': project_id, 'material_id': material_id, 'qty': quantity})
    db.session.commit()
    return True, f"Successfully allocated {quantity} {material_info.unit} of {material_info.material_name} to this project."


def validate_and_consume_material(project_id, usage_id, quantity_raw):
    """
    Validates that consumption quantity does not exceed remaining allocated balance,
    and updates material_usage.quantity_used.
    Returns (success: bool, message: str)
    """
    try:
        quantity = float(quantity_raw if quantity_raw is not None else 0)
    except (ValueError, TypeError):
        return False, "Invalid consumed quantity."

    if not usage_id or quantity <= 0:
        return False, "Please enter a valid consumption quantity greater than zero."

    usage_row = db.session.execute(text("""
        SELECT mu.usage_id, mu.quantity_allocated, mu.quantity_used, m.material_name, m.unit
        FROM material_usage mu
        JOIN materials m ON mu.material_id = m.material_id
        WHERE mu.usage_id = :usage_id AND mu.project_id = :project_id
    """), {'usage_id': usage_id, 'project_id': project_id}).fetchone()

    if not usage_row:
        return False, "Material allocation record not found for this project."

    new_used = float(usage_row.quantity_used) + quantity
    if new_used > float(usage_row.quantity_allocated):
        available_to_consume = max(0.0, float(usage_row.quantity_allocated) - float(usage_row.quantity_used))
        return False, f"Cannot record consumption of {quantity} {usage_row.unit}. It exceeds the allocated limit! Maximum available to consume is {available_to_consume:.2f} {usage_row.unit}."

    db.session.execute(text("""
        UPDATE material_usage
        SET quantity_used = quantity_used + :qty
        WHERE usage_id = :usage_id
    """), {'qty': quantity, 'usage_id': usage_id})
    db.session.commit()
    return True, f"Recorded consumption of {quantity} {usage_row.unit} of {usage_row.material_name}."
