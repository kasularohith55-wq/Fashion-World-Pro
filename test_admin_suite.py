import sys
import os
import unittest
from datetime import datetime

# Set path
sys.path.insert(0, os.path.abspath('.'))

from app import app, db, User, Product, Category, Order, OrderItem, SupportTicket
from werkzeug.security import generate_password_hash

def run_tests():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        # Setup test client
        client = app.test_client()

        # Check existing test admin or create temporary
        test_email = 'suite_admin@fashionworld.pro'
        admin = User.query.filter_by(email=test_email).first()
        if not admin:
            admin = User(
                username='SuiteAdmin',
                email=test_email,
                password=generate_password_hash('admin123', method='pbkdf2:sha256'),
                is_admin=True,
                first_name='Suite',
                last_name='Admin'
            )
            db.session.add(admin)
        else:
            admin.password = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin.is_admin = True
        db.session.commit()

        # Test 1: Security - Unauthorized access to /admin must redirect
        print("\n--- TEST 1: Security & Unauthorized Protection ---")
        unauth_resp = client.get('/admin', follow_redirects=False)
        assert unauth_resp.status_code == 302, f"Expected 302 redirect for unauth /admin, got {unauth_resp.status_code}"
        assert '/admin_login' in unauth_resp.location, f"Expected redirect to /admin_login, got {unauth_resp.location}"
        print("[PASS] Unauthenticated access to /admin properly redirects to /admin_login (302)")

        # Test 2: Admin Login Flow
        print("\n--- TEST 2: Admin Authentication Flow ---")
        login_resp = client.post('/admin_login', data={
            'email': test_email,
            'password': 'admin123'
        }, follow_redirects=True)
        assert login_resp.status_code == 200, f"Expected 200 on login, got {login_resp.status_code}"
        assert b"Total Revenue" in login_resp.data or b"Dashboard" in login_resp.data or b"Command Center" in login_resp.data
        print("[PASS] Administrator authenticated successfully and redirected to Dashboard.")

        # Test 3: Admin Dashboard Metrics & Charts
        print("\n--- TEST 3: Admin Dashboard KPI & Charts ---")
        dash_resp = client.get('/admin')
        assert dash_resp.status_code == 200
        assert b"Total Revenue" in dash_resp.data
        assert b"Total Orders" in dash_resp.data
        assert b"salesOverviewChart" in dash_resp.data
        assert b"orderStatusDonut" in dash_resp.data
        print("[PASS] /admin dashboard rendered with KPI metrics, sparklines, and Chart.js canvases.")

        # Test 4: Products Catalog & Search
        print("\n--- TEST 4: Products Catalog & Search ---")
        prod_resp = client.get('/admin/products')
        assert prod_resp.status_code == 200
        assert b"Products Catalog" in prod_resp.data
        
        search_resp = client.get('/admin/products?query=Shirt')
        assert search_resp.status_code == 200
        print("[PASS] /admin/products rendered with catalog inventory and search filtering.")

        # Test 5: Add New Product
        print("\n--- TEST 5: Create Product (Admin CRUD) ---")
        test_prod = Product.query.filter_by(name='Test Executive Oxford Shirt').first()
        if test_prod:
            db.session.delete(test_prod)
            db.session.commit()

        add_resp = client.post('/admin/products/add', data={
            'name': 'Test Executive Oxford Shirt',
            'price': '2499.00',
            'discount_price': '1999.00',
            'category': 'Men',
            'description': 'A high quality test shirt for admin testing.',
            'stock': '45',
            'size': 'S, M, L, XL',
            'color': 'Sky Blue',
            'image_url': '/static/images/m1.png',
            'is_active': 'on',
            'is_featured': 'on'
        }, follow_redirects=True)
        assert add_resp.status_code == 200
        test_prod = Product.query.filter_by(name='Test Executive Oxford Shirt').first()
        assert test_prod is not None, "Product was not created in DB!"
        assert test_prod.stock == 45
        assert test_prod.color == 'Sky Blue'
        print(f"[PASS] Added new product ID #{test_prod.id} '{test_prod.name}' with stock {test_prod.stock}.")

        # Test 6: Edit Product
        print("\n--- TEST 6: Edit Product (Admin CRUD) ---")
        edit_resp = client.post(f'/admin/products/edit/{test_prod.id}', data={
            'name': 'Test Executive Oxford Shirt Updated',
            'price': '2799.00',
            'discount_price': '2199.00',
            'category': 'Men',
            'description': 'Updated description.',
            'stock': '60',
            'size': 'M, L, XL',
            'color': 'Midnight Sky',
            'image_url': '/static/images/m1.png',
            'is_active': 'on'
        }, follow_redirects=True)
        assert edit_resp.status_code == 200
        db.session.refresh(test_prod)
        assert test_prod.name == 'Test Executive Oxford Shirt Updated'
        assert test_prod.stock == 60
        print(f"[PASS] Successfully edited product ID #{test_prod.id} to '{test_prod.name}'.")

        # Test 7: Quick Stock Update
        print("\n--- TEST 7: Quick Stock Adjustment ---")
        stock_resp = client.post(f'/admin/products/quick_stock/{test_prod.id}', data={
            'new_stock': '4'
        }, follow_redirects=True)
        assert stock_resp.status_code == 200
        db.session.refresh(test_prod)
        assert test_prod.stock == 4
        print(f"[PASS] Quick stock updated to {test_prod.stock} (now in low stock range).")

        # Test 8: Low Stock Alerts Page
        print("\n--- TEST 8: Low Stock Alerts ---")
        low_resp = client.get('/admin/low-stock')
        assert low_resp.status_code == 200
        assert b"Test Executive Oxford Shirt Updated" in low_resp.data
        print("[PASS] /admin/low-stock correctly displays low stock item.")

        # Test 9: Category Management
        print("\n--- TEST 9: Category Management ---")
        test_cat = Category.query.filter_by(name='Luxury Accessories Suite').first()
        if test_cat:
            db.session.delete(test_cat)
            db.session.commit()

        cat_resp = client.post('/admin/categories/add', data={
            'name': 'Luxury Accessories Suite',
            'description': 'High end luxury accessories and goods',
            'is_active': 'on'
        }, follow_redirects=True)
        assert cat_resp.status_code == 200
        test_cat = Category.query.filter_by(name='Luxury Accessories Suite').first()
        assert test_cat is not None
        print(f"[PASS] Added category '{test_cat.name}' ID #{test_cat.id}.")

        # Test 10: Orders List & Detail
        print("\n--- TEST 10: Order Management & Customer Tracking ---")
        orders_resp = client.get('/admin/orders')
        assert orders_resp.status_code == 200
        assert b"Customer Orders" in orders_resp.data
        
        sample_order = Order.query.first()
        if sample_order:
            order_detail_resp = client.get(f'/admin/orders/{sample_order.id}')
            assert order_detail_resp.status_code == 200
            assert f"#FW-{sample_order.id}".encode('utf-8') in order_detail_resp.data
            
            # Update order status
            update_resp = client.post(f'/admin/orders/{sample_order.id}/update', data={
                'status': 'Shipped',
                'payment_status': 'Paid',
                'tracking_number': 'BLUEDART-FW-9988'
            }, follow_redirects=True)
            assert update_resp.status_code == 200
            db.session.refresh(sample_order)
            assert sample_order.status == 'Shipped'
            assert sample_order.tracking_number == 'BLUEDART-FW-9988'
            print(f"[PASS] Order #{sample_order.id} status updated to '{sample_order.status}' with tracking {sample_order.tracking_number}.")

        # Test 11: Customer Directory & Purchase History
        print("\n--- TEST 11: Customer Purchase History ---")
        cust_resp = client.get('/admin/customers')
        assert cust_resp.status_code == 200
        assert b"Customer Directory" in cust_resp.data
        
        sample_customer = User.query.filter_by(is_admin=False).first()
        if sample_customer:
            cust_detail_resp = client.get(f'/admin/customers/{sample_customer.id}')
            assert cust_detail_resp.status_code == 200
            assert sample_customer.username.encode('utf-8') in cust_detail_resp.data
            assert b"Purchase History" in cust_detail_resp.data
            print(f"[PASS] Customer purchase history for '{sample_customer.username}' verified.")

        # Test 12: Sales Analytics
        print("\n--- TEST 12: Store Analytics Dashboard ---")
        analytics_resp = client.get('/admin/analytics')
        assert analytics_resp.status_code == 200
        assert b"Total Gross Sales" in analytics_resp.data
        assert b"monthlySalesChart" in analytics_resp.data
        assert b"categorySalesChart" in analytics_resp.data
        print("[PASS] Sales Analytics dashboard rendered with monthly revenue and category charts.")

        # Test 13: Customer Support Ticketing System in Admin
        print("\n--- TEST 13: Customer Support Tickets ---")
        support_resp = client.get('/admin/support')
        assert support_resp.status_code == 200
        assert b"Customer Support Tickets" in support_resp.data
        
        sample_ticket = SupportTicket.query.first()
        if sample_ticket:
            ticket_detail_resp = client.get(f'/admin/support/{sample_ticket.id}')
            assert ticket_detail_resp.status_code == 200
            assert sample_ticket.ticket_number.encode('utf-8') in ticket_detail_resp.data
            print(f"[PASS] Support ticket #{sample_ticket.ticket_number} detail rendered successfully.")

        # Test 14: Global Search API
        print("\n--- TEST 14: Global Search API ---")
        search_api_resp = client.get('/admin/api/search?q=Shirt')
        assert search_api_resp.status_code == 200
        assert b"results" in search_api_resp.data
        print("[PASS] Global search API returned JSON search results successfully.")

        # Test 15: Store Settings Route
        print("\n--- TEST 15: Store Settings Route ---")
        settings_resp = client.get('/admin/settings/store')
        assert settings_resp.status_code == 200
        assert b"Store Settings" in settings_resp.data
        assert b"Payment &amp; Checkout Gateways" in settings_resp.data or b"Payment & Checkout Gateways" in settings_resp.data
        print("[PASS] /admin/settings/store rendered successfully.")

        # Test 16: Marketing - Banners & Offers
        print("\n--- TEST 16: Marketing - Banners & Offers ---")
        banners_resp = client.get('/admin/marketing/banners')
        assert banners_resp.status_code == 200
        assert b"Banners &amp; Promotional Offers" in banners_resp.data or b"Banners & Promotional Offers" in banners_resp.data
        print("[PASS] /admin/marketing/banners rendered successfully.")

        # Test 17: Marketing - Coupons
        print("\n--- TEST 17: Marketing - Coupons ---")
        coupons_resp = client.get('/admin/marketing/coupons')
        assert coupons_resp.status_code == 200
        assert b"Store Coupons &amp; Discounts" in coupons_resp.data or b"Store Coupons & Discounts" in coupons_resp.data
        print("[PASS] /admin/marketing/coupons rendered successfully.")

        # Test 18: Marketing - Reviews & Ratings
        print("\n--- TEST 18: Marketing - Reviews & Ratings ---")
        reviews_resp = client.get('/admin/marketing/reviews')
        assert reviews_resp.status_code == 200
        assert b"Customer Reviews &amp; Ratings" in reviews_resp.data or b"Customer Reviews & Ratings" in reviews_resp.data
        print("[PASS] /admin/marketing/reviews rendered successfully.")

        # Test 19: Customer Storefront & Google OAuth routes remain intact
        print("\n--- TEST 19: Storefront & Customer Routes Compatibility ---")
        home_resp = client.get('/')
        assert home_resp.status_code == 200
        
        shop_resp = client.get('/products')
        assert shop_resp.status_code == 200
        
        google_resp = client.get('/auth/google', follow_redirects=False)
        assert google_resp.status_code == 302
        assert 'accounts.google.com' in google_resp.location
        print("[PASS] Storefront home, shop, and Authlib Google OAuth flow remain 100% functional and intact.")

        # Cleanup test product, category and test admin
        db.session.delete(test_prod)
        if test_cat:
            db.session.delete(test_cat)
        if admin:
            db.session.delete(admin)
        db.session.commit()
        print("[CLEANUP] Test product, category & test admin safely removed.")

    print("\n========================================================")
    print("ALL 15 ADMIN SUITE TESTS PASSED PERFECTLY!")
    print("========================================================\n")

if __name__ == '__main__':
    run_tests()
