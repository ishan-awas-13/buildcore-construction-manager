from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from sqlalchemy import text
from extensions import db
from routes.helpers import (
    validate_and_assign_task,
    validate_and_assign_worker,
    validate_and_assign_equipment,
    validate_and_allocate_material,
    validate_and_consume_material
)

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

# ─── 1. PROJECT LIST WITH STATUS FILTERING ────────────────────────────
@projects_bp.route('/')
@login_required
def list_projects():
    status_filter = request.args.get('status', 'All').strip()
    
    # Query status counts for the filter pills
    counts_data = db.session.execute(text("""
        SELECT status, COUNT(*) as cnt 
        FROM projects 
        GROUP BY status
    """)).fetchall()
    
    status_counts = {'All': 0, 'Active': 0, 'Planned': 0, 'On Hold': 0, 'Completed': 0}
    for r in counts_data:
        status_counts['All'] += r.cnt
        st = r.status
        if st in ('Planned', 'Planning'):
            status_counts['Planned'] += r.cnt
        elif st in status_counts:
            status_counts[st] += r.cnt

    if status_filter == 'Planned':
        query = text("""
            SELECT p.project_id, p.project_name, p.project_type, p.client_name, 
                   p.location, p.budget, p.status, 
                   COALESCE(pv.progress_percentage, 0) as progress
            FROM projects p
            LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
            WHERE p.status IN ('Planned', 'Planning')
            ORDER BY p.project_id DESC
        """)
        projects = db.session.execute(query).fetchall()
    elif status_filter in ('Active', 'On Hold', 'Completed'):
        query = text("""
            SELECT p.project_id, p.project_name, p.project_type, p.client_name, 
                   p.location, p.budget, p.status, 
                   COALESCE(pv.progress_percentage, 0) as progress
            FROM projects p
            LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
            WHERE p.status = :status
            ORDER BY p.project_id DESC
        """)
        projects = db.session.execute(query, {'status': status_filter}).fetchall()
    else:
        status_filter = 'All'
        query = text("""
            SELECT p.project_id, p.project_name, p.project_type, p.client_name, 
                   p.location, p.budget, p.status, 
                   COALESCE(pv.progress_percentage, 0) as progress
            FROM projects p
            LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
            ORDER BY p.project_id DESC
        """)
        projects = db.session.execute(query).fetchall()

    return render_template('projects/list.html', 
                           projects=projects, 
                           current_status=status_filter, 
                           status_counts=status_counts)


