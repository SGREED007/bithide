"""
BitHide Backend - Application Layer: Stego Blueprint
API endpoints: POST /encode   POST /decode
"""

import os
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, after_this_request

from processing.orchestrator import run_encode, run_decode
from file_handler.handler import FileHandler
from core.middlewares import optional_api_key
from config import Config
from utils.logger import get_logger
from utils.exceptions import (
    BitHideException,
    MissingFieldError,
    MessageTooLongError,
    WeakKeyError,
)

logger = get_logger(__name__)
file_handler = FileHandler()

stego_bp = Blueprint("stego", __name__, url_prefix="/")


# ─── Input Validation Helpers ─────────────────────────────────────────────────

def _require_field(form_or_files, field: str) -> str:
    value = form_or_files.get(field, "").strip()
    if not value:
        raise MissingFieldError(field)
    return value


def _validate_message(message: str) -> None:
    if len(message) > Config.MAX_MESSAGE_LENGTH:
        raise MessageTooLongError(Config.MAX_MESSAGE_LENGTH)


def _validate_key(key: str) -> None:
    if len(key) < Config.MIN_KEY_LENGTH:
        raise WeakKeyError(Config.MIN_KEY_LENGTH)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@stego_bp.route("/encode", methods=["POST"])
@optional_api_key
def encode():
    """
    POST /encode
    Form-data:
        file    — carrier file (image / audio / pdf)
        message — secret plaintext string
        key     — AES passphrase
    Returns:
        Downloadable stego file (image: PNG, audio: WAV, pdf: PDF)
    """
    upload_path: Path = None
    output_path: Path = None

    try:
        # 1. Validate inputs
        if "file" not in request.files:
            raise MissingFieldError("file")

        file = request.files["file"]
        message = _require_field(request.form, "message")
        key = _require_field(request.form, "key")

        _validate_message(message)
        _validate_key(key)

        # 2. Validate and save upload
        file_handler.validate_upload(file)
        upload_path = file_handler.save_upload(file)

        # 3. Run encode pipeline
        output_path = run_encode(upload_path, message, key)

        logger.info(f"[ENCODE] SUCCESS | file={file.filename} | output={output_path.name}")

        # 4. Stream the stego file back
        mime = file_handler.get_mime(output_path)

        # FIX #3: Schedule output file deletion AFTER Flask finishes streaming it.
        # Deleting in `finally` would remove the file before send_file reads it.
        captured_output = output_path

        @after_this_request
        def _cleanup_output(response):
            file_handler.cleanup(captured_output)
            return response

        return send_file(
            str(output_path),
            mimetype=mime,
            as_attachment=True,
            download_name=f"bithide_stego{output_path.suffix}",
        )

    finally:
        # Only clean up the upload; output is cleaned via after_this_request
        file_handler.cleanup(upload_path)


@stego_bp.route("/decode", methods=["POST"])
@optional_api_key
def decode():
    """
    POST /decode
    Form-data:
        file — stego file previously produced by /encode
        key  — AES passphrase used during encoding
    Returns:
        JSON: { "message": "original secret message" }
    """
    upload_path: Path = None

    try:
        # 1. Validate inputs
        if "file" not in request.files:
            raise MissingFieldError("file")

        file = request.files["file"]
        key = _require_field(request.form, "key")
        _validate_key(key)

        # 2. Validate and save
        file_handler.validate_upload(file)
        upload_path = file_handler.save_upload(file)

        # 3. Run decode pipeline
        message = run_decode(upload_path, key)

        logger.info(f"[DECODE] SUCCESS | file={file.filename} | chars={len(message)}")

        return jsonify({"success": True, "message": message}), 200

    finally:
        file_handler.cleanup(upload_path)


# ─── Health Check ─────────────────────────────────────────────────────────────

@stego_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "BitHide API", "version": "1.0.0"}), 200
