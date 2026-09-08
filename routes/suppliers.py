from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from app import db

suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')

@suppliers_bp.route('/')
@login_required
def list_suppliers():
    sql = text("SELECT * FROM suppliers ORDER BY supplier_name")
    suppliers = db.session.execute(sql).fetchall()
    return render_template('suppliers/list.html', suppliers=suppliers)

@suppliers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        name = request.form['supplier_name']
        contact = request.form['contact_person']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        
        sql = text("""
            INSERT INTO suppliers (supplier_name, contact_person, phone, email, address)
            VALUES (:name, :contact, :phone, :email, :address)
            RETURNING supplier_id
        """)
        result = db.session.execute(sql, {
            'name': name, 'contact': contact, 'phone': phone, 'email': email, 'address': address
        })
        new_id = result.fetchone()[0]
        db.session.commit()
        
        flash('Supplier added successfully!', 'success')
        return redirect(url_for('suppliers.view_supplier', supplier_id=new_id))
        
    return render_template('suppliers/form.html', supplier=None)

@suppliers_bp.route('/<int:supplier_id>')
@login_required
def view_supplier(supplier_id):
    sql = text("SELECT * FROM suppliers WHERE supplier_id = :id")
    supplier = db.session.execute(sql, {'id': supplier_id}).fetchone()
    
    if not supplier:
        flash('Supplier not found.', 'danger')
        return redirect(url_for('suppliers.list_suppliers'))
        
    purchases_sql = text("""
        SELECT p.purchase_id, p.purchase_date, p.status, p.total_amount, pr.project_name
        FROM purchases_with_total_view p
        JOIN projects pr ON p.project_id = pr.project_id
        WHERE p.supplier_id = :id
        ORDER BY p.purchase_date DESC
    """)
    purchases = db.session.execute(purchases_sql, {'id': supplier_id}).fetchall()
    
    return render_template('suppliers/view.html', supplier=supplier, purchases=purchases)

@suppliers_bp.route('/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(supplier_id):
    if request.method == 'POST':
        name = request.form['supplier_name']
        contact = request.form['contact_person']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        
        sql = text("""
            UPDATE suppliers 
            SET supplier_name=:name, contact_person=:contact, phone=:phone, email=:email, address=:address
            WHERE supplier_id=:id
        """)
        db.session.execute(sql, {
            'name': name, 'contact': contact, 'phone': phone, 'email': email, 'address': address, 'id': supplier_id
        })
        db.session.commit()
        
        flash('Supplier updated successfully!', 'success')
        return redirect(url_for('suppliers.view_supplier', supplier_id=supplier_id))
        
    sql = text("SELECT * FROM suppliers WHERE supplier_id = :id")
    supplier = db.session.execute(sql, {'id': supplier_id}).fetchone()
    return render_template('suppliers/form.html', supplier=supplier)

@suppliers_bp.route('/<int:supplier_id>/delete', methods=['POST'])
@login_required
def delete_supplier(supplier_id):
    try:
        sql = text("DELETE FROM suppliers WHERE supplier_id = :id")
        db.session.execute(sql, {'id': supplier_id})
        db.session.commit()
        flash('Supplier deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        # ON DELETE RESTRICT in purchases table means we can't delete if they have purchases
        flash('Cannot delete supplier. They likely have associated purchase records.', 'danger')
        
    return redirect(url_for('suppliers.list_suppliers'))
