"""Tests for app.services.auth_service — Firebase token verification."""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# We must patch firebase_admin *before* auth_service is imported, because
# the module-level `from firebase_admin import auth` would otherwise try
# to import the real SDK.  We also patch _init_firebase to be a no-op so
# the global `_app` guard doesn't trigger real Firebase initialisation.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_firebase_init():
    """Prevent _init_firebase from calling the real firebase_admin SDK."""
    with patch("app.services.auth_service._init_firebase"):
        yield


class TestVerifyFirebaseToken:
    """Unit tests for verify_firebase_token()."""

    def test_verify_valid_token(self):
        """Mock firebase_admin.auth.verify_id_token to return decoded claims."""
        with patch("app.services.auth_service.auth") as mock_auth:
            mock_auth.verify_id_token.return_value = {
                "uid": "test_uid_123",
                "email": "test@example.com",
                "phone_number": "+919876543210",
                "name": "Test User",
            }
            from app.services.auth_service import verify_firebase_token

            result = verify_firebase_token("valid_token")

            assert result is not None
            assert result["uid"] == "test_uid_123"
            assert result["email"] == "test@example.com"
            assert result["phone"] == "+919876543210"
            assert result["name"] == "Test User"
            mock_auth.verify_id_token.assert_called_once_with("valid_token")

    def test_verify_valid_token_minimal_claims(self):
        """Token with only uid (no email/phone/name) still returns dict."""
        with patch("app.services.auth_service.auth") as mock_auth:
            mock_auth.verify_id_token.return_value = {
                "uid": "minimal_uid",
            }
            from app.services.auth_service import verify_firebase_token

            result = verify_firebase_token("minimal_token")

            assert result is not None
            assert result["uid"] == "minimal_uid"
            assert result["email"] is None
            assert result["phone"] is None
            assert result["name"] is None

    def test_verify_invalid_token(self):
        """An invalid token causes verify_id_token to raise; result is None."""
        with patch("app.services.auth_service.auth") as mock_auth:
            mock_auth.verify_id_token.side_effect = Exception("Invalid token")
            from app.services.auth_service import verify_firebase_token

            result = verify_firebase_token("bad_token")

            assert result is None

    def test_verify_expired_token(self):
        """An expired token causes verify_id_token to raise; result is None."""
        with patch("app.services.auth_service.auth") as mock_auth:
            mock_auth.verify_id_token.side_effect = Exception("Token expired")
            from app.services.auth_service import verify_firebase_token

            result = verify_firebase_token("expired_token")

            assert result is None

    def test_verify_network_error(self):
        """A network error during verification returns None gracefully."""
        with patch("app.services.auth_service.auth") as mock_auth:
            mock_auth.verify_id_token.side_effect = ConnectionError("Network unreachable")
            from app.services.auth_service import verify_firebase_token

            result = verify_firebase_token("any_token")

            assert result is None
