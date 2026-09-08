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
        daily_rate = request.form['daily_rate']
        status = request.form['status']
        
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
        daily_rate = request.form['daily_rate']
        status = request.form['status']
        
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
    assigned_hours = request.form.get('assigned_hours', 0)
    
    if not project_task_id:
        flash("You must select a task.", "danger")
        return redirect(url_for('workers.view_worker', worker_id=worker_id))
        
    db.session.execute(text("""
        INSERT INTO task_workers (project_task_id, worker_id, assigned_hours)
        VALUES (:project_task_id, :worker_id, :assigned_hours)
    """), {
        'project_task_id': project_task_id,
        'worker_id': worker_id,
        'assigned_hours': assigned_hours
    })
    db.session.commit()
    flash("Worker assigned to task successfully!", "success")
    return redirect(url_for('workers.view_worker', worker_id=worker_id))
