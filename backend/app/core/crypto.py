"""
Encrypt/decrypt Saleor API tokens at rest (Fernet).
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_INSECURE_DEFAULT = "CHANGE_ME_IN_PRODUCTION_USE_64CHAR_SECRET"


def _fernet() -> Fernet | None:
    key = get_settings().token_encryption_key.strip()
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plain: str) -> str:
    if not plain:
        return ""
    f = _fernet()
    if f is None:
        return plain
    return f.encrypt(plain.encode()).decode()


def decrypt_token(stored: str) -> str:
    if not stored:
        return ""
    f = _fernet()
    if f is None:
        return stored
    try:
        return f.decrypt(stored.encode()).decode()
    except InvalidToken:
        return stored
