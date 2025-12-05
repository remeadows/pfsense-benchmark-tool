"""
Simple authentication for the Flask app.
"""

import logging
from functools import wraps
from flask import request, Response, session
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication for the application."""

    def __init__(self, username: str, password: str):
        """
        Initialize auth manager.

        Args:
            username: Admin username
            password: Admin password (will be hashed)
        """
        self.username = username
        # Store password hash instead of plaintext
        self.password_hash = generate_password_hash(password)

    def verify_credentials(self, username: str, password: str) -> bool:
        """
        Verify username and password.

        Args:
            username: Username to check
            password: Password to check

        Returns:
            True if credentials are valid
        """
        if username != self.username:
            logger.warning(f"Invalid login attempt for user: {username}")
            return False

        if check_password_hash(self.password_hash, password):
            logger.info(f"Successful login for user: {username}")
            return True

        logger.warning(f"Invalid password for user: {username}")
        return False


def check_auth(auth: tuple[str, str], auth_manager: AuthManager) -> bool:
    """
    Check if username/password combination is valid.

    Args:
        auth: Tuple of (username, password)
        auth_manager: AuthManager instance

    Returns:
        True if credentials are valid
    """
    if not auth or len(auth) != 2:
        return False
    return auth_manager.verify_credentials(auth[0], auth[1])


def authenticate() -> Response:
    """Send a 401 response that enables basic auth."""
    return Response(
        "Authentication required. Please log in.",
        401,
        {"WWW-Authenticate": 'Basic realm="pfSense Benchmark Tool"'}
    )


def requires_auth(auth_manager: AuthManager):
    """
    Decorator to require authentication for a route.

    Args:
        auth_manager: AuthManager instance
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not check_auth((auth.username, auth.password) if auth else (None, None), auth_manager):
                return authenticate()
            return f(*args, **kwargs)
        return decorated
    return decorator
