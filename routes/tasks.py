from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


# ── LIST ALL TASK TYPES ──────────────────────────────────────
@tasks_bp.route('/')
@login_required
def list_tasks():
    """List all reusable task types with the count of projects using each."""
    task_types = db.session.execute(text("""
        SELECT tt.task_type_id, tt.task_name, tt.description,
               COUNT(pt.project_task_id) AS project_count
        FROM task_types tt
        LEFT JOIN project_tasks pt ON tt.task_type_id = pt.task_type_id
        GROUP BY tt.task_type_id
        ORDER BY tt.task_type_id
    """)).fetchall()
    return render_template('tasks/list.html', task_types=task_types)


# ── VIEW TASK TYPE DETAILS + ALL PROJECTS USING IT ───────────
@tasks_bp.route('/<int:task_type_id>')
@login_required
def view_task(task_type_id):
    """View a task type and all projects where it is being performed."""
    task_type = db.session.execute(text("""
        SELECT * FROM task_types WHERE task_type_id = :id
    """), {'id': task_type_id}).fetchone()

    if not task_type:
        flash("Task type not found.", "danger")
        return redirect(url_for('tasks.list_tasks'))

    # All projects using this task type, with per-project progress
    project_instances = db.session.execute(text("""
        SELECT pt.project_task_id, pt.completion_percentage, pt.status,
               pt.start_date, pt.due_date, pt.description,
               p.project_id, p.project_name
        FROM project_tasks pt
        JOIN projects p ON pt.project_id = p.project_id
        WHERE pt.task_type_id = :task_type_id
        ORDER BY p.project_name
    """), {'task_type_id': task_type_id}).fetchall()

    return render_template('tasks/view.html', task_type=task_type, project_instances=project_instances)


# ── CREATE NEW TASK TYPE ─────────────────────────────────────
@tasks_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_task():
    """Create a new reusable task type."""
    if request.method == 'POST':
        task_name = request.form['task_name']
        description = request.form.get('description', '')

        db.session.execute(text("""
            INSERT INTO task_types (task_name, description)
            VALUES (:task_name, :description)
        """), {'task_name': task_name, 'description': description})
        db.session.commit()
        flash('Task type created successfully!', 'success')
        return redirect(url_for('tasks.list_tasks'))

    return render_template('tasks/form.html', task_type=None)


# ── EDIT TASK TYPE ───────────────────────────────────────────
@tasks_bp.route('/<int:task_type_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_type_id):
    """Edit a task type's name and description."""
    if request.method == 'POST':
        task_name = request.form['task_name']
        description = request.form.get('description', '')

        db.session.execute(text("""
            UPDATE task_types SET task_name=:task_name, description=:description
            WHERE task_type_id=:id
        """), {'task_name': task_name, 'description': description, 'id': task_type_id})
        db.session.commit()
        flash('Task type updated successfully!', 'success')
        return redirect(url_for('tasks.view_task', task_type_id=task_type_id))

    task_type = db.session.execute(text("SELECT * FROM task_types WHERE task_type_id = :id"),
                                   {'id': task_type_id}).fetchone()
    return render_template('tasks/form.html', task_type=task_type)


# ── ASSIGN TASK TYPE TO A PROJECT ────────────────────────────
@tasks_bp.route('/<int:task_type_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_task(task_type_id):
    """Assign a task type to a project, creating a project_tasks record."""
    task_type = db.session.execute(text("SELECT * FROM task_types WHERE task_type_id = :id"),
                                   {'id': task_type_id}).fetchone()
    if not task_type:
        flash("Task type not found.", "danger")
        return redirect(url_for('tasks.list_tasks'))

    if request.method == 'POST':
        project_id = request.form['project_id']
        start_date = request.form['start_date']
        due_date = request.form['due_date']
        status = request.form['status']
        completion_percentage = request.form['completion_percentage']
        description = request.form.get('description', '')

        db.session.execute(text("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (:project_id, :task_type_id, :start_date, :due_date, :status, :completion_percentage, :description)
        """), {
            'project_id': project_id, 'task_type_id': task_type_id,
            'start_date': start_date, 'due_date': due_date,
            'status': status, 'completion_percentage': completion_percentage,
            'description': description
        })
        db.session.commit()
        flash(f'"{task_type.task_name}" assigned to project successfully!', 'success')
        return redirect(url_for('tasks.view_task', task_type_id=task_type_id))

    # Fetch projects that DON'T already have this task type assigned
    projects = db.session.execute(text("""
        SELECT p.project_id, p.project_name
        FROM projects p
        WHERE p.project_id NOT IN (
            SELECT pt.project_id FROM project_tasks pt WHERE pt.task_type_id = :task_type_id
        )
        ORDER BY p.project_name
    """), {'task_type_id': task_type_id}).fetchall()

    return render_template('tasks/assign.html', task_type=task_type, projects=projects)


# ── EDIT A PROJECT-SPECIFIC TASK INSTANCE ────────────────────
@tasks_bp.route('/project-task/<int:project_task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project_task(project_task_id):
    """Edit the project-specific details of a task (dates, status, progress)."""
    if request.method == 'POST':
        start_date = request.form['start_date']
        due_date = request.form['due_date']
        status = request.form['status']
        completion_percentage = request.form['completion_percentage']
        description = request.form.get('description', '')

        db.session.execute(text("""
            UPDATE project_tasks SET
                start_date=:start_date, due_date=:due_date,
                status=:status, completion_percentage=:completion_percentage,
                description=:description
            WHERE project_task_id=:id
        """), {
            'start_date': start_date, 'due_date': due_date,
            'status': status, 'completion_percentage': completion_percentage,
            'description': description, 'id': project_task_id
        })
        db.session.commit()
        flash('Project task updated successfully!', 'success')

        # Redirect back to the task type view
        pt = db.session.execute(text("SELECT task_type_id FROM project_tasks WHERE project_task_id = :id"),
                                {'id': project_task_id}).fetchone()
        return redirect(url_for('tasks.view_task', task_type_id=pt.task_type_id))

    # Fetch the project task with its task type name and project name
    pt = db.session.execute(text("""
        SELECT pt.*, tt.task_name, p.project_name
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        JOIN projects p ON pt.project_id = p.project_id
        WHERE pt.project_task_id = :id
    """), {'id': project_task_id}).fetchone()

    if not pt:
        flash("Project task not found.", "danger")
        return redirect(url_for('tasks.list_tasks'))

    return render_template('tasks/edit_project_task.html', pt=pt)
