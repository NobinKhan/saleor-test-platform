"""Token encryption roundtrip tests."""

import os

from app.core.crypto import decrypt_token, encrypt_token


def test_encrypt_decrypt_roundtrip(monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key)

    from app.core.config import get_settings

    get_settings.cache_clear()

    plain = "secret-saleor-token"
    encrypted = encrypt_token(plain)
    assert encrypted != plain
    assert decrypt_token(encrypted) == plain

    get_settings.cache_clear()


def test_plaintext_fallback_without_key(monkeypatch):
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()

    plain = "token-no-key"
    assert encrypt_token(plain) == plain
    assert decrypt_token(plain) == plain

    get_settings.cache_clear()
