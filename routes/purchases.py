from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

purchases_bp = Blueprint('purchases', __name__, url_prefix='/purchases')

@purchases_bp.route('/')
@login_required
def list_purchases():
    # Use the purchases_with_total_view to get the total amount dynamically
    sql = text("""
        SELECT p.purchase_id, p.purchase_date, p.status, p.total_amount,
               s.supplier_name, pr.project_name
        FROM purchases_with_total_view p
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        JOIN projects pr ON p.project_id = pr.project_id
        ORDER BY p.purchase_date DESC
    """)
    purchases = db.session.execute(sql).fetchall()
    return render_template('purchases/list.html', purchases=purchases)

@purchases_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_purchase():
    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        project_id = request.form['project_id']
        purchase_date = request.form['purchase_date']
        status = request.form['status']
        
        valid_statuses = ['Ordered', 'Shipped', 'Delivered', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            flash('Invalid status selected.', 'danger')
            return redirect(url_for('purchases.add_purchase'))
        
        sql = text("""
            INSERT INTO purchases (supplier_id, project_id, purchase_date, status)
            VALUES (:supplier_id, :project_id, :purchase_date, :status)
            RETURNING purchase_id
        """)
        result = db.session.execute(sql, {
            'supplier_id': supplier_id, 'project_id': project_id, 
            'purchase_date': purchase_date, 'status': status
        })
        new_id = result.fetchone()[0]
        db.session.commit()
        
        flash('Purchase order created successfully!', 'success')
        return redirect(url_for('purchases.view_purchase', purchase_id=new_id))
        
    suppliers = db.session.execute(text("SELECT * FROM suppliers ORDER BY supplier_name")).fetchall()
    projects = db.session.execute(text("SELECT project_id, project_name FROM projects ORDER BY project_name")).fetchall()
    return render_template('purchases/form.html', purchase=None, suppliers=suppliers, projects=projects)

@purchases_bp.route('/<int:purchase_id>')
@login_required
def view_purchase(purchase_id):
    sql = text("""
        SELECT p.*, s.supplier_name, pr.project_name, p.total_amount
        FROM purchases_with_total_view p
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        JOIN projects pr ON p.project_id = pr.project_id
        WHERE p.purchase_id = :id
    """)
    purchase = db.session.execute(sql, {'id': purchase_id}).fetchone()
    
    if not purchase:
        flash('Purchase order not found.', 'danger')
        return redirect(url_for('purchases.list_purchases'))
        
    # Get items in this purchase order
    items_sql = text("""
        SELECT pi.*, m.material_name, m.unit
        FROM purchase_items pi
        JOIN materials m ON pi.material_id = m.material_id
        WHERE pi.purchase_id = :id
    """)
    items = db.session.execute(items_sql, {'id': purchase_id}).fetchall()
    
    # Get available materials to add
    materials = db.session.execute(text("SELECT * FROM materials ORDER BY material_name")).fetchall()
    
    return render_template('purchases/view.html', purchase=purchase, items=items, materials=materials)

@purchases_bp.route('/<int:purchase_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_purchase(purchase_id):
    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        project_id = request.form['project_id']
        purchase_date = request.form['purchase_date']
        status = request.form['status']
        
        valid_statuses = ['Ordered', 'Shipped', 'Delivered', 'Completed', 'Cancelled']
        if status not in valid_statuses:
            flash('Invalid status selected.', 'danger')
            return redirect(url_for('purchases.edit_purchase', purchase_id=purchase_id))
        
        sql = text("""
            UPDATE purchases 
            SET supplier_id=:supplier_id, project_id=:project_id, purchase_date=:purchase_date, status=:status
            WHERE purchase_id=:id
        """)
        db.session.execute(sql, {
            'supplier_id': supplier_id, 'project_id': project_id, 
            'purchase_date': purchase_date, 'status': status, 'id': purchase_id
        })
        db.session.commit()
        
        flash('Purchase order updated successfully!', 'success')
        return redirect(url_for('purchases.view_purchase', purchase_id=purchase_id))
        
    purchase = db.session.execute(text("SELECT * FROM purchases WHERE purchase_id = :id"), {'id': purchase_id}).fetchone()
    suppliers = db.session.execute(text("SELECT * FROM suppliers ORDER BY supplier_name")).fetchall()
    projects = db.session.execute(text("SELECT project_id, project_name FROM projects ORDER BY project_name")).fetchall()
    return render_template('purchases/form.html', purchase=purchase, suppliers=suppliers, projects=projects)

@purchases_bp.route('/<int:purchase_id>/add_item', methods=['POST'])
@login_required
def add_purchase_item(purchase_id):
    material_id = request.form['material_id']
    quantity = float(request.form['quantity'])
    unit_price = float(request.form['unit_price'])
    
    if quantity <= 0:
        flash('Quantity must be strictly greater than 0.', 'danger')
        return redirect(url_for('purchases.view_purchase', purchase_id=purchase_id))
    if unit_price < 0:
        flash('Unit price cannot be negative.', 'danger')
        return redirect(url_for('purchases.view_purchase', purchase_id=purchase_id))
    
    sql = text("""
        INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
        VALUES (:purchase_id, :material_id, :quantity, :unit_price)
    """)
    db.session.execute(sql, {
        'purchase_id': purchase_id, 'material_id': material_id, 
        'quantity': quantity, 'unit_price': unit_price
    })
    db.session.commit()
    
    flash('Item added to purchase order!', 'success')
    return redirect(url_for('purchases.view_purchase', purchase_id=purchase_id))

@purchases_bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_purchase_item(item_id):
    # Need to get purchase_id to redirect back
    sql_get = text("SELECT purchase_id FROM purchase_items WHERE purchase_item_id = :id")
    result = db.session.execute(sql_get, {'id': item_id}).fetchone()
    if result:
        purchase_id = result.purchase_id
        db.session.execute(text("DELETE FROM purchase_items WHERE purchase_item_id = :id"), {'id': item_id})
        db.session.commit()
        flash('Item removed.', 'success')
        return redirect(url_for('purchases.view_purchase', purchase_id=purchase_id))
    return redirect(url_for('purchases.list_purchases'))
