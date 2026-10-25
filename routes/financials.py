from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from extensions import db

financials_bp = Blueprint('financials', __name__, url_prefix='/financials')

# Operational categories that are strictly tracked via assignments and POs
# to prevent double-counting in project budgets.
OPERATIONAL_EXPENSE_TYPES = {'labour', 'labor', 'equipment', 'material', 'materials'}

# ─── Global Financials Overview (all projects) ────────────────────────
@financials_bp.route('/')
@login_required
def list_financials():
    """Shows a summary of financial health across all projects."""
    sql = text("""
        SELECT p.project_id, p.project_name, p.budget,
               COALESCE(SUM(el.amount), 0) AS total_cost
        FROM projects p
        LEFT JOIN expense_ledger_view el ON p.project_id = el.project_id
        GROUP BY p.project_id
        ORDER BY p.project_name
    """)
    projects = db.session.execute(sql).fetchall()
    return render_template('financials/list.html', projects=projects)

# ─── Project-Specific Financial Dashboard (Legacy 302 Redirect) ───────
@financials_bp.route('/project/<int:project_id>')
@login_required
def project_dashboard(project_id):
    """The project financial dashboard is now embedded in the Project Workspace.
    Redirect 302 to maintain full backwards compatibility."""
    return redirect(url_for('projects.project_financials_tab', project_id=project_id), code=302)

# ─── Miscellaneous Expense CRUD ───────────────────────────────────────
@financials_bp.route('/project/<int:project_id>/misc/add', methods=['GET', 'POST'])
@login_required
def add_misc_expense(project_id):
    if request.method == 'POST':
        expense_type = request.form['expense_type'].strip()
        expense_date = request.form['expense_date']
        description = request.form.get('description', '').strip()
        
        try:
            amount = float(request.form['amount'])
        except (ValueError, TypeError):
            flash('Please enter a valid numeric amount.', 'danger')
            return redirect(url_for('financials.add_misc_expense', project_id=project_id))
        
        if amount <= 0:
            flash('Expense amount must be strictly greater than zero.', 'danger')
            return redirect(url_for('financials.add_misc_expense', project_id=project_id))
        if not expense_type:
            flash('Expense type cannot be empty.', 'danger')
            return redirect(url_for('financials.add_misc_expense', project_id=project_id))

        # Guard against double-counting operational categories tracked via tasks/POs
        if expense_type.lower() in OPERATIONAL_EXPENSE_TYPES:
            flash('Operational expenses (Labour, Equipment, Materials) are automatically tracked via Task Assignments and Purchase Orders. For site or administrative overhead, please select an approved miscellaneous category.', 'danger')
            return redirect(url_for('financials.add_misc_expense', project_id=project_id))

        sql = text("""
            INSERT INTO expenses (project_id, expense_type, amount, expense_date, description)
            VALUES (:project_id, :expense_type, :amount, :expense_date, :description)
        """)
        db.session.execute(sql, {
            'project_id': project_id,
            'expense_type': expense_type,
            'amount': amount,
            'expense_date': expense_date,
            'description': description
        })
        db.session.commit()
        
        flash('Miscellaneous expense added successfully!', 'success')
        return redirect(url_for('financials.project_dashboard', project_id=project_id))
    
    project = db.session.execute(
        text("SELECT project_id, project_name FROM projects WHERE project_id = :id"),
        {'id': project_id}
    ).fetchone()
    return render_template('financials/misc_form.html', project=project, expense=None)

@financials_bp.route('/misc/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_misc_expense(expense_id):
    expense = db.session.execute(
        text("SELECT * FROM expenses WHERE expense_id = :id"),
        {'id': expense_id}
    ).fetchone()
    
    if not expense:
        flash('Expense not found.', 'danger')
        return redirect(url_for('financials.list_financials'))
    
    if request.method == 'POST':
        expense_type = request.form['expense_type'].strip()
        expense_date = request.form['expense_date']
        description = request.form.get('description', '').strip()
        
        try:
            amount = float(request.form['amount'])
        except (ValueError, TypeError):
            flash('Please enter a valid numeric amount.', 'danger')
            return redirect(url_for('financials.edit_misc_expense', expense_id=expense_id))
        
        if amount <= 0:
            flash('Expense amount must be strictly greater than zero.', 'danger')
            return redirect(url_for('financials.edit_misc_expense', expense_id=expense_id))
        if not expense_type:
            flash('Expense type cannot be empty.', 'danger')
            return redirect(url_for('financials.edit_misc_expense', expense_id=expense_id))
        
        # Guard against double-counting operational categories tracked via tasks/POs
        if expense_type.lower() in OPERATIONAL_EXPENSE_TYPES:
            flash('Operational expenses (Labour, Equipment, Materials) are automatically tracked via Task Assignments and Purchase Orders. For site or administrative overhead, please select an approved miscellaneous category.', 'danger')
            return redirect(url_for('financials.edit_misc_expense', expense_id=expense_id))
        
        sql = text("""
            UPDATE expenses 
            SET expense_type=:expense_type, amount=:amount, expense_date=:expense_date, description=:description
            WHERE expense_id=:id
        """)
        db.session.execute(sql, {
            'expense_type': expense_type,
            'amount': amount,
            'expense_date': expense_date,
            'description': description,
            'id': expense_id
        })
        db.session.commit()
        
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('financials.project_dashboard', project_id=expense.project_id))
    
    project = db.session.execute(
        text("SELECT project_id, project_name FROM projects WHERE project_id = :id"),
        {'id': expense.project_id}
    ).fetchone()
    return render_template('financials/misc_form.html', project=project, expense=expense)

@financials_bp.route('/misc/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_misc_expense(expense_id):
    expense = db.session.execute(
        text("SELECT project_id FROM expenses WHERE expense_id = :id"),
        {'id': expense_id}
    ).fetchone()
    
    if expense:
        db.session.execute(text("DELETE FROM expenses WHERE expense_id = :id"), {'id': expense_id})
        db.session.commit()
        flash('Expense deleted.', 'success')
        return redirect(url_for('financials.project_dashboard', project_id=expense.project_id))
    
    return redirect(url_for('financials.list_financials'))
