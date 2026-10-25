"""
Automated Unit Tests for Fashion World Pro Email OTP (Brevo HTTPS API & SMTP Fallback)
All outbound network calls are strictly mocked. No real emails or HTTP requests are sent.
"""

import os
import sys
import io
import unittest
from unittest.mock import patch, MagicMock
import smtplib
import socket
import requests
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import (
    app,
    send_brevo_email,
    resolve_brevo_sender,
    mask_email_safe,
    is_production_environment,
    BrevoAPIError,
    BrevoAuthError,
    BrevoValidationError,
    BrevoRateLimitError,
    BrevoTimeoutError,
    BrevoConnectionError,
    BrevoSSLError
)
from werkzeug.security import generate_password_hash


class TestBrevoHelperUnit(unittest.TestCase):
    """Unit tests for the send_brevo_email and resolve_brevo_sender helpers"""

    def setUp(self):
        self.canary_key = "xkeysib-canary-test-api-key-998877"

    def test_mask_email_safe(self):
        self.assertEqual(mask_email_safe("customer@example.com"), "cu***@example.com")
        self.assertEqual(mask_email_safe("a@example.com"), "a***@example.com")
        self.assertEqual(mask_email_safe("invalid-email"), "***")
        self.assertEqual(mask_email_safe(""), "***")
        self.assertEqual(mask_email_safe(None), "***")

    def test_resolve_brevo_sender_formats(self):
        # 1. Full standard RFC name <email> format
        res1 = resolve_brevo_sender("Fashion World Pro <store@fashionworld.pro>")
        self.assertEqual(res1, {"name": "Fashion World Pro", "email": "store@fashionworld.pro"})

        # 2. Plain email without name
        res2 = resolve_brevo_sender("store@fashionworld.pro")
        self.assertEqual(res2, {"name": "Fashion World Pro", "email": "store@fashionworld.pro"})

        # 3. Email enclosed in angle brackets
        res3 = resolve_brevo_sender("<store@fashionworld.pro>")
        self.assertEqual(res3, {"name": "Fashion World Pro", "email": "store@fashionworld.pro"})

        # 4. Fallback to MAIL_DEFAULT_SENDER when passed None
        with patch.dict(os.environ, {"MAIL_DEFAULT_SENDER": "Support <help@fashionworld.pro>"}):
            res4 = resolve_brevo_sender(None)
            self.assertEqual(res4, {"name": "Support", "email": "help@fashionworld.pro"})

        # 5. Brevo explicit environment sender (BREVO_SENDER_EMAIL / BREVO_SENDER_NAME)
        with patch.dict(os.environ, {"BREVO_SENDER_EMAIL": "verified@domain.com", "BREVO_SENDER_NAME": "Store Verified"}):
            res5 = resolve_brevo_sender(None)
            self.assertEqual(res5, {"name": "Store Verified", "email": "verified@domain.com"})

        # 6. Missing or unconfigured sender raises BrevoValidationError
        with patch.dict(os.environ, {"MAIL_DEFAULT_SENDER": "", "MAIL_USERNAME": "", "BREVO_SENDER_EMAIL": ""}):
            with self.assertRaises(BrevoValidationError):
                resolve_brevo_sender(None)
            with self.assertRaises(BrevoValidationError):
                resolve_brevo_sender("Fashion World Pro")

    def test_is_production_environment(self):
        with patch.dict(os.environ, {"RENDER": "true"}):
            self.assertTrue(is_production_environment())
        with patch.dict(os.environ, {"RENDER_SERVICE_ID": "srv-prod-9988"}):
            self.assertTrue(is_production_environment())
        with patch.dict(os.environ, {"FLASK_ENV": "production"}):
            self.assertTrue(is_production_environment())
        with patch.dict(os.environ, {"RENDER": "", "RENDER_SERVICE_ID": "", "RENDER_INSTANCE_ID": "", "FLASK_ENV": "development", "ENVIRONMENT": "development"}, clear=True):
            self.assertFalse(is_production_environment())

    @patch("requests.post")
    def test_send_brevo_email_success_payload_and_headers(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"messageId": "<msg-20261024-fw-123456>"}
        mock_post.return_value = mock_resp

        result = send_brevo_email(
            to_email="customer@example.com",
            subject="Your Login Code: 654321",
            html_content="<p>654321</p>",
            text_content="654321",
            sender="Fashion World Pro <orders@fashionworld.pro>",
            timeout=10.0,
            api_key=self.canary_key
        )

        self.assertEqual(result, {"messageId": "<msg-20261024-fw-123456>"})
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        # Verify URL
        self.assertEqual(args[0], "https://api.brevo.com/v3/smtp/email")

        # Verify Headers
        headers = kwargs.get("headers", {})
        self.assertEqual(headers.get("accept"), "application/json")
        self.assertEqual(headers.get("content-type"), "application/json")
        self.assertEqual(headers.get("api-key"), self.canary_key)

        # Verify Payload
        payload = kwargs.get("json", {})
        self.assertEqual(payload["sender"], {"name": "Fashion World Pro", "email": "orders@fashionworld.pro"})
        self.assertEqual(payload["to"], [{"email": "customer@example.com"}])
        self.assertEqual(payload["subject"], "Your Login Code: 654321")
        self.assertEqual(payload["htmlContent"], "<p>654321</p>")
        self.assertEqual(payload["textContent"], "654321")

        # Verify 10-second timeout
        self.assertEqual(kwargs.get("timeout"), 10.0)

    def test_send_brevo_email_missing_api_key_raises_auth_error(self):
        with patch.dict(os.environ, {}, clear=True):
            if "BREVO_API_KEY" in os.environ:
                del os.environ["BREVO_API_KEY"]
            with self.assertRaises(BrevoAuthError):
                send_brevo_email(
                    to_email="customer@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                    api_key=""
                )

    @patch("requests.post")
    def test_send_brevo_email_auth_failure_401_and_403(self, mock_post):
        # 401 Unauthorized
        mock_resp_401 = MagicMock()
        mock_resp_401.status_code = 401
        mock_resp_401.json.return_value = {"code": "unauthorized", "message": "Key not found"}
        mock_post.return_value = mock_resp_401

        with self.assertRaises(BrevoAuthError) as ctx:
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)
        self.assertEqual(ctx.exception.status_code, 401)

        # 403 Forbidden
        mock_resp_403 = MagicMock()
        mock_resp_403.status_code = 403
        mock_resp_403.json.return_value = {"code": "account_suspended", "message": "Account suspended"}
        mock_post.return_value = mock_resp_403

        with self.assertRaises(BrevoAuthError) as ctx:
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("requests.post")
    def test_send_brevo_email_validation_rejection_400(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"code": "invalid_parameter", "message": "Invalid email address format"}
        mock_post.return_value = mock_resp

        with self.assertRaises(BrevoValidationError) as ctx:
            send_brevo_email("bad-email", "Sub", "<p>H</p>", api_key=self.canary_key)
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("requests.post")
    def test_send_brevo_email_rate_limit_429(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"code": "too_many_requests", "message": "Rate limit exceeded"}
        mock_post.return_value = mock_resp

        with self.assertRaises(BrevoRateLimitError) as ctx:
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)
        self.assertEqual(ctx.exception.status_code, 429)

    @patch("requests.post")
    def test_send_brevo_email_server_error_500(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"message": "Internal gateway failure"}
        mock_post.return_value = mock_resp

        with self.assertRaises(BrevoAPIError) as ctx:
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)
        self.assertEqual(ctx.exception.status_code, 500)

    @patch("requests.post")
    def test_send_brevo_email_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("HTTPS connection timed out")

        with self.assertRaises(BrevoTimeoutError):
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)

    @patch("requests.post")
    def test_send_brevo_email_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to establish a new connection")

        with self.assertRaises(BrevoConnectionError):
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)

    @patch("requests.post")
    def test_send_brevo_email_ssl_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.SSLError("SSL certificate verify failed")

        with self.assertRaises(BrevoSSLError):
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)

    @patch("requests.post")
    def test_send_brevo_email_unexpected_request_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.ChunkedEncodingError("Connection broken: chunked stream ended")

        with self.assertRaises(BrevoAPIError):
            send_brevo_email("cust@example.com", "Sub", "<p>H</p>", api_key=self.canary_key)


