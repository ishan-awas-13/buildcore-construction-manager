from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

equipment_bp = Blueprint('equipment', __name__, url_prefix='/equipment')

@equipment_bp.route('/')
@login_required
def list_equipment():
    equipment = db.session.execute(text("""
        SELECT equipment_id, equipment_name, equipment_type, computed_status as status, hourly_rate
        FROM equipment_status_view
        ORDER BY equipment_id DESC
    """)).fetchall()
    return render_template('equipment/list.html', equipment=equipment)

@equipment_bp.route('/<int:equipment_id>')
@login_required
def view_equipment(equipment_id):
    eq = db.session.execute(text("""
        SELECT *, computed_status as status FROM equipment_status_view WHERE equipment_id = :id
    """), {'id': equipment_id}).fetchone()
    
    if not eq:
        flash("Equipment not found.", "danger")
        return redirect(url_for('equipment.list_equipment'))
        
    # Fetch all assignments for this equipment
    assignments = db.session.execute(text("""
        SELECT ea.assignment_id, ea.start_date, ea.end_date, ea.hours_used,
               p.project_id, p.project_name, tt.task_name, pt.status as task_status
        FROM equipment_assignments ea
        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        JOIN projects p ON pt.project_id = p.project_id
        WHERE ea.equipment_id = :id
        ORDER BY ea.start_date DESC
    """), {'id': equipment_id}).fetchall()
        
    active_projects = db.session.execute(text("""
        SELECT project_id, project_name FROM projects WHERE status != 'Completed' ORDER BY project_name
    """)).fetchall()
        
    return render_template('equipment/view.html', equipment=eq, assignments=assignments, active_projects=active_projects)

@equipment_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_equipment():
    if request.method == 'POST':
        equipment_name = request.form['equipment_name']
        equipment_type = request.form['equipment_type']
        status = request.form['status']
        hourly_rate = request.form['hourly_rate']
        
        db.session.execute(text("""
            INSERT INTO equipment (equipment_name, equipment_type, status, hourly_rate)
            VALUES (:name, :type, :status, :rate)
        """), {
            'name': equipment_name, 'type': equipment_type,
            'status': status, 'rate': hourly_rate
        })
        db.session.commit()
        flash('Equipment added successfully!', 'success')
        return redirect(url_for('equipment.list_equipment'))
        
    return render_template('equipment/form.html', equipment=None)

@equipment_bp.route('/<int:equipment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_equipment(equipment_id):
    if request.method == 'POST':
        equipment_name = request.form['equipment_name']
        equipment_type = request.form['equipment_type']
        status = request.form['status']
        hourly_rate = request.form['hourly_rate']
        
        db.session.execute(text("""
            UPDATE equipment SET 
                equipment_name=:name, equipment_type=:type, 
                status=:status, hourly_rate=:rate
            WHERE equipment_id=:id
        """), {
            'name': equipment_name, 'type': equipment_type,
            'status': status, 'rate': hourly_rate, 'id': equipment_id
        })
        db.session.commit()
        flash('Equipment updated successfully!', 'success')
        return redirect(url_for('equipment.view_equipment', equipment_id=equipment_id))
        
    eq = db.session.execute(text("SELECT * FROM equipment WHERE equipment_id = :id"), 
                            {'id': equipment_id}).fetchone()
    return render_template('equipment/form.html', equipment=eq)

@equipment_bp.route('/<int:equipment_id>/assign', methods=['POST'])
@login_required
def assign_equipment(equipment_id):
    project_task_id = request.form.get('project_task_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date') or None
    hours_used = request.form.get('hours_used', 0)
    
    if not project_task_id or not start_date:
        flash("Task and Start Date are required.", "danger")
        return redirect(url_for('equipment.view_equipment', equipment_id=equipment_id))
        
    db.session.execute(text("""
        INSERT INTO equipment_assignments (equipment_id, project_task_id, start_date, end_date, hours_used)
        VALUES (:equipment_id, :project_task_id, :start_date, :end_date, :hours_used)
    """), {
        'equipment_id': equipment_id,
        'project_task_id': project_task_id,
        'start_date': start_date,
        'end_date': end_date,
        'hours_used': hours_used
    })
    db.session.commit()
    flash("Equipment assigned to task successfully!", "success")
    return redirect(url_for('equipment.view_equipment', equipment_id=equipment_id))
