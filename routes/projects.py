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
        ORDER BY ea.start_date DESC
    """), {'project_id': project_id}).fetchall()
    
    # Fetch materials allocated to this project + delivered purchases specifically for this project
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

    # Materials with delivered purchases on this project that have unallocated stock available
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
        
    return render_template('projects/view.html', project=project, project_tasks=project_tasks, 
                           project_equipment=project_equipment, project_materials=project_materials,
                           available_to_allocate=available_to_allocate)

@projects_bp.route('/<int:project_id>/materials/allocate', methods=['POST'])
@login_required
def allocate_material(project_id):
    material_id = request.form.get('material_id')
    try:
        quantity = float(request.form.get('quantity_allocated', 0))
    except (ValueError, TypeError):
        flash('Invalid allocation quantity.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    if not material_id or quantity <= 0:
        flash('Please select a valid material and enter a quantity greater than zero.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    # Verify delivered purchase stock specifically for this project
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

    material_info = db.session.execute(text("SELECT material_name, unit FROM materials WHERE material_id = :id"), {'id': material_id}).fetchone()
    if not material_info:
        flash('Material not found.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    new_total_alloc = float(existing_alloc) + quantity
    if new_total_alloc > float(delivered_stock):
        available = max(0.0, float(delivered_stock) - float(existing_alloc))
        flash(f"Cannot allocate {quantity} {material_info.unit}. Only {available:.2f} {material_info.unit} of delivered stock is available for allocation on this project.", 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    db.session.execute(text("""
        INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
        VALUES (:project_id, :material_id, :qty, 0)
        ON CONFLICT (project_id, material_id)
        DO UPDATE SET quantity_allocated = material_usage.quantity_allocated + EXCLUDED.quantity_allocated
    """), {'project_id': project_id, 'material_id': material_id, 'qty': quantity})
    db.session.commit()

    flash(f"Successfully allocated {quantity} {material_info.unit} of {material_info.material_name} to this project.", 'success')
    return redirect(url_for('projects.view_project', project_id=project_id))

@projects_bp.route('/<int:project_id>/materials/consume', methods=['POST'])
@login_required
def consume_material(project_id):
    usage_id = request.form.get('usage_id')
    try:
        quantity = float(request.form.get('quantity_consumed', 0))
    except (ValueError, TypeError):
        flash('Invalid consumed quantity.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    if not usage_id or quantity <= 0:
        flash('Please enter a valid consumption quantity greater than zero.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    usage_row = db.session.execute(text("""
        SELECT mu.usage_id, mu.quantity_allocated, mu.quantity_used, m.material_name, m.unit
        FROM material_usage mu
        JOIN materials m ON mu.material_id = m.material_id
        WHERE mu.usage_id = :usage_id AND mu.project_id = :project_id
    """), {'usage_id': usage_id, 'project_id': project_id}).fetchone()

    if not usage_row:
        flash('Material allocation record not found for this project.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    new_used = float(usage_row.quantity_used) + quantity
    if new_used > float(usage_row.quantity_allocated):
        available_to_consume = max(0.0, float(usage_row.quantity_allocated) - float(usage_row.quantity_used))
        flash(f"Cannot record consumption of {quantity} {usage_row.unit}. It exceeds the allocated limit! Maximum available to consume is {available_to_consume:.2f} {usage_row.unit}.", 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))

    db.session.execute(text("""
        UPDATE material_usage
        SET quantity_used = quantity_used + :qty
        WHERE usage_id = :usage_id
    """), {'qty': quantity, 'usage_id': usage_id})
    db.session.commit()

    flash(f"Recorded consumption of {quantity} {usage_row.unit} of {usage_row.material_name}.", 'success')
    return redirect(url_for('projects.view_project', project_id=project_id))

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
