"""
BitHide Backend - Processing Layer: Image Steganography Engine
LSB (Least Significant Bit) encoding/decoding for PNG and JPEG images.
"""

from pathlib import Path
from PIL import Image

from utils.logger import get_logger
from utils.exceptions import PayloadTooLargeForCarrierError, ExtractionError

logger = get_logger(__name__)

# 32-bit unsigned int to store payload length prefix
_LENGTH_BITS = 32


def _payload_to_bits(payload: bytes) -> list[int]:
    """Convert bytes to a list of individual bits (MSB first)."""
    bits = []
    for byte in payload:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_bytes(bits: list[int]) -> bytes:
    """Convert list of bits back to bytes."""
    chars = []
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | bit
        chars.append(byte)
    return bytes(chars)


def _length_to_bits(length: int) -> list[int]:
    """Encode a 32-bit unsigned integer as a list of bits."""
    return [(length >> (31 - i)) & 1 for i in range(_LENGTH_BITS)]


def _bits_to_int(bits: list[int]) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def encode_image(input_path: Path, payload: bytes, output_path: Path) -> None:
    """
    Embed payload bytes into the LSB of each pixel channel of an image.
    Output is always saved as PNG to preserve lossless data.

    Args:
        input_path:  Path to the carrier image.
        payload:     Encrypted bytes to embed.
        output_path: Destination path for the stego image (always .png).

    Raises:
        PayloadTooLargeForCarrierError: If carrier has insufficient capacity.
    """
    img = Image.open(input_path).convert("RGB")
    data = bytearray(img.tobytes())

    payload_bits = _payload_to_bits(payload)
    length_bits = _length_to_bits(len(payload))
    full_bits = length_bits + payload_bits

    if len(full_bits) > len(data):
        raise PayloadTooLargeForCarrierError()

    for i, bit in enumerate(full_bits):
        data[i] = (data[i] & 0xFE) | bit

    stego_img = Image.frombytes("RGB", img.size, bytes(data))
    stego_img.save(str(output_path), format="PNG")
    logger.info(f"Image encoded: carrier={input_path.name}, payload={len(payload)} bytes → {output_path.name}")


def decode_image(stego_path: Path) -> bytes:
    """
    Extract the hidden payload from the LSBs of a stego image.

    Returns:
        bytes: Raw extracted payload (still encrypted).

    Raises:
        ExtractionError: If the image cannot be parsed or length header is corrupt.
    """
    try:
        img = Image.open(stego_path).convert("RGB")
        data = img.tobytes()

        # Read length prefix
        length_bits = [byte & 1 for byte in data[:_LENGTH_BITS]]
        payload_length = _bits_to_int(length_bits)

        max_payload_bytes = (len(data) - _LENGTH_BITS) // 8
        if payload_length <= 0 or payload_length > max_payload_bytes:
            raise ExtractionError("Invalid length header — file may not contain hidden data.")

        payload_bits = [byte & 1 for byte in data[_LENGTH_BITS : _LENGTH_BITS + payload_length * 8]]
        payload = _bits_to_bytes(payload_bits)

        logger.info(f"Image decoded: {stego_path.name}, extracted {len(payload)} bytes")
        return payload
    except ExtractionError:
        raise
    except Exception as exc:
        logger.error(f"Image decode error: {exc}")
        raise ExtractionError(detail=str(exc)) from exc
