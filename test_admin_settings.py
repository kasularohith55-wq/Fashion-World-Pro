# Test script for Fashion World Pro Admin Settings
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, db, User, seed_db
from werkzeug.security import generate_password_hash, check_password_hash

def run_tests():
    print("\n========================================================")
    print("STARTING FASHION WORLD PRO ADMIN SETTINGS TESTS")
    print("========================================================\n")
    
    client = app.test_client()
    
    with app.app_context():
        # Setup clean isolated test admin
        test_email = "_test_settings_admin@fashionworld.test"
        admin = User.query.filter_by(email=test_email).first()
        if not admin:
            admin = User(
                username="_test_settings_admin",
                email=test_email,
                password=generate_password_hash("testadmin123", method="pbkdf2:sha256"),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
        else:
            admin.username = "_test_settings_admin"
            admin.password = generate_password_hash("testadmin123", method="pbkdf2:sha256")
            db.session.commit()
            
        print(f"[SETUP] Dedicated test admin initialized: {admin.email} (ID #{admin.id})")

        # ----------------------------------------------------
        # TEST 1: Unauthenticated protection
        # ----------------------------------------------------
        print("\n--- TEST 1: Unauthenticated Protection for Settings ---")
        unauth_resp = client.get('/admin/settings/account', follow_redirects=False)
        assert unauth_resp.status_code == 302
        assert '/admin_login' in unauth_resp.location
        print("[PASS] Unauthenticated access to /admin/settings/account redirected to /admin_login (302)")

        # ----------------------------------------------------
        # TEST 2: Customer / Non-admin protection
        # ----------------------------------------------------
        print("\n--- TEST 2: Customer Access Protection ---")
        customer = User.query.filter_by(is_admin=False).first()
        if customer:
            # Login as customer
            client.post('/login', data={'email': customer.email, 'password': 'customerpassword'}, follow_redirects=True)
            # Try to access admin settings
            cust_admin_resp = client.get('/admin/settings/account', follow_redirects=False)
            assert cust_admin_resp.status_code == 302
            assert '/admin_login' in cust_admin_resp.location
            print(f"[PASS] Customer '{customer.username}' blocked from accessing /admin/settings/account (redirected to /admin_login)")

        # ----------------------------------------------------
        # TEST 3: Admin Login and View Settings Page
        # ----------------------------------------------------
        print("\n--- TEST 3: Admin Login & View Settings Page ---")
        login_resp = client.post('/admin_login', data={
            'email': test_email,
            'password': 'testadmin123'
        }, follow_redirects=True)
        assert login_resp.status_code == 200
        
        settings_resp = client.get('/admin/settings/account')
        assert settings_resp.status_code == 200
        assert b"Administrator Profile" in settings_resp.data
        assert b"Change Admin Email" in settings_resp.data
        assert b"Change Security Password" in settings_resp.data
        assert test_email.encode() in settings_resp.data
        print("[PASS] /admin/settings/account successfully rendered for authenticated administrator.")

        # ----------------------------------------------------
        # TEST 4: Update Profile Information
        # ----------------------------------------------------
        print("\n--- TEST 4: Update Profile Details ---")
        profile_resp = client.post('/admin/settings/profile', data={
            'username': '_test_SuperAdmin',
            'first_name': 'Chief',
            'last_name': 'Executive',
            'phone': '+91 9988776655'
        }, follow_redirects=True)
        assert profile_resp.status_code == 200
        db.session.refresh(admin)
        assert admin.username == '_test_SuperAdmin'
        assert admin.first_name == 'Chief'
        assert admin.phone == '+91 9988776655'
        print(f"[PASS] Admin profile updated: Name='{admin.username}', Phone='{admin.phone}'")

        # ----------------------------------------------------
        # TEST 5: Change Admin Email Validations
        # ----------------------------------------------------
        print("\n--- TEST 5: Change Email Validations ---")
        # Wrong password
        resp = client.post('/admin/settings/change_email', data={
            'new_email': '_test_updated.admin@fashionworld.test',
            'confirm_new_email': '_test_updated.admin@fashionworld.test',
            'current_password': 'wrongpassword'
        }, follow_redirects=True)
        assert b"Incorrect current password" in resp.data
        print("[PASS] Wrong current password rejected for email change.")

        # Successful email update
        resp = client.post('/admin/settings/change_email', data={
            'new_email': '_test_updated.admin@fashionworld.test',
            'confirm_new_email': '_test_updated.admin@fashionworld.test',
            'current_password': 'testadmin123'
        }, follow_redirects=True)
        assert b"Administrator email updated successfully" in resp.data
        db.session.refresh(admin)
        assert admin.email == '_test_updated.admin@fashionworld.test'
        print(f"[PASS] Admin email successfully updated to: {admin.email}")

        # ----------------------------------------------------
        # TEST 6: Verify Login with New Email
        # ----------------------------------------------------
        print("\n--- TEST 6: Verify Login with New vs Old Email ---")
        # Logout
        client.get('/logout')
        
        # Try logging in with old email (should fail)
        old_login = client.post('/admin_login', data={
            'email': test_email,
            'password': 'testadmin123'
        }, follow_redirects=True)
        assert b"Login Unsuccessful" in old_login.data
        print(f"[PASS] Old email '{test_email}' is no longer accepted.")

        # Log in with new email (should succeed)
        new_login = client.post('/admin_login', data={
            'email': '_test_updated.admin@fashionworld.test',
            'password': 'testadmin123'
        }, follow_redirects=True)
        assert new_login.status_code == 200
        assert b"Command Center" in new_login.data or b"Dashboard" in new_login.data
        print("[PASS] New email '_test_updated.admin@fashionworld.test' authenticated successfully!")

        # ----------------------------------------------------
        # TEST 7: Change Admin Password Validations
        # ----------------------------------------------------
        print("\n--- TEST 7: Change Password Validations ---")
        # 1. Wrong current password
        resp = client.post('/admin/settings/change_password', data={
            'current_password': 'wrongpassword',
            'new_password': 'NewAdminPass2026',
            'confirm_new_password': 'NewAdminPass2026'
        }, follow_redirects=True)
        assert b"Current password verification failed" in resp.data
        print("[PASS] Wrong current password rejected for password change.")

        # 2. Mismatched passwords
        resp = client.post('/admin/settings/change_password', data={
            'current_password': 'testadmin123',
            'new_password': 'NewAdminPass2026',
            'confirm_new_password': 'DifferentPass2026'
        }, follow_redirects=True)
        assert b"do not match" in resp.data
        print("[PASS] Mismatched confirmation password rejected.")

        # 3. Short password (< 6 chars)
        resp = client.post('/admin/settings/change_password', data={
            'current_password': 'testadmin123',
            'new_password': '123',
            'confirm_new_password': '123'
        }, follow_redirects=True)
        assert b"at least 6 characters" in resp.data
        print("[PASS] Password shorter than 6 characters rejected.")

        # 4. Successful password update (should logout and redirect to /admin_login)
        resp = client.post('/admin/settings/change_password', data={
            'current_password': 'testadmin123',
            'new_password': 'NewAdminPass2026',
            'confirm_new_password': 'NewAdminPass2026'
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert '/admin_login' in resp.location
        print("[PASS] Password updated successfully and session cleanly terminated.")

        # ----------------------------------------------------
        # TEST 8: Verify Login with New Password
        # ----------------------------------------------------
        print("\n--- TEST 8: Verify Login with New vs Old Password ---")
        # Try logging in with old password
        old_pwd_login = client.post('/admin_login', data={
            'email': '_test_updated.admin@fashionworld.test',
            'password': 'testadmin123'
        }, follow_redirects=True)
        assert b"Login Unsuccessful" in old_pwd_login.data
        print("[PASS] Old password 'testadmin123' is no longer accepted.")

        # Log in with new password
        new_pwd_login = client.post('/admin_login', data={
            'email': '_test_updated.admin@fashionworld.test',
            'password': 'NewAdminPass2026'
        }, follow_redirects=True)
        assert new_pwd_login.status_code == 200
        assert b"Command Center" in new_pwd_login.data or b"Dashboard" in new_pwd_login.data
        print("[PASS] New password 'NewAdminPass2026' authenticated successfully!")

        # ----------------------------------------------------
        # TEST 9: Verify seed_db() Does NOT Overwrite Changed Credentials
        # ----------------------------------------------------
        print("\n--- TEST 9: Verify seed_db() Persistence Safety ---")
        # Call seed_db() as if the application restarted
        seed_db()
        
        # Verify that our test admin still has the updated email & password
        test_adm = User.query.filter_by(email='_test_updated.admin@fashionworld.test').first()
        assert test_adm is not None, "Test admin was deleted or overwritten by seed_db()!"
        assert check_password_hash(test_adm.password, 'NewAdminPass2026'), "Admin password was overwritten by seed_db()!"
        print("[PASS] seed_db() executed safely and did NOT overwrite credentials or duplicate accounts!")

        # ----------------------------------------------------
        # RESTORATION & CLEANUP
        # ----------------------------------------------------
        print("\n--- CLEANUP & RESTORATION ---")
        if test_adm:
            db.session.delete(test_adm)
            db.session.commit()
        print("[CLEANUP] Dedicated test admin safely cleaned up.")

    print("\n========================================================")
    print("ALL 9 ADMIN SETTINGS VERIFICATION SUITES PASSED (100%)!")
    print("========================================================\n")

if __name__ == '__main__':
    run_tests()

