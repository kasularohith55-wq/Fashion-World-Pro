"""
test_payment_checkout.py
Comprehensive regression test suite for Fashion World Pro payment & checkout workflows:
1. get_razorpay_client configuration validation (unconfigured, placeholder, test, live)
2. Checkout route context variables (razorpay_configured, is_test_mode, is_live_mode)
3. /create_order endpoint (empty cart, unconfigured gateway, successful order creation)
4. /verify_payment endpoint (parameter validation, signature verification, stock deduction, idempotency)
5. /cod_success Cash on Delivery order placement
6. /upi_payment route redirect to checkout
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from app import app, db, User, Product, CartItem, Order, OrderItem, get_razorpay_client
from werkzeug.security import generate_password_hash
import razorpay

class PaymentCheckoutTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SERVER_NAME'] = 'localhost'

    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create unique test user
        self.test_user = User.query.filter_by(email='checkout_tester@example.com').first()
        if not self.test_user:
            self.test_user = User(
                username='checkout_tester',
                email='checkout_tester@example.com',
                password=generate_password_hash('TestPass123!', method='pbkdf2:sha256'),
                first_name='Test',
                last_name='Customer',
                phone='9876543210',
                address='123 Fashion Street',
                city='Hyderabad',
                zip_code='500001'
            )
            db.session.add(self.test_user)
            db.session.commit()
        else:
            self.test_user.password = generate_password_hash('TestPass123!', method='pbkdf2:sha256')
            db.session.commit()

        # Create test product with known stock
        self.test_product = Product.query.filter_by(name='Payment Test T-Shirt').first()
        if not self.test_product:
            self.test_product = Product(
                name='Payment Test T-Shirt',
                price=500.0,
                discount_price=450.0,
                stock=20,
                category='Men',
                image_url='/static/images/m1.png',
                description='Test clothing item for payment flow'
            )
            db.session.add(self.test_product)
            db.session.commit()
        else:
            self.test_product.stock = 20
            db.session.commit()

        # Clean cart & orders for this user
        CartItem.query.filter_by(user_id=self.test_user.id).delete()
        db.session.commit()

    def tearDown(self):
        try:
            # Clean cart and orders created during tests
            if hasattr(self, 'test_user') and self.test_user:
                CartItem.query.filter_by(user_id=self.test_user.id).delete()
                test_orders = Order.query.filter_by(user_id=self.test_user.id).all()
                for o in test_orders:
                    OrderItem.query.filter_by(order_id=o.id).delete()
                    db.session.delete(o)
                db.session.commit()
        except Exception:
            db.session.rollback()
        finally:
            db.session.remove()
            self.app_context.pop()

    def login_test_user(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user.id)
            sess['_fresh'] = True

    # -------------------------------------------------------------------------
    # 1. get_razorpay_client unit tests
    # -------------------------------------------------------------------------
    def test_get_razorpay_client_unconfigured_placeholders(self):
        """Placeholder keys should mark gateway as not configured and return client as None"""
        with patch.dict(os.environ, {
            'RAZORPAY_KEY_ID': 'rzp_test_your_key_id',
            'RAZORPAY_KEY_SECRET': 'your_key_secret'
        }, clear=False):
            client, key_id, key_secret, is_configured = get_razorpay_client()
            self.assertFalse(is_configured)
            self.assertIsNone(client)

    def test_get_razorpay_client_empty(self):
        """Empty keys should mark gateway as unconfigured"""
        with patch.dict(os.environ, {
            'RAZORPAY_KEY_ID': '',
            'RAZORPAY_KEY_SECRET': ''
        }, clear=False):
            client, key_id, key_secret, is_configured = get_razorpay_client()
            self.assertFalse(is_configured)
            self.assertIsNone(client)

    def test_get_razorpay_client_valid_test_keys(self):
        """Valid test keys should configure client and identify test mode"""
        with patch.dict(os.environ, {
            'RAZORPAY_KEY_ID': 'rzp_test_AbCdEf123456',
            'RAZORPAY_KEY_SECRET': 'SecretKey1234567890'
        }, clear=False):
            client, key_id, key_secret, is_configured = get_razorpay_client()
            self.assertTrue(is_configured)
            self.assertIsNotNone(client)
            self.assertTrue(key_id.startswith('rzp_test_'))

    def test_get_razorpay_client_valid_live_keys(self):
        """Valid live keys should configure client and identify live mode"""
        with patch.dict(os.environ, {
            'RAZORPAY_KEY_ID': 'rzp_live_AbCdEf123456',
            'RAZORPAY_KEY_SECRET': 'LiveSecretKey1234567890'
        }, clear=False):
            client, key_id, key_secret, is_configured = get_razorpay_client()
            self.assertTrue(is_configured)
            self.assertIsNotNone(client)
            self.assertTrue(key_id.startswith('rzp_live_'))

    # -------------------------------------------------------------------------
    # 2. /checkout route rendering
    # -------------------------------------------------------------------------
    def test_checkout_page_renders_with_cart_items(self):
        """Checkout page should render with items and show payment options"""
        self.login_test_user()
        cart_item = CartItem(user_id=self.test_user.id, product_id=self.test_product.id, quantity=2, size='M')
        db.session.add(cart_item)
        db.session.commit()

        response = self.client.get('/checkout')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('Choose Your Payment Method', html)
        self.assertIn('Razorpay Secure', html)
        self.assertIn('Cash on Delivery', html)
        self.assertIn('Payment Test T-Shirt', html)

    def test_checkout_page_shows_test_mode_notice_when_test_keys_active(self):
        """In test mode, checkout HTML must display warning that mobile UPI apps cannot scan test QR"""
        self.login_test_user()
        cart_item = CartItem(user_id=self.test_user.id, product_id=self.test_product.id, quantity=1, size='L')
        db.session.add(cart_item)
        db.session.commit()

        with patch.dict(os.environ, {
            'RAZORPAY_KEY_ID': 'rzp_test_AbCdEf123456',
            'RAZORPAY_KEY_SECRET': 'SecretKey1234567890'
        }, clear=False):
            response = self.client.get('/checkout')
            self.assertEqual(response.status_code, 200)
            html = response.data.decode('utf-8')
            self.assertIn('TEST MODE', html)
            self.assertIn('Why Mobile UPI App Scans Fail', html)
            self.assertIn('success@razorpay', html)

    def test_checkout_page_shows_unconfigured_when_no_keys(self):
        """When unconfigured, checkout HTML must display unconfigured warning and default to COD"""
        self.login_test_user()
        cart_item = CartItem(user_id=self.test_user.id, product_id=self.test_product.id, quantity=1, size='M')
        db.session.add(cart_item)
        db.session.commit()

        with patch.dict(os.environ, {
            'RAZORPAY_KEY_ID': 'rzp_test_your_key_id',
            'RAZORPAY_KEY_SECRET': 'your_key_secret'
        }, clear=False):
            response = self.client.get('/checkout')
            self.assertEqual(response.status_code, 200)
            html = response.data.decode('utf-8')
            self.assertIn('UNCONFIGURED', html)
            self.assertIn('Online Payment Gateway Unconfigured', html)

    # -------------------------------------------------------------------------
    # 3. /create_order endpoint tests
    # -------------------------------------------------------------------------
    def test_create_order_empty_cart(self):
        """Empty cart must return 400 bad request"""
        self.login_test_user()
        response = self.client.post('/create_order', json={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('empty', data['error'].lower())

    def test_create_order_unconfigured_gateway(self):
        """When keys are placeholders, /create_order returns 503 Service Unavailable"""
        self.login_test_user()
        cart_item = CartItem(user_id=self.test_user.id, product_id=self.test_product.id, quantity=1, size='M')
        db.session.add(cart_item)
        db.session.commit()

        with patch.dict(os.environ, {
            'RAZORPAY_KEY_ID': 'rzp_test_your_key_id',
            'RAZORPAY_KEY_SECRET': 'your_key_secret'
        }, clear=False):
            response = self.client.post('/create_order', json={})
            self.assertEqual(response.status_code, 503)
            data = response.get_json()
            self.assertFalse(data['success'])
            self.assertIn('not configured', data['error'].lower())

    def test_create_order_successful_with_mock(self):
        """Valid configured gateway returns order_id, amount in paise, and test mode status"""
        self.login_test_user()
        cart_item = CartItem(user_id=self.test_user.id, product_id=self.test_product.id, quantity=2, size='M')
        db.session.add(cart_item)
        db.session.commit()

        mock_client = MagicMock()
        mock_client.order.create.return_value = {'id': 'order_test_12345'}

        with patch('app.get_razorpay_client', return_value=(mock_client, 'rzp_test_mock123', 'mocksecret', True)):
            response = self.client.post('/create_order', json={})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['order_id'], 'order_test_12345')
            # 2 items * 450.0 (discount price) = 900.0 INR = 90000 paise
            self.assertEqual(data['amount'], 90000)
            self.assertEqual(data['currency'], 'INR')
            self.assertTrue(data['is_test_mode'])

    # -------------------------------------------------------------------------
    # 4. /verify_payment endpoint tests
    # -------------------------------------------------------------------------
    def test_verify_payment_missing_params(self):
        """Missing verification parameters returns 400"""
        self.login_test_user()
        response = self.client.post('/verify_payment', json={
            'razorpay_payment_id': '',
            'razorpay_order_id': '',
            'razorpay_signature': ''
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['status'], 'failure')

    def test_verify_payment_signature_mismatch(self):
        """Invalid signature raises SignatureVerificationError and returns 400"""
        self.login_test_user()
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.side_effect = razorpay.errors.SignatureVerificationError("Signature mismatch")

        with patch('app.get_razorpay_client', return_value=(mock_client, 'rzp_test_mock123', 'mocksecret', True)):
            response = self.client.post('/verify_payment', json={
                'razorpay_payment_id': 'pay_invalid123',
                'razorpay_order_id': 'order_invalid123',
                'razorpay_signature': 'sig_bad123'
            })
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertEqual(data['status'], 'failure')
            self.assertIn('signature', data['error'].lower())

    def test_verify_payment_successful_creates_order_and_deducts_stock(self):
        """Valid payment signature creates paid order, deducts product stock, and clears cart"""
        self.login_test_user()
        initial_stock = self.test_product.stock
        order_qty = 2
        cart_item = CartItem(user_id=self.test_user.id, product_id=self.test_product.id, quantity=order_qty, size='M')
        db.session.add(cart_item)
        db.session.commit()

        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.return_value = True

        with patch('app.get_razorpay_client', return_value=(mock_client, 'rzp_test_mock123', 'mocksecret', True)), \
             patch('app.send_order_email') as mock_email:
            response = self.client.post('/verify_payment', json={
                'razorpay_payment_id': 'pay_valid_999888',
                'razorpay_order_id': 'order_valid_777666',
                'razorpay_signature': 'sig_valid_555444',
                'first_name': 'Test',
                'last_name': 'Customer',
                'phone': '9876543210',
                'address': '123 Fashion Street',
                'city': 'Hyderabad',
                'state': 'Telangana',
                'zip_code': '500001'
            })
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            order_id = data['order_id']

            # Verify order in database
            saved_order = db.session.get(Order, order_id)
            self.assertIsNotNone(saved_order)
            self.assertEqual(saved_order.payment_method, 'Razorpay')
            self.assertEqual(saved_order.payment_status, 'Paid')
            self.assertEqual(saved_order.status, 'Paid')
            self.assertEqual(saved_order.payment_id, 'pay_valid_999888')
            self.assertEqual(saved_order.razorpay_order_id, 'order_valid_777666')

            # Verify stock deduction
            db.session.refresh(self.test_product)
            self.assertEqual(self.test_product.stock, initial_stock - order_qty)

            # Verify cart items were cleared
            remaining_cart = CartItem.query.filter_by(user_id=self.test_user.id).all()
            self.assertEqual(len(remaining_cart), 0)

    def test_verify_payment_idempotency_protection(self):
        """Duplicate verify_payment call with same payment_id returns already_processed without creating duplicate"""
        self.login_test_user()
        existing_order = Order(
            user_id=self.test_user.id,
            total_price=900.0,
            payment_method='Razorpay',
            payment_status='Paid',
            status='Paid',
            payment_id='pay_duplicate_112233',
            razorpay_order_id='order_duplicate_445566'
        )
        db.session.add(existing_order)
        db.session.commit()

        response = self.client.post('/verify_payment', json={
            'razorpay_payment_id': 'pay_duplicate_112233',
            'razorpay_order_id': 'order_duplicate_445566',
            'razorpay_signature': 'any_sig'
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data.get('already_processed'))
        self.assertEqual(data['order_id'], existing_order.id)

    # -------------------------------------------------------------------------
    # 5. /cod_success route tests
    # -------------------------------------------------------------------------
    def test_cod_success_flow(self):
        """Cash on Delivery orders are placed with Pending payment status and decrement stock"""
        self.login_test_user()
        initial_stock = self.test_product.stock
        order_qty = 1
        cart_item = CartItem(user_id=self.test_user.id, product_id=self.test_product.id, quantity=order_qty, size='M')
        db.session.add(cart_item)
        db.session.commit()

        with patch('app.send_order_email') as mock_email:
            response = self.client.get('/cod_success?first_name=Test&last_name=COD&phone=9876543210&address=Road1&city=Hyd&state=TS&zip_code=500001')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/track/', response.headers['Location'])

            # Verify order in DB
            latest_order = Order.query.filter_by(user_id=self.test_user.id).order_by(Order.id.desc()).first()
            self.assertIsNotNone(latest_order)
            self.assertEqual(latest_order.payment_method, 'COD')
            self.assertEqual(latest_order.payment_status, 'Pending')
            self.assertEqual(latest_order.status, 'Pending')

            # Verify stock deduction
            db.session.refresh(self.test_product)
            self.assertEqual(self.test_product.stock, initial_stock - order_qty)

            # Verify cart was cleared
            remaining_cart = CartItem.query.filter_by(user_id=self.test_user.id).all()
            self.assertEqual(len(remaining_cart), 0)

    # -------------------------------------------------------------------------
    # 6. /upi_payment route tests
    # -------------------------------------------------------------------------
    def test_upi_payment_route_redirects_to_checkout(self):
        """Accessing /upi_payment redirects cleanly to /checkout"""
        self.login_test_user()
        response = self.client.get('/upi_payment')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/checkout', response.headers['Location'])

if __name__ == '__main__':
    unittest.main()
