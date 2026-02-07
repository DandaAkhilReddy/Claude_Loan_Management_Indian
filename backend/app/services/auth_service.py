"""Firebase Admin SDK token verification."""

import logging

import firebase_admin
from firebase_admin import auth, credentials

from app.config import settings

logger = logging.getLogger(__name__)

_app = None


def _init_firebase():
    global _app
    if _app is not None:
        return
    try:
        if settings.firebase_project_id:
            _app = firebase_admin.initialize_app(options={
                "projectId": settings.firebase_project_id,
            })
        else:
            _app = firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized")
    except Exception as e:
        logger.warning(f"Firebase init failed (may already be initialized): {e}")


def verify_firebase_token(id_token: str) -> dict | None:
    """Verify a Firebase ID token and return decoded claims.

    Returns:
        Dict with uid, email, phone_number, name, etc. or None if invalid.
    """
    _init_firebase()
    try:
        decoded = auth.verify_id_token(id_token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email"),
            "phone": decoded.get("phone_number"),
            "name": decoded.get("name"),
        }
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None