class TestEmailOtpRoutesIntegration(unittest.TestCase):
    """Integration tests for /auth/email_otp/send and /auth/email_otp/verify with mocked delivery"""

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.canary_key = "xkeysib-test-canary-secret-556677"

    @patch("requests.post")
    @patch("app.send_mail_with_timeout")
    def test_route_send_otp_via_brevo_success(self, mock_smtp_send, mock_brevo_post):
        """When BREVO_API_KEY is configured, OTP dispatches via Brevo over HTTPS; SMTP is NOT called"""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"messageId": "<msg-success-777>"}
        mock_brevo_post.return_value = mock_resp

        with patch.dict(os.environ, {
            "BREVO_API_KEY": self.canary_key,
            "MAIL_DEFAULT_SENDER": "Fashion World Pro <orders@fashionworld.pro>"
        }):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("cooldown"), 60)
            self.assertIn("Verification code sent", data.get("message"))

            # Brevo was called, SMTP was NEVER called
            mock_brevo_post.assert_called_once()
            mock_smtp_send.assert_not_called()

            # Verify session state was created upon successful dispatch
            with self.client.session_transaction() as sess:
                self.assertIsNotNone(sess.get("email_otp_hash"))
                self.assertEqual(sess.get("email_otp_target"), "shopper@example.com")
                self.assertIsNotNone(sess.get("email_otp_expires_at"))
                self.assertEqual(sess.get("email_otp_attempts"), 0)
                self.assertIsNotNone(sess.get("email_otp_last_sent"))

    @patch("requests.post")
    @patch("app.send_mail_with_timeout")
    def test_route_send_otp_brevo_failure_does_not_fall_back_to_smtp(self, mock_smtp_send, mock_brevo_post):
        """When Brevo fails on production, it must NOT silently fall back to SMTP; session state must NOT be activated"""
        mock_brevo_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        with patch.dict(os.environ, {
            "BREVO_API_KEY": self.canary_key,
            "MAIL_USERNAME": "gmailuser@gmail.com",
            "MAIL_PASSWORD": "apppassword123"
        }):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 504)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("timed out", data.get("message").lower())

            # SMTP must NEVER be attempted on Brevo failure
            mock_smtp_send.assert_not_called()

            # Session OTP state and cooldown must NOT be activated
            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))
                self.assertIsNone(sess.get("email_otp_last_sent"))

    @patch("requests.post")
    @patch("app.send_mail_with_timeout")
    def test_route_send_otp_brevo_auth_failure_500(self, mock_smtp_send, mock_brevo_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"code": "unauthorized", "message": "Key not found"}
        mock_brevo_post.return_value = mock_resp

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 500)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("authentication failed", data.get("message").lower())

            # Ensure the secret API key is NOT leaked in the response
            self.assertNotIn(self.canary_key, resp.get_data(as_text=True))
            mock_smtp_send.assert_not_called()

            # Session state NOT activated
            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    def test_route_send_otp_brevo_validation_rejection_400(self, mock_brevo_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"code": "invalid_parameter", "message": "Domain not allowed"}
        mock_brevo_post.return_value = mock_resp

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 400)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("rejected", data.get("message").lower())

            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    def test_route_send_otp_brevo_rate_limit_429(self, mock_brevo_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"code": "too_many_requests", "message": "Rate limit exceeded"}
        mock_brevo_post.return_value = mock_resp

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 429)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("rate limit", data.get("message").lower())

            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    def test_route_send_otp_brevo_connection_error_502(self, mock_brevo_post):
        mock_brevo_post.side_effect = requests.exceptions.ConnectionError("DNS resolution failed")

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 502)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("unable to connect", data.get("message").lower())

            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    def test_route_send_otp_brevo_ssl_error_502(self, mock_brevo_post):
        mock_brevo_post.side_effect = requests.exceptions.SSLError("SSL handshake failure")

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 502)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("secure connection", data.get("message").lower())

            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    def test_route_send_otp_brevo_api_error_502(self, mock_brevo_post):
        """Base BrevoAPIError (e.g. 500 status code) returns 502 and does NOT activate session state"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"message": "Internal gateway failure"}
        mock_brevo_post.return_value = mock_resp

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 502)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("unable to deliver", data.get("message").lower())

            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    def test_route_send_otp_unconfigured_sender_400(self, mock_brevo_post):
        """When Brevo sender has no valid email configured, returns 400 and does NOT call Brevo"""
        with patch.dict(os.environ, {
            "BREVO_API_KEY": self.canary_key,
            "MAIL_DEFAULT_SENDER": "",
            "MAIL_USERNAME": ""
        }):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 400)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("rejected", data.get("message").lower())

            mock_brevo_post.assert_not_called()
            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    def test_route_safe_logging_and_provider_selection(self, mock_brevo_post):
        """Verifies stdout logs provider selection and masked identifiers, never leaks secrets"""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"messageId": "<msg-logged-123>"}
        mock_brevo_post.return_value = mock_resp

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            with patch.dict(os.environ, {
                "BREVO_API_KEY": self.canary_key,
                "MAIL_DEFAULT_SENDER": "Fashion World Pro <orders@fashionworld.pro>"
            }):
                with self.client.session_transaction() as sess:
                    sess.clear()
                self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

        log_output = captured_output.getvalue()
        self.assertIn("[EMAIL OTP] Active provider: Brevo HTTPS REST API (Port 443) for recipient sh***@example.com", log_output)
        self.assertIn("[EMAIL OTP] Brevo sender configured: Fashion World Pro <or***@fashionworld.pro>", log_output)
        self.assertIn("[EMAIL OTP] Verification code successfully dispatched via Brevo HTTPS for recipient sh***@example.com", log_output)
        self.assertNotIn(self.canary_key, log_output)
        self.assertNotIn("shopper@example.com", log_output)

    @patch("requests.post")
    @patch("app.send_mail_with_timeout")
    def test_route_send_otp_fallback_to_smtp_when_no_brevo_key(self, mock_smtp_send, mock_brevo_post):
        """When BREVO_API_KEY is omitted, the application uses SMTP for local development"""
        with patch.dict(os.environ, {
            "BREVO_API_KEY": "",
            "MAIL_USERNAME": "localdev@gmail.com",
            "MAIL_PASSWORD": "apppassword456",
            "MAIL_SERVER": "smtp.gmail.com",
            "MAIL_PORT": "587"
        }):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data.get("success"))

            # SMTP send was called; Brevo was NOT called
            mock_smtp_send.assert_called_once()
            mock_brevo_post.assert_not_called()

            with self.client.session_transaction() as sess:
                self.assertIsNotNone(sess.get("email_otp_hash"))

    @patch("requests.post")
    @patch("app.send_mail_with_timeout")
    def test_route_send_otp_smtp_timeout_handling(self, mock_smtp_send, mock_brevo_post):
        """When SMTP connection times out or drops unexpectedly, returns 504 and activates NO session state"""
        mock_smtp_send.side_effect = smtplib.SMTPServerDisconnected("Connection unexpectedly closed: timed out")

        with patch.dict(os.environ, {
            "BREVO_API_KEY": "",
            "MAIL_USERNAME": "localdev@gmail.com",
            "MAIL_PASSWORD": "apppassword456"
        }):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 504)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("timed out", data.get("message").lower())

            with self.client.session_transaction() as sess:
                self.assertIsNone(sess.get("email_otp_hash"))
                self.assertIsNone(sess.get("email_otp_last_sent"))

    @patch("app.send_mail_with_timeout")
    def test_route_send_otp_unconfigured_service_503(self, mock_smtp_send):
        """When neither Brevo nor SMTP credentials are configured, returns 503"""
        with patch.dict(os.environ, {
            "BREVO_API_KEY": "",
            "MAIL_USERNAME": "",
            "MAIL_PASSWORD": ""
        }):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 503)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("not configured", data.get("message").lower())
            mock_smtp_send.assert_not_called()

    @patch("requests.post")
    @patch("app.send_mail_with_timeout")
    def test_route_send_otp_production_missing_brevo_key_fails_503(self, mock_smtp_send, mock_brevo_post):
        """When running in production (e.g. Render) and BREVO_API_KEY is not configured, returns 503 promptly without attempting SMTP"""
        with patch.dict(os.environ, {
            "RENDER": "true",
            "BREVO_API_KEY": "",
            "MAIL_USERNAME": "gmailuser@gmail.com",
            "MAIL_PASSWORD": "apppassword123"
        }):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})

            self.assertEqual(resp.status_code, 503)
            data = resp.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("not configured on production", data.get("message").lower())

            # Outbound SMTP must NEVER be called on production when Brevo key is missing
            mock_smtp_send.assert_not_called()
            mock_brevo_post.assert_not_called()

    @patch("requests.post")
    def test_route_send_otp_no_sensitive_data_in_error_responses(self, mock_brevo_post):
        """Verifies that API keys, passwords, and raw provider payloads never leak into responses"""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {
            "code": "unauthorized",
            "message": f"Key {self.canary_key} is invalid for account"
        }
        mock_brevo_post.return_value = mock_resp

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            resp = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})
            resp_text = resp.get_data(as_text=True)

            self.assertNotIn(self.canary_key, resp_text)
            self.assertNotIn("unauthorized", resp_text)

    @patch("requests.post")
    def test_route_send_otp_cooldown_enforcement(self, mock_brevo_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"messageId": "<msg-cd-1>"}
        mock_brevo_post.return_value = mock_resp

        with patch.dict(os.environ, {"BREVO_API_KEY": self.canary_key}):
            with self.client.session_transaction() as sess:
                sess.clear()

            # First send: succeeds
            resp1 = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})
            self.assertEqual(resp1.status_code, 200)

            # Second send immediately: blocked by 60s cooldown (429)
            resp2 = self.client.post("/auth/email_otp/send", json={"email": "shopper@example.com"})
            self.assertEqual(resp2.status_code, 429)
            data2 = resp2.get_json()
            self.assertIn("wait", data2.get("message").lower())

    def test_route_verify_otp_max_attempts_and_expiry(self):
        """Validates OTP verification attempt lockout (5 max) and expiry handling"""
        target_email = "shopper@example.com"
        correct_otp = "889900"

        # 1. Test incorrect attempts up to limit
        with self.client.session_transaction() as sess:
            sess['email_otp_hash'] = generate_password_hash(correct_otp, method='pbkdf2:sha256')
            sess['email_otp_target'] = target_email
            sess['email_otp_expires_at'] = (datetime.utcnow() + timedelta(minutes=5)).timestamp()
            sess['email_otp_attempts'] = 0

        for i in range(1, 5):
            resp = self.client.post("/auth/email_otp/verify", json={"email": target_email, "otp": "000000"})
            self.assertEqual(resp.status_code, 400)
            self.assertIn(f"{5 - i} attempt(s) remaining", resp.get_json().get("message"))

        # 5th failed attempt: locks out and clears session
        resp_final = self.client.post("/auth/email_otp/verify", json={"email": target_email, "otp": "000000"})
        self.assertEqual(resp_final.status_code, 429)
        self.assertIn("Maximum attempts exceeded", resp_final.get_json().get("message"))

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('email_otp_hash'))

        # 2. Test expired OTP
        with self.client.session_transaction() as sess:
            sess['email_otp_hash'] = generate_password_hash(correct_otp, method='pbkdf2:sha256')
            sess['email_otp_target'] = target_email
            # Expired 1 minute ago
            sess['email_otp_expires_at'] = (datetime.utcnow() - timedelta(minutes=1)).timestamp()
            sess['email_otp_attempts'] = 0

        resp_expired = self.client.post("/auth/email_otp/verify", json={"email": target_email, "otp": correct_otp})
        self.assertEqual(resp_expired.status_code, 400)
        self.assertIn("expired", resp_expired.get_json().get("message").lower())


if __name__ == "__main__":
    unittest.main()
