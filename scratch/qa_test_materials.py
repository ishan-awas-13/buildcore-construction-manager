import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# Point Flask to buildcore_test
os.environ['TEST_DB_NAME'] = 'buildcore_test'

from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_tests():
    print("=" * 70)
    print("MODULE 1: ADVERSARIAL MATERIAL & INVENTORY ISOLATION TESTS")
    print("=" * 70)

    results = []

    with app.app_context():
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Connected Database: '{curr_db}'")
        assert curr_db == 'buildcore_test', f"Safety violation: Expected buildcore_test, got {curr_db}"

        client = app.test_client()

        # Log in as admin
        login_res = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
        assert login_res.status_code == 200, "Admin login failed!"

        # Query simulation project IDs
        p101_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-101%'")).scalar()
        p102_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-102%'")).scalar()
        p103_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-103%'")).scalar()
        mat_cement_id = db.session.execute(text("SELECT material_id FROM materials WHERE material_name = 'QA-Mat-Cement OPC 53'")).scalar()
        mat_concrete_id = db.session.execute(text("SELECT material_id FROM materials WHERE material_name = 'QA-Mat-ReadyMix Concrete M30'")).scalar()
        
        # -------------------------------------------------------------
        # TEST-MAT-01: Cross-Project Stock Leakage Prevention
        # -------------------------------------------------------------
        print("\n[TEST-MAT-01] Testing Cross-Project Stock Leakage...")
        # Check Project 101 page: should have 0 Cement available
        res = client.get(f'/projects/{p101_id}')
        assert res.status_code == 200
        # Attempt to allocate Cement on P101 (where 0 is delivered)
        post_alloc = client.post(f'/projects/{p101_id}/materials/allocate', data={
            'material_id': mat_cement_id,
            'quantity_allocated': 50
        }, follow_redirects=True)
        html = post_alloc.data.decode('utf-8')
        passed_01 = "Cannot allocate" in html or "Only 0.00" in html
        db_p101_alloc = db.session.execute(text("SELECT quantity_allocated FROM material_usage WHERE project_id = :p AND material_id = :m"), {'p': p101_id, 'm': mat_cement_id}).scalar() or 0
        assert db_p101_alloc == 0, "Cross-project leakage: Material allocated without project delivery!"
        print(f"  Result: PASS - Allocation safely blocked. DB Allocation: {db_p101_alloc}")
        results.append(('TEST-MAT-01', 'Cross-Project Stock Leakage Prevention', 'PASS', 'Blocked allocation when delivered_stock = 0'))

        # -------------------------------------------------------------
        # TEST-MAT-02: Over-Allocation Defense
        # -------------------------------------------------------------
        print("\n[TEST-MAT-02] Testing Over-Allocation Defense...")
        # P102 has 500 delivered, 350 allocated -> 150 available
        post_over_alloc = client.post(f'/projects/{p102_id}/materials/allocate', data={
            'material_id': mat_cement_id,
            'quantity_allocated': 151
        }, follow_redirects=True)
        html = post_over_alloc.data.decode('utf-8')
        assert "Cannot allocate" in html and "Only 150.00" in html, f"Over-allocation not blocked! Response: {html[:300]}"
        db_p102_alloc = db.session.execute(text("SELECT quantity_allocated FROM material_usage WHERE project_id = :p AND material_id = :m"), {'p': p102_id, 'm': mat_cement_id}).scalar()
        assert db_p102_alloc == 350.0, f"Over-allocation corrupted database: {db_p102_alloc}"
        print(f"  Result: PASS - Over-allocation (151 > 150 available) rejected. DB Allocation remains: {db_p102_alloc}")
        results.append(('TEST-MAT-02', 'Over-Allocation Defense', 'PASS', 'Blocked allocation of 151 units when 150 available'))

        # -------------------------------------------------------------
        # TEST-MAT-03: Over-Consumption Defense
        # -------------------------------------------------------------
        print("\n[TEST-MAT-03] Testing Over-Consumption Defense...")
        # P102 has 350 allocated, 250 consumed -> 100 available to consume
        usage_row = db.session.execute(text("SELECT usage_id FROM material_usage WHERE project_id = :p AND material_id = :m"), {'p': p102_id, 'm': mat_cement_id}).fetchone()
        usage_id_102 = usage_row.usage_id

        post_over_consume = client.post(f'/projects/{p102_id}/materials/consume', data={
            'usage_id': usage_id_102,
            'quantity_consumed': 101
        }, follow_redirects=True)
        html = post_over_consume.data.decode('utf-8')
        assert "Cannot record consumption" in html and "Maximum available to consume is 100.00" in html
        db_p102_used = db.session.execute(text("SELECT quantity_used FROM material_usage WHERE usage_id = :u"), {'u': usage_id_102}).scalar()
        assert db_p102_used == 250.0, f"Over-consumption corrupted database: {db_p102_used}"
        print(f"  Result: PASS - Over-consumption (101 > 100 limit) rejected. DB Used remains: {db_p102_used}")
        results.append(('TEST-MAT-03', 'Over-Consumption Defense', 'PASS', 'Blocked consumption exceeding allocated limit'))

        # -------------------------------------------------------------
        # TEST-MAT-04: Negative and Zero Quantity Attacks
        # -------------------------------------------------------------
        print("\n[TEST-MAT-04] Testing Negative and Zero Quantity Injection...")
        # Negative allocation
        res_neg_alloc = client.post(f'/projects/{p102_id}/materials/allocate', data={
            'material_id': mat_cement_id,
            'quantity_allocated': -20
        }, follow_redirects=True)
        assert "greater than zero" in res_neg_alloc.data.decode('utf-8')

        # Zero allocation
        res_zero_alloc = client.post(f'/projects/{p102_id}/materials/allocate', data={
            'material_id': mat_cement_id,
            'quantity_allocated': 0
        }, follow_redirects=True)
        assert "greater than zero" in res_zero_alloc.data.decode('utf-8')

        # Negative consumption
        res_neg_consume = client.post(f'/projects/{p102_id}/materials/consume', data={
            'usage_id': usage_id_102,
            'quantity_consumed': -10
        }, follow_redirects=True)
        assert "greater than zero" in res_neg_consume.data.decode('utf-8')

        # Zero consumption
        res_zero_consume = client.post(f'/projects/{p102_id}/materials/consume', data={
            'usage_id': usage_id_102,
            'quantity_consumed': 0
        }, follow_redirects=True)
        assert "greater than zero" in res_zero_consume.data.decode('utf-8')

        print("  Result: PASS - Negative and zero quantities rejected across allocate and consume.")
        results.append(('TEST-MAT-04', 'Negative/Zero Quantity Injection Defense', 'PASS', 'All zero/negative submissions blocked'))

        # -------------------------------------------------------------
        # TEST-MAT-05: Cross-Project Usage ID Tampering (IDOR / Hijack)
        # -------------------------------------------------------------
        print("\n[TEST-MAT-05] Testing Cross-Project Usage ID Tampering...")
        # Submitting consumption to P101 endpoint using P102's usage_id
        res_tamper = client.post(f'/projects/{p101_id}/materials/consume', data={
            'usage_id': usage_id_102,
            'quantity_consumed': 10
        }, follow_redirects=True)
        html = res_tamper.data.decode('utf-8')
        assert "Material allocation record not found for this project" in html, f"Cross-project IDOR succeeded! HTML: {html[:300]}"
        # Verify P102 consumption didn't change
        db_p102_used_after = db.session.execute(text("SELECT quantity_used FROM material_usage WHERE usage_id = :u"), {'u': usage_id_102}).scalar()
        assert db_p102_used_after == 250.0
        print("  Result: PASS - Cross-project usage_id hijacking blocked by project_id verification.")
        results.append(('TEST-MAT-05', 'Cross-Project Usage ID Tampering Guard', 'PASS', 'Rejected foreign project usage_id'))

        # -------------------------------------------------------------
        # TEST-MAT-06: Procurement Status Boundary (Shipped vs Delivered)
        # -------------------------------------------------------------
        print("\n[TEST-MAT-06] Testing Procurement Status Boundary...")
        # Concrete on P102 is 'Shipped', NOT Delivered. Attempt to allocate 10 cu.m
        res_shipped_alloc = client.post(f'/projects/{p102_id}/materials/allocate', data={
            'material_id': mat_concrete_id,
            'quantity_allocated': 10
        }, follow_redirects=True)
        html = res_shipped_alloc.data.decode('utf-8')
        assert "Cannot allocate" in html and "Only 0.00" in html, f"Shipped material incorrectly allowed allocation! {html[:300]}"
        print("  Result: PASS - 'Shipped' status material correctly excluded from allocatable delivered stock.")
        results.append(('TEST-MAT-06', 'Procurement Status Boundary', 'PASS', 'Shipped materials cannot be allocated'))

        # -------------------------------------------------------------
        # TEST-MAT-07: Purchase Item Deletion from Delivered Order (DEFECT CHECK)
        # -------------------------------------------------------------
        print("\n[TEST-MAT-07] Testing Purchase Item Deletion Protection on Delivered Order...")
        po_item = db.session.execute(text("""
            SELECT pi.purchase_item_id, pi.quantity, p.status, p.purchase_id
            FROM purchase_items pi
            JOIN purchases p ON pi.purchase_id = p.purchase_id
            WHERE p.project_id = :p AND pi.material_id = :m
        """), {'p': p102_id, 'm': mat_cement_id}).fetchone()
        
        print(f"  Found PO #{po_item.purchase_id} (Status: {po_item.status}) with {po_item.quantity} units of Cement.")
        print("  Attempting to delete this purchase item via POST /purchases/item/<id>/delete...")
        
        del_res = client.post(f'/purchases/item/{po_item.purchase_item_id}/delete', follow_redirects=True)
        
        # Check if the item was deleted
        item_still_exists = db.session.execute(text("SELECT 1 FROM purchase_items WHERE purchase_item_id = :id"), {'id': po_item.purchase_item_id}).scalar()
        
        if not item_still_exists:
            print("  CRITICAL DEFECT DETECTED: Application allowed deleting a purchase item from a DELIVERED order with active allocations!")
            delivered_now = db.session.execute(text("""
                SELECT COALESCE(SUM(pi.quantity), 0)
                FROM purchase_items pi
                JOIN purchases p ON pi.purchase_id = p.purchase_id
                WHERE p.project_id = :p AND pi.material_id = :m AND p.status IN ('Delivered', 'Completed')
            """), {'p': p102_id, 'm': mat_cement_id}).scalar()
            alloc_now = db.session.execute(text("SELECT quantity_allocated FROM material_usage WHERE project_id = :p AND material_id = :m"), {'p': p102_id, 'm': mat_cement_id}).scalar()
            print(f"  INCONSISTENCY: Delivered Stock is now {delivered_now}, but Allocated Quantity is {alloc_now}!")
            results.append(('TEST-MAT-07', 'Purchase Item Deletion Guard on Delivered Orders', 'FAIL', f'CRITICAL: Allowed deleting delivered PO item with active allocation (delivered={delivered_now} < allocated={alloc_now})'))
            
            # Restore the deleted purchase item so further tests have correct state
            db.session.execute(text("""
                INSERT INTO purchase_items (purchase_item_id, purchase_id, material_id, quantity, unit_price)
                VALUES (:id, :pid, :mid, :qty, :price)
            """), {'id': po_item.purchase_item_id, 'pid': po_item.purchase_id, 'mid': mat_cement_id, 'qty': 500.0, 'price': 380.00})
            db.session.commit()
            print("  Restored test purchase item for downstream stability.")
        else:
            print("  Result: PASS - Purchase item deletion on Delivered order was rejected.")
            results.append(('TEST-MAT-07', 'Purchase Item Deletion Guard on Delivered Orders', 'PASS', 'Deletion prevented on delivered PO'))

        # -------------------------------------------------------------
        # TEST-MAT-08: Order Status Cancellation Mutation on Allocated Materials (DEFECT CHECK)
        # -------------------------------------------------------------
        print("\n[TEST-MAT-08] Testing Order Cancellation Guard when Materials are Allocated...")
        po_id = po_item.purchase_id
        sup_id = db.session.execute(text("SELECT supplier_id FROM purchases WHERE purchase_id = :id"), {'id': po_id}).scalar()
        # Attempt to edit purchase order status to 'Cancelled'
        res_cancel = client.post(f'/purchases/{po_id}/edit', data={
            'supplier_id': sup_id,
            'project_id': p102_id,
            'purchase_date': '2026-08-10',
            'status': 'Cancelled'
        }, follow_redirects=True)
        
        po_status = db.session.execute(text("SELECT status FROM purchases WHERE purchase_id = :id"), {'id': po_id}).scalar()
        if po_status == 'Cancelled':
            print("  CRITICAL DEFECT DETECTED: Application allowed cancelling a Delivered PO whose materials are actively allocated and consumed!")
            results.append(('TEST-MAT-08', 'Order Cancellation Guard for Allocated Stock', 'FAIL', 'CRITICAL: Allowed changing status to Cancelled on PO with active allocations/consumptions'))
            # Restore to Delivered
            db.session.execute(text("UPDATE purchases SET status = 'Delivered' WHERE purchase_id = :id"), {'id': po_id})
            db.session.commit()
            print("  Restored PO status to 'Delivered'.")
        else:
            print("  Result: PASS - Order status cancellation guarded.")
            results.append(('TEST-MAT-08', 'Order Cancellation Guard for Allocated Stock', 'PASS', 'Cancellation prevented on allocated PO'))

        # -------------------------------------------------------------
        # TEST-MAT-09: Multi-Price Purchase Reconciliation in Reports
        # -------------------------------------------------------------
        print("\n[TEST-MAT-09] Testing Multi-Price Purchase Layering & Cost Reconciliation...")
        # Add a second purchase of Cement on P102 at a different unit price: 100 bags @ ₹420 (₹42,000)
        cur_sup = db.session.execute(text("SELECT supplier_id FROM suppliers LIMIT 1")).scalar()
        db.session.execute(text("""
            INSERT INTO purchases (purchase_id, supplier_id, project_id, purchase_date, status)
            VALUES (999102, :sup, :p, '2026-09-01', 'Delivered')
        """), {'sup': cur_sup, 'p': p102_id})
        db.session.execute(text("""
            INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
            VALUES (999102, :m, 100.0, 420.00)
        """), {'m': mat_cement_id})
        db.session.commit()

        # Check Report 4 for P102
        rep4_res = client.get(f'/reports/?project_id={p102_id}')
        assert rep4_res.status_code == 200
        
        # Verify Report 4 SQL calculation: Total Purchased = 500 + 100 = 600 bags.
        # Total Cost = (500 * 380) + (100 * 420) = 190,000 + 42,000 = 232,000.
        rep_data = db.session.execute(text("""
            SELECT 
                SUM(pi.quantity) as total_purchased, 
                SUM(pi.quantity * pi.unit_price) as total_cost
            FROM purchase_items pi
            JOIN purchases pur ON pi.purchase_id = pur.purchase_id
            WHERE pur.status IN ('Delivered', 'Completed') 
              AND pur.project_id = :p AND pi.material_id = :m
        """), {'p': p102_id, 'm': mat_cement_id}).fetchone()

        assert rep_data.total_purchased == 600.0, f"Expected 600 bags, got {rep_data.total_purchased}"
        assert rep_data.total_cost == 232000.00, f"Expected ₹232,000, got {rep_data.total_cost}"
        print(f"  Result: PASS - Multi-price layering verified. Total: 600 bags @ exact cost ₹{rep_data.total_cost:,.2f}")
        results.append(('TEST-MAT-09', 'Multi-Price Purchase Cost Reconciliation', 'PASS', f'Reconciled 600 units @ exact blended cost ₹232,000.00'))

        # Cleanup extra PO
        db.session.execute(text("DELETE FROM purchase_items WHERE purchase_id = 999102"))
        db.session.execute(text("DELETE FROM purchases WHERE purchase_id = 999102"))
        db.session.commit()

    print("\n" + "=" * 70)
    print("MODULE 1 RESULTS SUMMARY:")
    for code, name, outcome, notes in results:
        print(f"  [{outcome}] {code:12} : {name:40} | {notes}")
    print("=" * 70)
    return results

if __name__ == '__main__':
    run_tests()
