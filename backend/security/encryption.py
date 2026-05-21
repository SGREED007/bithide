"""
BitHide Backend - Security Layer
AES-256 encryption/decryption via Fernet with PBKDF2 key derivation.
"""

import base64
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from utils.logger import get_logger
from utils.exceptions import EncryptionError, DecryptionError

logger = get_logger(__name__)

# Iterations for PBKDF2 - NIST recommended minimum
_PBKDF2_ITERATIONS = 480_000
# Salt is stored as a prefix to the ciphertext: [32 bytes salt | ciphertext]
_SALT_SIZE = 32


def _derive_key(passphrase: str, salt: bytes) -> Fernet:
    """Derive a Fernet-compatible AES key from a user passphrase + salt via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return Fernet(key)


def encrypt_message(message: str, passphrase: str) -> bytes:
    """
    Encrypt a plaintext message using AES-256 (Fernet) with PBKDF2 key derivation.

    Returns:
        bytes: [32-byte salt] + [Fernet ciphertext]
    """
    try:
        salt = os.urandom(_SALT_SIZE)
        fernet = _derive_key(passphrase, salt)
        ciphertext = fernet.encrypt(message.encode("utf-8"))
        payload = salt + ciphertext
        logger.debug(f"Encrypted message: {len(message)} chars → {len(payload)} bytes payload")
        return payload
    except Exception as exc:
        logger.error(f"Encryption error: {exc}")
        raise EncryptionError(detail=str(exc)) from exc


def decrypt_payload(payload: bytes, passphrase: str) -> str:
    """
    Decrypt a payload previously produced by `encrypt_message`.

    Args:
        payload: [32-byte salt] + [Fernet ciphertext]
        passphrase: User passphrase to derive the AES key.

    Returns:
        str: Original plaintext message.

    Raises:
        DecryptionError: If passphrase is wrong or data is corrupted.
    """
    try:
        salt = payload[:_SALT_SIZE]
        ciphertext = payload[_SALT_SIZE:]
        fernet = _derive_key(passphrase, salt)
        plaintext = fernet.decrypt(ciphertext).decode("utf-8")
        logger.debug(f"Decrypted payload successfully: {len(plaintext)} chars")
        return plaintext
    except InvalidToken:
        logger.warning("Decryption failed: invalid token (wrong key or corrupted data)")
        raise DecryptionError()
    except Exception as exc:
        logger.error(f"Unexpected decryption error: {exc}")
        raise DecryptionError() from exc
