"""Small standard-library authentication primitives for local M5 development."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


class AuthenticationError(ValueError):
    """Raised for invalid or expired access tokens."""


def hash_password(password: str) -> str:
    """Hash a password with scrypt; raw passwords are never persisted."""
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"{_encode(salt)}${_encode(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        encoded_salt, encoded_hash = encoded.split("$", maxsplit=1)
        salt = _decode(encoded_salt)
        expected = _decode(encoded_hash)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, secret: str, expires_minutes: int) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + expires_minutes * 60}
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def read_access_token(token: str, secret: str) -> str:
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        expected = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _decode(encoded_signature)):
            raise AuthenticationError("Invalid access token.")
        payload = json.loads(_decode(encoded_payload))
        if int(payload["exp"]) <= time.time():
            raise AuthenticationError("Access token has expired.")
        return str(payload["sub"])
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, AuthenticationError):
            raise
        raise AuthenticationError("Invalid access token.") from error


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
