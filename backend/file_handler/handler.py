"""
BitHide Backend - File Management Layer
Handles upload validation, saving, and secure cleanup.
"""

import os
import uuid
import mimetypes
from pathlib import Path
from werkzeug.datastructures import FileStorage

from config import Config
from utils.logger import get_logger
from utils.exceptions import (
    InvalidFileTypeError,
    FileTooLargeError,
    MissingFileError,
)

logger = get_logger(__name__)


class FileHandler:
    """Manages temporary file lifecycle: validation → save → cleanup."""

    def __init__(self):
        self.upload_dir = Path(Config.UPLOAD_FOLDER)
        self.output_dir = Path(Config.OUTPUT_FOLDER)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ─── Validation ──────────────────────────────────────────────────────────

    def validate_upload(self, file: FileStorage) -> None:
        """Validate file presence, size, and MIME type."""
        if file is None or file.filename == "":
            raise MissingFileError()

        # Check extension
        suffix = Path(file.filename).suffix.lower()
        if suffix not in Config.ALLOWED_EXTENSIONS:
            raise InvalidFileTypeError(suffix)

        # Check MIME type from content or header
        mime_type = file.mimetype or mimetypes.guess_type(file.filename)[0] or ""
        if mime_type not in Config.ALLOWED_MIME_TYPES:
            raise InvalidFileTypeError(mime_type)

        # Check file size
        file.seek(0, 2)  # seek to end
        size = file.tell()
        file.seek(0)  # reset
        if size > Config.MAX_CONTENT_LENGTH:
            raise FileTooLargeError(Config.MAX_CONTENT_LENGTH // (1024 * 1024))

        logger.debug(f"File validated: name={file.filename}, mime={mime_type}, size={size} bytes")

    # ─── Save ────────────────────────────────────────────────────────────────

    def save_upload(self, file: FileStorage) -> Path:
        """Save the validated upload to disk with a unique name. Returns Path."""
        suffix = Path(file.filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{suffix}"
        dest = self.upload_dir / unique_name
        file.save(str(dest))
        logger.info(f"File saved: {dest}")
        return dest

    def reserve_output_path(self, suffix: str) -> Path:
        """Create a unique output file path (file does not exist yet)."""
        unique_name = f"{uuid.uuid4().hex}_stego{suffix}"
        return self.output_dir / unique_name

    # ─── Cleanup ─────────────────────────────────────────────────────────────

    def cleanup(self, *paths: Path) -> None:
        """Securely delete temporary files after processing."""
        for path in paths:
            try:
                if path and path.exists():
                    os.remove(path)
                    logger.debug(f"Deleted temp file: {path}")
            except OSError as exc:
                logger.warning(f"Could not delete temp file {path}: {exc}")

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_mime(path: Path) -> str:
        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"

    @staticmethod
    def categorize(path: Path) -> str:
        """Return 'image' | 'audio' | 'pdf' based on extension."""
        ext = path.suffix.lower()
        if ext in {".jpg", ".jpeg", ".png"}:
            return "image"
        if ext in {".mp3", ".wav"}:
            return "audio"
        if ext == ".pdf":
            return "pdf"
        raise InvalidFileTypeError(ext)
