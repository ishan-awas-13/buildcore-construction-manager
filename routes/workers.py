from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

workers_bp = Blueprint('workers', __name__, url_prefix='/workers')

@workers_bp.route('/')
@login_required
def list_workers():
    workers = db.session.execute(text("""
        SELECT worker_id, name, role, skill, phone, daily_rate, computed_status as status
        FROM worker_status_view
        ORDER BY worker_id DESC
    """)).fetchall()
    return render_template('workers/list.html', workers=workers)

@workers_bp.route('/<int:worker_id>')
@login_required
def view_worker(worker_id):
    worker = db.session.execute(text("""
        SELECT *, computed_status as status FROM worker_status_view WHERE worker_id = :worker_id
    """), {'worker_id': worker_id}).fetchone()
    
    if not worker:
        flash("Worker not found.", "danger")
        return redirect(url_for('workers.list_workers'))
        
    assignments = db.session.execute(text("""
        SELECT tw.assigned_hours, pt.status as task_status, pt.start_date, pt.due_date,
               tt.task_name, p.project_name, p.project_id
        FROM task_workers tw
        JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        JOIN projects p ON pt.project_id = p.project_id
        WHERE tw.worker_id = :worker_id
        ORDER BY pt.start_date DESC
    """), {'worker_id': worker_id}).fetchall()
    
    active_projects = db.session.execute(text("""
        SELECT project_id, project_name FROM projects WHERE status != 'Completed' ORDER BY project_name
    """)).fetchall()
        
    return render_template('workers/view.html', worker=worker, assignments=assignments, active_projects=active_projects)

@workers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_worker():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        skill = request.form['skill']
        phone = request.form.get('phone', '')
        daily_rate = float(request.form['daily_rate'])
        status = request.form['status']
        
        if daily_rate <= 0:
            flash('Daily rate must be greater than 0.', 'danger')
            return redirect(url_for('workers.add_worker'))
        
        db.session.execute(text("""
            INSERT INTO workers (name, role, skill, phone, daily_rate, status)
            VALUES (:name, :role, :skill, :phone, :daily_rate, :status)
        """), {
            'name': name, 'role': role, 'skill': skill,
            'phone': phone, 'daily_rate': daily_rate, 'status': status
        })
        db.session.commit()
        flash('Worker added successfully!', 'success')
        return redirect(url_for('workers.list_workers'))
        
    return render_template('workers/form.html', worker=None)

@workers_bp.route('/<int:worker_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_worker(worker_id):
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        skill = request.form['skill']
        phone = request.form.get('phone', '')
        daily_rate = float(request.form['daily_rate'])
        status = request.form['status']
        
        if daily_rate <= 0:
            flash('Daily rate must be greater than 0.', 'danger')
            return redirect(url_for('workers.edit_worker', worker_id=worker_id))
        
        db.session.execute(text("""
            UPDATE workers SET 
                name=:name, role=:role, skill=:skill, 
                phone=:phone, daily_rate=:daily_rate, status=:status
            WHERE worker_id=:worker_id
        """), {
            'name': name, 'role': role, 'skill': skill,
            'phone': phone, 'daily_rate': daily_rate, 'status': status, 'worker_id': worker_id
        })
        db.session.commit()
        flash('Worker updated successfully!', 'success')
        return redirect(url_for('workers.view_worker', worker_id=worker_id))
        
    worker = db.session.execute(text("SELECT * FROM workers WHERE worker_id = :worker_id"), 
                                {'worker_id': worker_id}).fetchone()
    return render_template('workers/form.html', worker=worker)

@workers_bp.route('/<int:worker_id>/assign', methods=['POST'])
@login_required
def assign_worker(worker_id):
    project_task_id = request.form.get('project_task_id')
    assigned_hours = float(request.form.get('assigned_hours', 0))
    
    if not project_task_id:
        flash("You must select a task.", "danger")
        return redirect(url_for('workers.view_worker', worker_id=worker_id))
    if assigned_hours <= 0:
        flash("Assigned hours must be greater than 0.", "danger")
        return redirect(url_for('workers.view_worker', worker_id=worker_id))
        
    worker = db.session.execute(text("SELECT worker_id, name, daily_rate, status FROM workers WHERE worker_id = :id"), {'id': worker_id}).fetchone()
    if not worker:
        flash("Worker not found.", "danger")
        return redirect(url_for('workers.list_workers'))

    # 1. Reject inactive or on-leave workers
    if worker.status in ('On Leave', 'Inactive'):
        flash(f"Cannot assign {worker.name}: Worker status is currently '{worker.status}'.", "danger")
        return redirect(url_for('workers.view_worker', worker_id=worker_id))

    # 2. Check if worker is already assigned to this exact task
    existing = db.session.execute(text("""
        SELECT 1 FROM task_workers 
        WHERE worker_id = :w_id AND project_task_id = :pt_id
    """), {'w_id': worker_id, 'pt_id': project_task_id}).fetchone()
    if existing:
        flash("Worker is already assigned to this task.", "warning")
        return redirect(url_for('workers.view_worker', worker_id=worker_id))

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
            flash(
                f"Schedule conflict: {worker.name} is already assigned to '{conflict.task_name}' on '{conflict.project_name}' "
                f"({conflict.start_date.strftime('%Y-%m-%d')} to {conflict.due_date.strftime('%Y-%m-%d')}).",
                "danger"
            )
            return redirect(url_for('workers.view_worker', worker_id=worker_id))

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
    flash("Worker assigned to task successfully!", "success")
    return redirect(url_for('workers.view_worker', worker_id=worker_id))
