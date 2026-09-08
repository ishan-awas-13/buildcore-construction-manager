from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

@projects_bp.route('/')
@login_required
def list_projects():
    projects = db.session.execute(text("""
        SELECT p.project_id, p.project_name, p.project_type, p.client_name, 
               p.location, p.budget, p.status, 
               COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        ORDER BY p.project_id DESC
    """)).fetchall()
    return render_template('projects/list.html', projects=projects)

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
    
    # Fetch all tasks assigned to this project (many-to-many via project_tasks)
    project_tasks = db.session.execute(text("""
        SELECT pt.project_task_id, pt.completion_percentage, pt.status,
               pt.start_date, pt.due_date, pt.description,
               tt.task_type_id, tt.task_name
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :project_id
        ORDER BY pt.start_date
    """), {'project_id': project_id}).fetchall()
    
    # Fetch equipment assigned to this project
    project_equipment = db.session.execute(text("""
        SELECT ea.assignment_id, ea.start_date, ea.end_date, ea.hours_used,
               eq.equipment_id, eq.equipment_name, eq.equipment_type,
               tt.task_name
        FROM equipment_assignments ea
        JOIN equipment eq ON ea.equipment_id = eq.equipment_id
        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        WHERE pt.project_id = :project_id
        ORDER BY ea.start_date
    """), {'project_id': project_id}).fetchall()
    
    # Fetch materials allocated to this project
    project_materials = db.session.execute(text("""
        SELECT mu.usage_id, mu.quantity_allocated, mu.quantity_used,
               m.material_id, m.material_name, m.unit, m.unit_cost
        FROM material_usage mu
        JOIN materials m ON mu.material_id = m.material_id
        WHERE mu.project_id = :project_id
        ORDER BY m.material_name
    """), {'project_id': project_id}).fetchall()
        
    return render_template('projects/view.html', project=project, project_tasks=project_tasks, project_equipment=project_equipment, project_materials=project_materials)

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
    from flask import jsonify
    return jsonify(tasks)

@projects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        project_name = request.form['project_name']
        project_type = request.form['project_type']
        client_name = request.form['client_name']
        location = request.form['location']
        start_date = request.form['start_date']
        expected_end_date = request.form['expected_end_date']
        budget = request.form['budget']
        status = request.form['status']
        
        db.session.execute(text("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES (:project_name, :project_type, :client_name, :location, :start_date, :expected_end_date, :budget, :status)
        """), {
            'project_name': project_name, 'project_type': project_type, 
            'client_name': client_name, 'location': location, 
            'start_date': start_date, 'expected_end_date': expected_end_date, 
            'budget': budget, 'status': status
        })
        db.session.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('projects.list_projects'))
        
    return render_template('projects/form.html', project=None)

@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    if request.method == 'POST':
        project_name = request.form['project_name']
        client_name = request.form['client_name']
        project_type = request.form['project_type']
        location = request.form['location']
        start_date = request.form['start_date']
        expected_end_date = request.form['expected_end_date']
        budget = request.form['budget']
        status = request.form['status']
        
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
    
    # Verify the admin password
    if not check_password_hash(current_user.password_hash, password):
        flash('Incorrect admin password. Project deletion failed.', 'danger')
        return redirect(url_for('projects.edit_project', project_id=project_id))
        
    # Delete the project (ON DELETE CASCADE will handle related records in project_tasks, material_usage, etc.)
    db.session.execute(text("DELETE FROM projects WHERE project_id = :id"), {'id': project_id})
    db.session.commit()
    
    flash('Project deleted successfully.', 'success')
    return redirect(url_for('projects.list_projects'))
