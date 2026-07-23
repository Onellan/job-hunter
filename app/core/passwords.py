"""Small standard-library password hashing helpers using scrypt."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_N = 2**14
_R = 8
_P = 1
_KEY_LENGTH = 32


def hash_password(password: str) -> str:
    """Return a salted scrypt verifier suitable for durable local storage."""

    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_KEY_LENGTH)
    return "$".join(("scrypt", str(_N), str(_R), str(_P), _encode(salt), _encode(derived)))


def verify_password(password: str, encoded: str) -> bool:
    """Compare a password against a scrypt verifier without leaking comparison timing."""

    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode(), salt=_decode(salt), n=int(n), r=int(r), p=int(p), dklen=_KEY_LENGTH
        )
        return hmac.compare_digest(derived, _decode(expected))
    except (ValueError, TypeError):
        return False


def new_token() -> str:
    """Return a high-entropy URL-safe token for session or CSRF use."""

    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    """Return a one-way SHA-256 digest for database token lookup and storage."""

    return hashlib.sha256(token.encode()).hexdigest()


def _encode(value: bytes) -> str:
    """Encode bytes without padding for a compact verifier representation."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    """Decode an unpadded URL-safe base64 verifier component."""

    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
