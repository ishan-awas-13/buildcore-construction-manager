from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

financials_bp = Blueprint('financials', __name__, url_prefix='/financials')

# ─── Global Financials Overview (all projects) ───
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

# ─── Project-Specific Financial Dashboard ───
@financials_bp.route('/project/<int:project_id>')
@login_required
def project_dashboard(project_id):
    """The main Financials dashboard for a single project."""
    
    # Get project info
    project = db.session.execute(
        text("SELECT * FROM projects WHERE project_id = :id"),
        {'id': project_id}
    ).fetchone()
    
    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('financials.list_financials'))
    
    # Category totals
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
    
    # Get the full transaction ledger, with optional category filter
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
    
    return render_template('financials/dashboard.html',
        project=project,
        categories=categories,
        total_cost=total_cost,
        remaining=remaining,
        budget_used_pct=budget_used_pct,
        ledger=ledger,
        filter_category=filter_category
    )

# ─── Miscellaneous Expense CRUD ───
@financials_bp.route('/project/<int:project_id>/misc/add', methods=['GET', 'POST'])
@login_required
def add_misc_expense(project_id):
    if request.method == 'POST':
        expense_type = request.form['expense_type']
        amount = request.form['amount']
        expense_date = request.form['expense_date']
        description = request.form.get('description', '')
        
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
        expense_type = request.form['expense_type']
        amount = request.form['amount']
        expense_date = request.form['expense_date']
        description = request.form.get('description', '')
        
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
