from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from extensions import db

materials_bp = Blueprint('materials', __name__, url_prefix='/materials')

@materials_bp.route('/')
@login_required
def list_materials():
    materials = db.session.execute(text("""
         SELECT m.material_id, m.material_name, m.unit, m.unit_cost,
             COALESCE(mu.total_allocated, 0) AS total_allocated,
             COALESCE(mu.total_used, 0) AS total_used
         FROM materials m
         LEFT JOIN (
             SELECT material_id, SUM(quantity_allocated) AS total_allocated,
                 SUM(quantity_used) AS total_used
             FROM material_usage
             GROUP BY material_id
         ) mu ON mu.material_id = m.material_id
         ORDER BY m.material_name
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
        
    # Fetch all project allocations and delivered purchases for this material
    allocations = db.session.execute(text("""
        SELECT p.project_id, p.project_name,
               COALESCE(purchased.total_delivered, 0) AS total_delivered,
               COALESCE(mu.quantity_allocated, 0) AS quantity_allocated,
               COALESCE(mu.quantity_used, 0) AS quantity_used,
               mu.usage_id
        FROM projects p
        LEFT JOIN (
            SELECT pur.project_id, SUM(pi.quantity) AS total_delivered
            FROM purchase_items pi
            JOIN purchases pur ON pi.purchase_id = pur.purchase_id
            WHERE pur.status IN ('Delivered', 'Completed') AND pi.material_id = :id
            GROUP BY pur.project_id
        ) purchased ON p.project_id = purchased.project_id
        LEFT JOIN material_usage mu ON p.project_id = mu.project_id AND mu.material_id = :id
        WHERE COALESCE(purchased.total_delivered, 0) > 0 OR COALESCE(mu.quantity_allocated, 0) > 0
        ORDER BY p.project_name
    """), {'id': material_id}).fetchall()
    
    return render_template('materials/view.html', material=material, allocations=allocations)

@materials_bp.route('/new', methods=['GET', 'POST'])
@login_required
def add_material():
    if request.method == 'POST':
        material_name = request.form['material_name']
        unit = request.form['unit']
        unit_cost = float(request.form['unit_cost'])
        
        if unit_cost < 0:
            flash('Unit cost cannot be negative.', 'danger')
            return redirect(url_for('materials.add_material'))
        
        db.session.execute(text("""
            INSERT INTO materials (material_name, unit, unit_cost)
            VALUES (:name, :unit, :cost)
        """), {
            'name': material_name, 'unit': unit,
            'cost': unit_cost
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
        unit_cost = float(request.form['unit_cost'])
        
        if unit_cost < 0:
            flash('Unit cost cannot be negative.', 'danger')
            return redirect(url_for('materials.edit_material', material_id=material_id))
        
        db.session.execute(text("""
            UPDATE materials SET 
                material_name=:name, unit=:unit, unit_cost=:cost
            WHERE material_id=:id
        """), {
            'name': material_name, 'unit': unit,
            'cost': unit_cost, 'id': material_id
        })
        db.session.commit()
        flash('Material updated successfully!', 'success')
        return redirect(url_for('materials.view_material', material_id=material_id))
        
    material = db.session.execute(text("SELECT * FROM materials WHERE material_id = :id"), 
                            {'id': material_id}).fetchone()
    return render_template('materials/form.html', material=material)
