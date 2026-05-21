"""
BitHide Backend - Processing Layer: Audio Steganography Engine
LSB encoding/decoding for WAV audio files.
MP3 input is converted to WAV in-memory before processing (MP3 is lossy → cannot be round-tripped).
"""

import wave
import struct
from pathlib import Path

from utils.logger import get_logger
from utils.exceptions import PayloadTooLargeForCarrierError, ExtractionError, UnsupportedOperationError

logger = get_logger(__name__)

_LENGTH_BYTES = 4  # 32-bit unsigned int for payload length prefix


# ─── Helper: bits ────────────────────────────────────────────────────────────

def _to_bits(data: bytes) -> list[int]:
    return [(byte >> (7 - i)) & 1 for byte in data for i in range(8)]


def _from_bits(bits: list[int]) -> bytes:
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | bit
        result.append(byte)
    return bytes(result)


# ─── WAV Encode ──────────────────────────────────────────────────────────────

def encode_audio(input_path: Path, payload: bytes, output_path: Path) -> None:
    """
    Embed payload bytes into WAV audio frame LSBs.
    Output is always WAV (lossless), regardless of input format.

    Raises:
        UnsupportedOperationError: If audio stream cannot be opened as WAV.
        PayloadTooLargeForCarrierError: If carrier capacity is insufficient.
    """
    if input_path.suffix.lower() not in {".wav"}:
        raise UnsupportedOperationError(
            detail="Only WAV audio is supported for LSB embedding. Convert MP3 to WAV first."
        )

    try:
        with wave.open(str(input_path), "rb") as wav_in:
            params = wav_in.getparams()
            n_frames = wav_in.getnframes()
            raw_frames = wav_in.readframes(n_frames)
    except wave.Error as exc:
        raise UnsupportedOperationError(detail=str(exc)) from exc

    # Convert raw bytes → list of sample integers (16-bit LE)
    sample_size = params.sampwidth
    sample_format = {1: "B", 2: "h", 4: "i"}.get(sample_size, "h")
    n_samples = len(raw_frames) // sample_size
    samples = list(struct.unpack(f"<{n_samples}{sample_format}", raw_frames[: n_samples * sample_size]))

    # Build payload with length prefix
    length_prefix = struct.pack(">I", len(payload))  # big-endian 4-byte length
    full_payload = length_prefix + payload
    payload_bits = _to_bits(full_payload)

    if len(payload_bits) > len(samples):
        raise PayloadTooLargeForCarrierError()

    # Embed bits into LSB of each sample - handle signed/unsigned uniformly
    # For signed 16-bit: mask with 0xFFFE (-2 in signed = 0xFFFE as uint16)
    # We use (s & ~1) which in Python integer arithmetic is always correct
    # because Python ints are arbitrary-precision two's complement
    modified_samples = list(samples)
    for i, bit in enumerate(payload_bits):
        s = modified_samples[i]
        # Zero out LSB and set to desired bit — correct for both signed and unsigned
        modified_samples[i] = (s & ~1) | bit

    modified_frames = struct.pack(f"<{n_samples}{sample_format}", *modified_samples)

    with wave.open(str(output_path), "wb") as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(modified_frames)

    logger.info(f"Audio encoded: {input_path.name} → {output_path.name}, payload={len(payload)} bytes")


# ─── WAV Decode ──────────────────────────────────────────────────────────────

def decode_audio(stego_path: Path) -> bytes:
    """
    Extract the hidden payload from WAV LSBs.

    Returns:
        bytes: Raw extracted payload (encrypted).

    Raises:
        ExtractionError: If the file cannot be parsed or the data is corrupt.
    """
    try:
        with wave.open(str(stego_path), "rb") as wav_in:
            n_frames = wav_in.getnframes()
            sample_size = wav_in.getsampwidth()
            raw_frames = wav_in.readframes(n_frames)

        sample_format = {1: "B", 2: "h", 4: "i"}.get(sample_size, "h")
        n_samples = len(raw_frames) // sample_size
        samples = struct.unpack(f"<{n_samples}{sample_format}", raw_frames[: n_samples * sample_size])

        # Extract all LSBs — use bitwise AND with 1, which correctly extracts
        # the least-significant bit for both signed and unsigned integers in Python.
        # Python's arbitrary-precision ints always give us the correct bit 0.
        all_bits = [s & 1 for s in samples]

        # Read 32-bit length prefix (first 32 bits)
        length_bits = all_bits[:32]
        length_bytes = _from_bits(length_bits)
        payload_length = struct.unpack(">I", length_bytes)[0]

        if payload_length <= 0 or (32 + payload_length * 8) > len(all_bits):
            raise ExtractionError("Invalid length header — audio may not contain hidden data.")

        payload_bits = all_bits[32 : 32 + payload_length * 8]
        payload = _from_bits(payload_bits)

        logger.info(f"Audio decoded: {stego_path.name}, extracted {len(payload)} bytes")
        return payload
    except ExtractionError:
        raise
    except Exception as exc:
        logger.error(f"Audio decode error: {exc}")
        raise ExtractionError(detail=str(exc)) from exc
