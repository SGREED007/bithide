"""
BitHide Backend - Custom Exception Hierarchy
Centralized exception definitions for all layers.
"""


class BitHideException(Exception):
    """Base exception for the BitHide application."""

    def __init__(self, message: str = "An internal error occurred.", status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

    def to_dict(self, request_id: str = "unknown") -> dict:
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "request_id": request_id
        }


# ─── File Validation ─────────────────────────────────────────────────────────

class InvalidFileTypeError(BitHideException):
    def __init__(self, mime_type: str = ""):
        super().__init__(
            message=f"Unsupported file type: '{mime_type}'. Allowed: JPEG, PNG, MP3, WAV, PDF.",
            status_code=415,
            error_code="UNSUPPORTED_MEDIA_TYPE"
        )


class FileTooLargeError(BitHideException):
    def __init__(self, max_mb: int = 50):
        super().__init__(
            message=f"File exceeds the maximum allowed size of {max_mb} MB.",
            status_code=413,
            error_code="PAYLOAD_TOO_LARGE"
        )


class MissingFileError(BitHideException):
    def __init__(self):
        super().__init__(message="No file was provided in the request.", status_code=400, error_code="MISSING_FILE")


# ─── Input Validation ─────────────────────────────────────────────────────────

class MessageTooLongError(BitHideException):
    def __init__(self, max_len: int = 5000):
        super().__init__(
            message=f"Message exceeds maximum length of {max_len} characters.",
            status_code=422,
            error_code="MESSAGE_TOO_LONG"
        )


class WeakKeyError(BitHideException):
    def __init__(self, min_len: int = 8):
        super().__init__(
            message=f"Passphrase must be at least {min_len} characters long.",
            status_code=422,
            error_code="WEAK_PASSPHRASE"
        )


class MissingFieldError(BitHideException):
    def __init__(self, field: str):
        super().__init__(message=f"Required field missing: '{field}'.", status_code=400, error_code="MISSING_FIELD")


# ─── Encryption / Decryption ─────────────────────────────────────────────────

class EncryptionError(BitHideException):
    def __init__(self, detail: str = ""):
        super().__init__(
            message=f"Encryption failed. {detail}".strip(),
            status_code=500,
            error_code="ENCRYPTION_FAILED"
        )


class DecryptionError(BitHideException):
    def __init__(self):
        super().__init__(
            message="Decryption failed. The passphrase is incorrect or the file has been tampered with.",
            status_code=422,
            error_code="DECRYPTION_FAILED"
        )


# ─── Steganography ───────────────────────────────────────────────────────────

class PayloadTooLargeForCarrierError(BitHideException):
    def __init__(self):
        super().__init__(
            message="The encrypted message is too large to embed into the provided carrier file.",
            status_code=422,
            error_code="CARRIER_CAPACITY_EXCEEDED"
        )


class ExtractionError(BitHideException):
    def __init__(self, detail: str = ""):
        super().__init__(
            message=f"Failed to extract hidden data from file. {detail}".strip(),
            status_code=422,
            error_code="EXTRACTION_FAILED"
        )


# ─── Processing ──────────────────────────────────────────────────────────────

class UnsupportedOperationError(BitHideException):
    def __init__(self, detail: str = ""):
        super().__init__(
            message=f"Unsupported operation for this file type. {detail}".strip(),
            status_code=400,
            error_code="UNSUPPORTED_OPERATION"
        )