# ─── 2. PROJECT WORKSPACE: OVERVIEW TAB ────────────────────────────────
@projects_bp.route('/<int:project_id>')
@login_required
def view_project(project_id):
    project = db.session.execute(text("""
        SELECT p.*, COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id}).fetchone()
    
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    # Task metrics
    task_counts = db.session.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'In Progress') as active,
            COUNT(*) FILTER (WHERE status = 'Completed') as completed,
            COUNT(*) FILTER (WHERE status = 'Not Started') as not_started
        FROM project_tasks
        WHERE project_id = :id
    """), {'id': project_id}).fetchone()

    # Resource counts
    worker_count = db.session.execute(text("""
        SELECT COUNT(DISTINCT tw.worker_id)
        FROM task_workers tw
        JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
        WHERE pt.project_id = :id
    """), {'id': project_id}).scalar() or 0

    equipment_count = db.session.execute(text("""
        SELECT COUNT(DISTINCT ea.equipment_id)
        FROM equipment_assignments ea
        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
        WHERE pt.project_id = :id
    """), {'id': project_id}).scalar() or 0

    material_lines_count = db.session.execute(text("""
        SELECT COUNT(*) FROM material_usage WHERE project_id = :id
    """), {'id': project_id}).scalar() or 0

    po_count = db.session.execute(text("""
        SELECT COUNT(*) FROM purchases WHERE project_id = :id
    """), {'id': project_id}).scalar() or 0

    # Financial overview
    total_spend = db.session.execute(text("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expense_ledger_view
        WHERE project_id = :id
    """), {'id': project_id}).scalar() or 0

    budget = float(project.budget or 0)
    total_spend = float(total_spend)
    remaining_budget = budget - total_spend
    budget_used_pct = (total_spend / budget * 100) if budget > 0 else 0

    # Recent activity / snapshot
    recent_tasks = db.session.execute(text("""
        SELECT pt.project_task_id, tt.task_name, pt.status, pt.completion_percentage, pt.due_date
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :id
        ORDER BY pt.due_date ASC
        LIMIT 5
    """), {'id': project_id}).fetchall()

    return render_template(
        'projects/overview.html',
        project=project,
        active_tab='overview',
        task_counts=task_counts,
        worker_count=worker_count,
        equipment_count=equipment_count,
        material_lines_count=material_lines_count,
        po_count=po_count,
        total_spend=total_spend,
        remaining_budget=remaining_budget,
        budget_used_pct=budget_used_pct,
        recent_tasks=recent_tasks
    )


# ─── 3. PROJECT WORKSPACE: TASKS TAB ──────────────────────────────────
@projects_bp.route('/<int:project_id>/tasks')
@login_required
def project_tasks_tab(project_id):
    project = db.session.execute(text("""
        SELECT p.*, COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id}).fetchone()
    
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    tasks = db.session.execute(text("""
        SELECT pt.project_task_id, pt.completion_percentage, pt.status,
               pt.start_date, pt.due_date, pt.description,
               tt.task_type_id, tt.task_name,
               COALESCE(tw_cnt.worker_count, 0) as worker_count,
               COALESCE(ea_cnt.equipment_count, 0) as equipment_count
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        LEFT JOIN (
            SELECT project_task_id, COUNT(DISTINCT worker_id) as worker_count 
            FROM task_workers GROUP BY project_task_id
        ) tw_cnt ON pt.project_task_id = tw_cnt.project_task_id
        LEFT JOIN (
            SELECT project_task_id, COUNT(DISTINCT equipment_id) as equipment_count 
            FROM equipment_assignments GROUP BY project_task_id
        ) ea_cnt ON pt.project_task_id = ea_cnt.project_task_id
        WHERE pt.project_id = :project_id
        ORDER BY pt.start_date
    """), {'project_id': project_id}).fetchall()

    # Available task types not already assigned to this project
    available_task_types = db.session.execute(text("""
        SELECT tt.task_type_id, tt.task_name, tt.description
        FROM task_types tt
        WHERE tt.task_type_id NOT IN (
            SELECT pt.task_type_id FROM project_tasks pt WHERE pt.project_id = :project_id
        )
        ORDER BY tt.task_name
    """), {'project_id': project_id}).fetchall()

    return render_template(
        'projects/tasks.html',
        project=project,
        active_tab='tasks',
        tasks=tasks,
        available_task_types=available_task_types
    )


@projects_bp.route('/<int:project_id>/tasks/add', methods=['POST'])
@login_required
def add_project_task(project_id):
    task_type_id = request.form.get('task_type_id')
    start_date = request.form.get('start_date')
    due_date = request.form.get('due_date')
    status = request.form.get('status', 'Not Started')
    completion_percentage = request.form.get('completion_percentage', 0)
    description = request.form.get('description', '')

    if not task_type_id:
        flash("Please select a task type.", "danger")
        return redirect(url_for('projects.project_tasks_tab', project_id=project_id))

    success, msg, _ = validate_and_assign_task(
        project_id=project_id,
        task_type_id=task_type_id,
        start_date_str=start_date,
        due_date_str=due_date,
        status=status,
        completion_percentage_raw=completion_percentage,
        description=description
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for('projects.project_tasks_tab', project_id=project_id))


