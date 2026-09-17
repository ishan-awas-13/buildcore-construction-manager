from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import text
from app import db

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def dashboard():
    # 1. Get filter
    project_id_str = request.args.get('project_id', 'all')
    project_id = None if project_id_str == 'all' else int(project_id_str)

    # Fetch all projects for dropdown
    all_projects = db.session.execute(text("SELECT project_id, project_name FROM projects ORDER BY project_name")).fetchall()

    # Define common query parameters dictionary
    params = {'project_id': project_id}

    # ==========================================
    # REPORT 1: PROJECT PROGRESS
    # ==========================================
    # Get project summaries
    project_summaries = db.session.execute(text("""
        SELECT 
            p.project_id, p.project_name, p.project_type, p.client_name, p.location, 
            p.start_date, p.expected_end_date, p.status, p.budget,
            COALESCE(pv.progress_percentage, 0) as progress_percentage,
            COALESCE(pv.total_tasks, 0) as total_tasks,
            COALESCE(pv.completed_tasks, 0) as completed_tasks
        FROM projects p
        LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
        WHERE (:project_id IS NULL OR p.project_id = :project_id)
        ORDER BY p.project_id DESC
    """), params).fetchall()

    # Get task details
    project_tasks = db.session.execute(text("""
        SELECT pt.project_task_id, tt.task_name, p.project_name, pt.start_date, pt.due_date, pt.status, pt.completion_percentage,
        CASE WHEN CURRENT_DATE > pt.due_date AND pt.status != 'Completed' THEN True ELSE False END as is_overdue
        FROM project_tasks pt
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        JOIN projects p ON pt.project_id = p.project_id
        WHERE (:project_id IS NULL OR pt.project_id = :project_id)
        ORDER BY pt.due_date ASC
    """), params).fetchall()

    # ==========================================
    # REPORT 2: FINANCIAL REPORT
    # ==========================================
    financial_breakdown = db.session.execute(text("""
        SELECT category, SUM(amount) as total_cost 
        FROM expense_ledger_view 
        WHERE (:project_id IS NULL OR project_id = :project_id)
        GROUP BY category
    """), params).fetchall()

    total_budget = sum(p.budget for p in project_summaries)
    total_cost = sum(row.total_cost for row in financial_breakdown) if financial_breakdown else 0
    remaining_budget = total_budget - total_cost
    budget_utilization = (total_cost / total_budget * 100) if total_budget > 0 else 0

    # Recent expenses for table
    recent_expenses = db.session.execute(text("""
        SELECT transaction_date, category, description, amount, source_type
        FROM expense_ledger_view
        WHERE (:project_id IS NULL OR project_id = :project_id)
        ORDER BY transaction_date DESC, transaction_id DESC
        LIMIT 20
    """), params).fetchall()

    # ==========================================
    # REPORT 3: RESOURCE UTILIZATION
    # ==========================================
    worker_utilization = db.session.execute(text("""
        SELECT w.name as worker_name, p.project_name, tt.task_name, tw.assigned_hours, 
               ROUND((tw.assigned_hours / 8.0) * w.daily_rate, 2) as labour_cost
        FROM task_workers tw
        JOIN workers w ON tw.worker_id = w.worker_id
        JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        JOIN projects p ON pt.project_id = p.project_id
        WHERE (:project_id IS NULL OR pt.project_id = :project_id)
        ORDER BY p.project_name, tt.task_name, w.name
    """), params).fetchall()

    equipment_utilization = db.session.execute(text("""
        SELECT e.equipment_name, e.equipment_type, p.project_name, tt.task_name, ea.hours_used,
               ROUND(ea.hours_used * e.hourly_rate, 2) as equipment_cost
        FROM equipment_assignments ea
        JOIN equipment e ON ea.equipment_id = e.equipment_id
        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
        JOIN task_types tt ON pt.task_type_id = tt.task_type_id
        JOIN projects p ON pt.project_id = p.project_id
        WHERE (:project_id IS NULL OR pt.project_id = :project_id)
        ORDER BY p.project_name, tt.task_name, e.equipment_name
    """), params).fetchall()

    # ==========================================
    # REPORT 4: PROCUREMENT & MATERIALS
    # ==========================================
    material_usage_report = db.session.execute(text("""
        SELECT 
            m.material_id, m.material_name, m.unit,
            COALESCE(purchased.total_purchased, 0) as total_purchased,
            COALESCE(purchased.total_cost, 0) as total_purchase_cost,
            COALESCE(usage.total_allocated, 0) as total_allocated,
            COALESCE(usage.total_used, 0) as total_used
        FROM materials m
        LEFT JOIN (
            SELECT pi.material_id, SUM(pi.quantity) as total_purchased, SUM(pi.quantity * pi.unit_price) as total_cost
            FROM purchase_items pi
            JOIN purchases pur ON pi.purchase_id = pur.purchase_id
            WHERE pur.status IN ('Delivered', 'Completed') 
              AND (:project_id IS NULL OR pur.project_id = :project_id)
            GROUP BY pi.material_id
        ) purchased ON m.material_id = purchased.material_id
        LEFT JOIN (
            SELECT mu.material_id, SUM(mu.quantity_allocated) as total_allocated, SUM(mu.quantity_used) as total_used
            FROM material_usage mu
            WHERE (:project_id IS NULL OR mu.project_id = :project_id)
            GROUP BY mu.material_id
        ) usage ON m.material_id = usage.material_id
        WHERE COALESCE(purchased.total_purchased, 0) > 0 OR COALESCE(usage.total_allocated, 0) > 0
    """), params).fetchall()
    
    procurement_details = db.session.execute(text("""
        SELECT p.purchase_date, m.material_name, s.supplier_name, pi.quantity, m.unit, pi.unit_price, (pi.quantity * pi.unit_price) as total
        FROM purchase_items pi
        JOIN purchases p ON pi.purchase_id = p.purchase_id
        JOIN materials m ON pi.material_id = m.material_id
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        WHERE (:project_id IS NULL OR p.project_id = :project_id)
        ORDER BY p.purchase_date DESC
        LIMIT 20
    """), params).fetchall()

    # Package data for template
    data = {
        'project_summaries': project_summaries,
        'project_tasks': project_tasks,
        'financial_breakdown': financial_breakdown,
        'total_budget': total_budget,
        'total_cost': total_cost,
        'remaining_budget': remaining_budget,
        'budget_utilization': budget_utilization,
        'recent_expenses': recent_expenses,
        'worker_utilization': worker_utilization,
        'equipment_utilization': equipment_utilization,
        'material_usage_report': material_usage_report,
        'procurement_details': procurement_details
    }

    return render_template('reports/dashboard.html', 
                           all_projects=all_projects, 
                           selected_project_id=project_id_str, 
                           data=data)
