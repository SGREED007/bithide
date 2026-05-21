"""
BitHide Backend - Processing Layer: PDF Steganography Engine
Hides data in PDF EOF (End-Of-File) comment markers.

Strategy:  Append a structured binary blob after the valid %%EOF marker.
           On extraction, locate the custom sentinel and read the payload.
"""

import struct
from pathlib import Path

from utils.logger import get_logger
from utils.exceptions import PayloadTooLargeForCarrierError, ExtractionError

logger = get_logger(__name__)

# Sentinel that marks the start of hidden data — unique enough to avoid false matches
_SENTINEL = b"%%BitHide-STEGO-V1|"
_SENTINEL_END = b"|%%"
_MAX_PDF_PAYLOAD = 10 * 1024 * 1024  # 10 MB cap on payload for PDFs


def encode_pdf(input_path: Path, payload: bytes, output_path: Path) -> None:
    """
    Append the encrypted payload after the PDF %%EOF marker using a custom sentinel.

    Args:
        input_path:  Original PDF carrier.
        payload:     Encrypted bytes to hide.
        output_path: Destination stego PDF.

    Raises:
        PayloadTooLargeForCarrierError: If payload exceeds 10 MB.
    """
    if len(payload) > _MAX_PDF_PAYLOAD:
        raise PayloadTooLargeForCarrierError()

    original_bytes = input_path.read_bytes()

    # Length-prefix the payload (4 bytes big-endian)
    length_prefix = struct.pack(">I", len(payload))
    hidden_block = _SENTINEL + length_prefix + payload + _SENTINEL_END

    stego_bytes = original_bytes + b"\n" + hidden_block
    output_path.write_bytes(stego_bytes)

    logger.info(f"PDF encoded: {input_path.name} → {output_path.name}, payload={len(payload)} bytes")


def decode_pdf(stego_path: Path) -> bytes:
    """
    Locate and extract the payload embedded after the PDF %%EOF marker.

    Returns:
        bytes: Raw extracted payload (still encrypted).

    Raises:
        ExtractionError: If the sentinel is not found or data is malformed.
    """
    try:
        data = stego_path.read_bytes()

        start_idx = data.rfind(_SENTINEL)
        if start_idx == -1:
            raise ExtractionError("No hidden data sentinel found in the PDF.")

        payload_start = start_idx + len(_SENTINEL)

        # Read the 4-byte length prefix
        length_prefix = data[payload_start : payload_start + 4]
        if len(length_prefix) < 4:
            raise ExtractionError("Payload length header is truncated.")

        payload_length = struct.unpack(">I", length_prefix)[0]
        payload = data[payload_start + 4 : payload_start + 4 + payload_length]

        if len(payload) != payload_length:
            raise ExtractionError("Extracted payload length mismatch — file may be corrupted.")

        logger.info(f"PDF decoded: {stego_path.name}, extracted {len(payload)} bytes")
        return payload
    except ExtractionError:
        raise
    except Exception as exc:
        logger.error(f"PDF decode error: {exc}")
        raise ExtractionError(detail=str(exc)) from exc