# ─── 4. PROJECT WORKSPACE: WORKERS TAB ────────────────────────────────
@projects_bp.route('/<int:project_id>/workers')
@login_required
def project_workers_tab(project_id):
    project = db.session.execute(text("""
        SELECT p.*, COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id}).fetchone()
    
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    # Workers assigned to tasks in this project
    assignments = db.session.execute(text("""
        SELECT tw.task_worker_id, tw.assigned_hours, tw.locked_daily_rate,
               ((tw.assigned_hours / 8.0) * tw.locked_daily_rate) as total_cost,
               w.worker_id, w.name as worker_name, w.role, w.skill, w.phone, w.status as worker_current_status,
               pt.project_task_id, tt.task_name, pt.status as task_status, pt.start_date as task_start_date, pt.due_date as task_due_date
        FROM task_workers tw
        JOIN workers w ON tw.worker_id = w.worker_id
        JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :project_id
        ORDER BY tt.task_name, w.name
    """), {'project_id': project_id}).fetchall()

    # Eligible project tasks for assignment modal (active/not completed)
    project_tasks = db.session.execute(text("""
        SELECT pt.project_task_id, tt.task_name, pt.start_date, pt.due_date, pt.status
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :project_id AND pt.status != 'Completed'
        ORDER BY tt.task_name
    """), {'project_id': project_id}).fetchall()

    # Eligible workers (status not On Leave or Inactive)
    eligible_workers = db.session.execute(text("""
        SELECT w.worker_id, w.name, w.role, w.skill, w.daily_rate, w.status
        FROM workers w
        WHERE w.status NOT IN ('On Leave', 'Inactive')
        ORDER BY w.name
    """)).fetchall()

    # Summary calculations
    total_labor_hours = sum(float(a.assigned_hours) for a in assignments)
    total_labor_cost = sum(float(a.total_cost) for a in assignments)

    return render_template(
        'projects/workers.html',
        project=project,
        active_tab='workers',
        assignments=assignments,
        project_tasks=project_tasks,
        eligible_workers=eligible_workers,
        total_labor_hours=total_labor_hours,
        total_labor_cost=total_labor_cost
    )


@projects_bp.route('/<int:project_id>/workers/assign', methods=['POST'])
@login_required
def assign_project_worker(project_id):
    project_task_id = request.form.get('project_task_id')
    worker_id = request.form.get('worker_id')
    assigned_hours = request.form.get('assigned_hours')

    # Security check: verify project_task_id belongs to this project
    task_owner = db.session.execute(text("""
        SELECT project_id FROM project_tasks WHERE project_task_id = :pt_id
    """), {'pt_id': project_task_id}).fetchone()

    if not task_owner or task_owner.project_id != project_id:
        flash("Invalid task selected for this project.", "danger")
        return redirect(url_for('projects.project_workers_tab', project_id=project_id))

    success, msg, is_warn = validate_and_assign_worker(
        project_task_id=project_task_id,
        worker_id=worker_id,
        assigned_hours_raw=assigned_hours
    )

    if success:
        flash(msg, "success")
    elif is_warn:
        flash(msg, "warning")
    else:
        flash(msg, "danger")

    return redirect(url_for('projects.project_workers_tab', project_id=project_id))


# ─── 5. PROJECT WORKSPACE: EQUIPMENT TAB ──────────────────────────────
@projects_bp.route('/<int:project_id>/equipment')
@login_required
def project_equipment_tab(project_id):
    project = db.session.execute(text("""
        SELECT p.*, COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id}).fetchone()
    
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    assignments = db.session.execute(text("""
        SELECT ea.assignment_id, ea.start_date, ea.end_date, ea.hours_used, ea.locked_hourly_rate,
               (ea.hours_used * ea.locked_hourly_rate) as total_cost,
               eq.equipment_id, eq.equipment_name, eq.equipment_type, eq.status as equipment_current_status,
               pt.project_task_id, tt.task_name, pt.status as task_status
        FROM equipment_assignments ea
        JOIN equipment eq ON ea.equipment_id = eq.equipment_id
        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :project_id
        ORDER BY ea.start_date DESC
    """), {'project_id': project_id}).fetchall()

    project_tasks = db.session.execute(text("""
        SELECT pt.project_task_id, tt.task_name, pt.start_date, pt.due_date, pt.status
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :project_id AND pt.status != 'Completed'
        ORDER BY tt.task_name
    """), {'project_id': project_id}).fetchall()

    eligible_equipment = db.session.execute(text("""
        SELECT eq.equipment_id, eq.equipment_name, eq.equipment_type, eq.hourly_rate, eq.computed_status as status
        FROM equipment_status_view eq
        WHERE eq.computed_status NOT IN ('Maintenance', 'Retired')
        ORDER BY eq.equipment_name
    """)).fetchall()

    total_eq_hours = sum(float(a.hours_used) for a in assignments)
    total_eq_cost = sum(float(a.total_cost) for a in assignments)

    # Serialize active tasks for client-side date bounding
    tasks_json = [
        {
            'id': pt.project_task_id,
            'name': pt.task_name,
            'start': pt.start_date.strftime('%Y-%m-%d') if pt.start_date else '',
            'end': pt.due_date.strftime('%Y-%m-%d') if pt.due_date else '',
            'start_fmt': pt.start_date.strftime('%d %b %Y') if pt.start_date else '',
            'end_fmt': pt.due_date.strftime('%d %b %Y') if pt.due_date else ''
        }
        for pt in project_tasks
    ]

    # Query active & upcoming equipment bookings across company to empower live UI guidance
    bookings_query = db.session.execute(text("""
        SELECT ea.equipment_id, ea.start_date, COALESCE(ea.end_date, pt.due_date) as end_date,
               p.project_name, tt.task_name, pt.status as task_status
        FROM equipment_assignments ea
        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
        JOIN projects p ON pt.project_id = p.project_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.status != 'Completed'
           OR (ea.end_date IS NOT NULL AND ea.end_date >= CURRENT_DATE)
        ORDER BY ea.start_date ASC
    """)).fetchall()

    bookings_by_equipment = {}
    for b in bookings_query:
        eq_id = b.equipment_id
        if eq_id not in bookings_by_equipment:
            bookings_by_equipment[eq_id] = []
        bookings_by_equipment[eq_id].append({
            'start': b.start_date.strftime('%Y-%m-%d') if b.start_date else '',
            'end': b.end_date.strftime('%Y-%m-%d') if b.end_date else '',
            'start_fmt': b.start_date.strftime('%d %b %Y') if b.start_date else '',
            'end_fmt': b.end_date.strftime('%d %b %Y') if b.end_date else 'Ongoing',
            'project_name': b.project_name,
            'task_name': b.task_name
        })

    return render_template(
        'projects/equipment.html',
        project=project,
        active_tab='equipment',
        assignments=assignments,
        project_tasks=project_tasks,
        eligible_equipment=eligible_equipment,
        total_eq_hours=total_eq_hours,
        total_eq_cost=total_eq_cost,
        tasks_json=tasks_json,
        bookings_json=bookings_by_equipment
    )


