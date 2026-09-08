from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

materials_bp = Blueprint('materials', __name__, url_prefix='/materials')

@materials_bp.route('/')
@login_required
def list_materials():
    materials = db.session.execute(text("""
        SELECT material_id, material_name, unit, unit_cost, minimum_stock
        FROM materials
        ORDER BY material_name
    """)).fetchall()
    return render_template('materials/list.html', materials=materials)

@materials_bp.route('/<int:material_id>')
@login_required
def view_material(material_id):
    material = db.session.execute(text("""
        SELECT * FROM materials WHERE material_id = :id
    """), {'id': material_id}).fetchone()
    
    if not material:
        flash("Material not found.", "danger")
        return redirect(url_for('materials.list_materials'))
        
    # Fetch all project allocations for this material
    allocations = db.session.execute(text("""
        SELECT mu.usage_id, mu.quantity_allocated, mu.quantity_used,
               p.project_id, p.project_name
        FROM material_usage mu
        JOIN projects p ON mu.project_id = p.project_id
        WHERE mu.material_id = :id
        ORDER BY p.project_name
    """), {'id': material_id}).fetchall()
    
    # Active projects for the allocation modal
    active_projects = db.session.execute(text("""
        SELECT project_id, project_name FROM projects WHERE status != 'Completed' ORDER BY project_name
    """)).fetchall()
        
    return render_template('materials/view.html', material=material, allocations=allocations, active_projects=active_projects)

@materials_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_material():
    if request.method == 'POST':
        material_name = request.form['material_name']
        unit = request.form['unit']
        unit_cost = request.form['unit_cost']
        minimum_stock = request.form['minimum_stock']
        
        db.session.execute(text("""
            INSERT INTO materials (material_name, unit, unit_cost, minimum_stock)
            VALUES (:name, :unit, :cost, :min_stock)
        """), {
            'name': material_name, 'unit': unit,
            'cost': unit_cost, 'min_stock': minimum_stock
        })
        db.session.commit()
        flash('Material added successfully!', 'success')
        return redirect(url_for('materials.list_materials'))
        
    return render_template('materials/form.html', material=None)

@materials_bp.route('/<int:material_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_material(material_id):
    if request.method == 'POST':
        material_name = request.form['material_name']
        unit = request.form['unit']
        unit_cost = request.form['unit_cost']
        minimum_stock = request.form['minimum_stock']
        
        db.session.execute(text("""
            UPDATE materials SET 
                material_name=:name, unit=:unit, 
                unit_cost=:cost, minimum_stock=:min_stock
            WHERE material_id=:id
        """), {
            'name': material_name, 'unit': unit,
            'cost': unit_cost, 'min_stock': minimum_stock, 'id': material_id
        })
        db.session.commit()
        flash('Material updated successfully!', 'success')
        return redirect(url_for('materials.view_material', material_id=material_id))
        
    material = db.session.execute(text("SELECT * FROM materials WHERE material_id = :id"), 
                            {'id': material_id}).fetchone()
    return render_template('materials/form.html', material=material)

@materials_bp.route('/<int:material_id>/allocate', methods=['POST'])
@login_required
def allocate_material(material_id):
    project_id = request.form.get('project_id')
    quantity_allocated = request.form.get('quantity_allocated', 0)
    quantity_used = 0 # Initially 0, usage can be updated later
    
    if not project_id:
        flash("Project is required.", "danger")
        return redirect(url_for('materials.view_material', material_id=material_id))
        
    # Check if this material is already allocated to this project
    existing = db.session.execute(text("""
        SELECT usage_id FROM material_usage 
        WHERE project_id = :project_id AND material_id = :material_id
    """), {'project_id': project_id, 'material_id': material_id}).fetchone()

    if existing:
        flash("This material is already allocated to the selected project. Please edit the existing allocation instead.", "warning")
        return redirect(url_for('materials.view_material', material_id=material_id))
        
    db.session.execute(text("""
        INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
        VALUES (:project_id, :material_id, :quantity_allocated, :quantity_used)
    """), {
        'project_id': project_id,
        'material_id': material_id,
        'quantity_allocated': quantity_allocated,
        'quantity_used': quantity_used
    })
    db.session.commit()
    flash("Material allocated to project successfully!", "success")
    return redirect(url_for('materials.view_material', material_id=material_id))
