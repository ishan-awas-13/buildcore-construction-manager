from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import text
from app import db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    # 1. Total Projects, Active Projects, Completed Projects
    proj_stats = db.session.execute(text("""
        SELECT 
            COUNT(*) as total_projects,
            SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_projects,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_projects
        FROM projects
    """)).fetchone()

    # 2. Total Workers, Available Equipment
    workers_count = db.session.execute(text("SELECT COUNT(*) FROM workers")).scalar()
    equipment_count = db.session.execute(text("SELECT COUNT(*) FROM equipment WHERE status = 'Available'")).scalar()

    # 3. Total Material Purchases, Total Project Expenses
    total_purchases = db.session.execute(text("SELECT COALESCE(SUM(total_amount), 0) FROM purchases_with_total_view")).scalar()
    total_expenses = db.session.execute(text("SELECT COALESCE(SUM(amount), 0) FROM expenses")).scalar()

    # 4. List of active projects (with progress from our view)
    active_projects = db.session.execute(text("""
        SELECT p.project_id, p.project_name, p.project_type, p.location, p.budget, p.status, 
               COALESCE(pv.progress_percentage, 0) as progress
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE p.status = 'Active'
    """)).fetchall()

    return render_template('dashboard.html', 
                           proj_stats=proj_stats,
                           workers_count=workers_count,
                           equipment_count=equipment_count,
                           total_purchases=total_purchases,
                           total_expenses=total_expenses,
                           active_projects=active_projects)