@projects_bp.route('/<int:project_id>/equipment/assign', methods=['POST'])
@login_required
def assign_project_equipment(project_id):
    project_task_id = request.form.get('project_task_id')
    equipment_id = request.form.get('equipment_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date') or None
    hours_used = request.form.get('hours_used', 0)

    # Security check: verify task belongs to project
    task_owner = db.session.execute(text("""
        SELECT project_id FROM project_tasks WHERE project_task_id = :pt_id
    """), {'pt_id': project_task_id}).fetchone()

    if not task_owner or task_owner.project_id != project_id:
        flash("Invalid task selected for this project.", "danger")
        return redirect(url_for('projects.project_equipment_tab', project_id=project_id))

    success, msg = validate_and_assign_equipment(
        project_task_id=project_task_id,
        equipment_id=equipment_id,
        start_date_str=start_date,
        end_date_str=end_date,
        hours_used_raw=hours_used
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for('projects.project_equipment_tab', project_id=project_id))


# ─── 6. PROJECT WORKSPACE: MATERIALS TAB ──────────────────────────────
@projects_bp.route('/<int:project_id>/materials')
@login_required
def project_materials_tab(project_id):
    project = db.session.execute(text("""
        SELECT p.*, COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id}).fetchone()
    
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    project_materials = db.session.execute(text("""
        SELECT 
            m.material_id, 
            m.material_name, 
            m.unit,
            COALESCE(purchased.total_purchased, 0) AS total_purchased,
            COALESCE(purchased.total_purchased, 0) AS total_delivered,
            COALESCE(mu.usage_id, 0) AS usage_id,
            COALESCE(mu.quantity_allocated, 0) AS quantity_allocated,
            COALESCE(mu.quantity_used, 0) AS quantity_used
        FROM materials m
        LEFT JOIN (
            SELECT pi.material_id, SUM(pi.quantity) AS total_purchased
            FROM purchase_items pi
            JOIN purchases p ON pi.purchase_id = p.purchase_id
            WHERE p.project_id = :project_id AND p.status IN ('Delivered', 'Completed')
            GROUP BY pi.material_id
        ) purchased ON m.material_id = purchased.material_id
        LEFT JOIN material_usage mu ON mu.project_id = :project_id AND mu.material_id = m.material_id
        WHERE (COALESCE(purchased.total_purchased, 0) > 0 OR COALESCE(mu.quantity_allocated, 0) > 0)
        ORDER BY m.material_name
    """), {'project_id': project_id}).fetchall()

    available_to_allocate = db.session.execute(text("""
        SELECT m.material_id, m.material_name, m.unit,
               SUM(pi.quantity) AS total_purchased,
               COALESCE(mu.quantity_allocated, 0) AS total_allocated,
               (SUM(pi.quantity) - COALESCE(mu.quantity_allocated, 0)) AS available_qty
        FROM purchase_items pi
        JOIN purchases p ON pi.purchase_id = p.purchase_id
        JOIN materials m ON pi.material_id = m.material_id
        LEFT JOIN material_usage mu ON mu.project_id = :project_id AND mu.material_id = m.material_id
        WHERE p.project_id = :project_id AND p.status IN ('Delivered', 'Completed')
        GROUP BY m.material_id, m.material_name, m.unit, mu.quantity_allocated
        HAVING (SUM(pi.quantity) - COALESCE(mu.quantity_allocated, 0)) > 0
        ORDER BY m.material_name
    """), {'project_id': project_id}).fetchall()

    return render_template(
        'projects/materials.html',
        project=project,
        active_tab='materials',
        project_materials=project_materials,
        available_to_allocate=available_to_allocate
    )


@projects_bp.route('/<int:project_id>/materials/allocate', methods=['POST'])
@login_required
def allocate_material(project_id):
    material_id = request.form.get('material_id')
    quantity = request.form.get('quantity_allocated')

    success, msg = validate_and_allocate_material(
        project_id=project_id,
        material_id=material_id,
        quantity_raw=quantity
    )

    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('projects.project_materials_tab', project_id=project_id))


@projects_bp.route('/<int:project_id>/materials/consume', methods=['POST'])
@login_required
def consume_material(project_id):
    usage_id = request.form.get('usage_id')
    quantity = request.form.get('quantity_consumed')

    success, msg = validate_and_consume_material(
        project_id=project_id,
        usage_id=usage_id,
        quantity_raw=quantity
    )

    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('projects.project_materials_tab', project_id=project_id))


# ─── 7. PROJECT WORKSPACE: PURCHASES TAB ──────────────────────────────
@projects_bp.route('/<int:project_id>/purchases')
@login_required
def project_purchases_tab(project_id):
    project = db.session.execute(text("""
        SELECT p.*, COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id}).fetchone()
    
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    purchases = db.session.execute(text("""
        SELECT p.purchase_id, p.purchase_date, p.status, p.total_amount,
               s.supplier_name, s.supplier_id,
               COALESCE(item_cnt.item_count, 0) as item_count
        FROM purchases_with_total_view p
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        LEFT JOIN (
            SELECT purchase_id, COUNT(*) as item_count
            FROM purchase_items GROUP BY purchase_id
        ) item_cnt ON p.purchase_id = item_cnt.purchase_id
        WHERE p.project_id = :project_id
        ORDER BY p.purchase_date DESC
    """), {'project_id': project_id}).fetchall()

    total_po_value = sum(float(p.total_amount or 0) for p in purchases)
    recognized_po_spend = sum(
        float(p.total_amount or 0) for p in purchases if p.status in ('Delivered', 'Completed')
    )

    return render_template(
        'projects/purchases.html',
        project=project,
        active_tab='purchases',
        purchases=purchases,
        total_po_value=total_po_value,
        recognized_po_spend=recognized_po_spend
    )


# ─── 8. PROJECT WORKSPACE: FINANCIALS TAB ─────────────────────────────
@projects_bp.route('/<int:project_id>/financials')
@login_required
def project_financials_tab(project_id):
    project = db.session.execute(text("""
        SELECT p.*, COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id}).fetchone()
    
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    category_sql = text("""
        SELECT category, COALESCE(SUM(amount), 0) AS total
        FROM expense_ledger_view
        WHERE project_id = :id
        GROUP BY category
    """)
    category_rows = db.session.execute(category_sql, {'id': project_id}).fetchall()
    
    categories = {'Materials': 0, 'Labour': 0, 'Equipment': 0, 'Other': 0}
    for row in category_rows:
        categories[row.category] = float(row.total)
    
    total_cost = sum(categories.values())
    budget = float(project.budget or 0)
    remaining = budget - total_cost
    budget_used_pct = (total_cost / budget * 100) if budget > 0 else 0
    
    filter_category = request.args.get('category', 'All')
    
    if filter_category and filter_category != 'All':
        ledger_sql = text("""
            SELECT * FROM expense_ledger_view
            WHERE project_id = :id AND category = :cat
            ORDER BY transaction_date DESC
        """)
        ledger = db.session.execute(ledger_sql, {'id': project_id, 'cat': filter_category}).fetchall()
    else:
        ledger_sql = text("""
            SELECT * FROM expense_ledger_view
            WHERE project_id = :id
            ORDER BY transaction_date DESC
        """)
        ledger = db.session.execute(ledger_sql, {'id': project_id}).fetchall()
    
    return render_template(
        'projects/financials.html',
        project=project,
        active_tab='financials',
        categories=categories,
        total_cost=total_cost,
        remaining=remaining,
        budget_used_pct=budget_used_pct,
        ledger=ledger,
        filter_category=filter_category
    )


# ─── API AND UTILITY ROUTES ───────────────────────────────────────────
@projects_bp.route('/<int:project_id>/tasks/api')
@login_required
def api_tasks(project_id):
    project_tasks = db.session.execute(text("""
        SELECT pt.project_task_id, tt.task_name, pt.status
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :project_id
        ORDER BY tt.task_name
    """), {'project_id': project_id}).fetchall()
    
    tasks = [{'id': pt.project_task_id, 'name': pt.task_name, 'status': pt.status} for pt in project_tasks]
    return jsonify(tasks)


@projects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        project_type = request.form['project_type'].strip()
        client_name = request.form['client_name'].strip()
        location = request.form['location'].strip()
        start_date = request.form['start_date']
        expected_end_date = request.form['expected_end_date']
        status = request.form['status'].strip()
        
        try:
            budget = float(request.form['budget'])
        except (ValueError, TypeError):
            flash('Invalid budget amount. Please enter a valid number.', 'danger')
            return redirect(url_for('projects.add_project'))
            
        if budget < 0:
            flash('Project budget cannot be negative.', 'danger')
            return redirect(url_for('projects.add_project'))
        
        result = db.session.execute(text("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES (:project_name, :project_type, :client_name, :location, :start_date, :expected_end_date, :budget, :status)
            RETURNING project_id
        """), {
            'project_name': project_name, 'project_type': project_type, 
            'client_name': client_name, 'location': location, 
            'start_date': start_date, 'expected_end_date': expected_end_date, 
            'budget': budget, 'status': status
        })
        new_project_id = result.fetchone()[0]
        db.session.commit()
        flash('Project added successfully! Welcome to your project workspace.', 'success')
        return redirect(url_for('projects.view_project', project_id=new_project_id))
        
    return render_template('projects/form.html', project=None)


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        client_name = request.form['client_name'].strip()
        project_type = request.form['project_type'].strip()
        location = request.form['location'].strip()
        start_date = request.form['start_date']
        expected_end_date = request.form['expected_end_date']
        status = request.form['status'].strip()
        
        try:
            budget = float(request.form['budget'])
        except (ValueError, TypeError):
            flash('Invalid budget amount. Please enter a valid number.', 'danger')
            return redirect(url_for('projects.edit_project', project_id=project_id))
            
        if budget < 0:
            flash('Project budget cannot be negative.', 'danger')
            return redirect(url_for('projects.edit_project', project_id=project_id))
        
        db.session.execute(text("""
            UPDATE projects SET 
                project_name=:name, client_name=:client, project_type=:type, 
                location=:loc, start_date=:start, expected_end_date=:end, 
                budget=:budget, status=:status
            WHERE project_id=:id
        """), {
            'name': project_name, 'client': client_name, 'type': project_type,
            'loc': location, 'start': start_date, 'end': expected_end_date,
            'budget': budget, 'status': status, 'id': project_id
        })
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects.view_project', project_id=project_id))
        
    project = db.session.execute(text("SELECT * FROM projects WHERE project_id = :id"), 
                                 {'id': project_id}).fetchone()
    return render_template('projects/form.html', project=project)


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    from werkzeug.security import check_password_hash
    from flask_login import current_user
    
    password = request.form.get('admin_password')
    
    # 1. Verify the admin password
    if not password or not check_password_hash(current_user.password_hash, password):
        flash('Incorrect admin password. Project deletion failed.', 'danger')
        return redirect(url_for('projects.edit_project', project_id=project_id))

    project = db.session.execute(text("SELECT project_id, project_name FROM projects WHERE project_id = :id"), {'id': project_id}).fetchone()
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('projects.list_projects'))

    # 2. History Protection: Audit whether project has historical transactions or assignments
    po_count = db.session.execute(text("SELECT COUNT(*) FROM purchases WHERE project_id = :id"), {'id': project_id}).scalar() or 0
    exp_count = db.session.execute(text("SELECT COUNT(*) FROM expenses WHERE project_id = :id"), {'id': project_id}).scalar() or 0
    tw_count = db.session.execute(text("""
        SELECT COUNT(*) 
        FROM task_workers tw
        JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
        WHERE pt.project_id = :id
    """), {'id': project_id}).scalar() or 0
    ea_count = db.session.execute(text("""
        SELECT COUNT(*) 
        FROM equipment_assignments ea
        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
        WHERE pt.project_id = :id
    """), {'id': project_id}).scalar() or 0
    mu_count = db.session.execute(text("""
        SELECT COUNT(*) 
        FROM material_usage 
        WHERE project_id = :id AND (quantity_allocated > 0 OR quantity_used > 0)
    """), {'id': project_id}).scalar() or 0

    reasons = []
    if po_count > 0:
        reasons.append(f"{po_count} purchase order(s)")
    if exp_count > 0:
        reasons.append(f"{exp_count} expense record(s)")
    if tw_count > 0:
        reasons.append(f"{tw_count} worker assignment(s)")
    if ea_count > 0:
        reasons.append(f"{ea_count} equipment assignment(s)")
    if mu_count > 0:
        reasons.append(f"{mu_count} material inventory record(s)")

    if reasons:
        reasons_summary = ", ".join(reasons)
        flash(
            f"Cannot delete project '{project.project_name}': It contains historical audit records ({reasons_summary}). "
            "To preserve accounting, tax, and labor compliance trails, projects with recorded history cannot be deleted.",
            "danger"
        )
        return redirect(url_for('projects.edit_project', project_id=project_id))

    # Safe to delete draft project with zero historical records
    db.session.execute(text("DELETE FROM projects WHERE project_id = :id"), {'id': project_id})
    db.session.commit()
    
    flash(f"Draft project '{project.project_name}' deleted successfully.", 'success')
    return redirect(url_for('projects.list_projects'))
