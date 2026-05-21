"""
BitHide Backend - Processing Layer: Steganography Orchestrator
Routes encode/decode operations to the correct engine based on file type.
"""

from pathlib import Path

from security.encryption import encrypt_message, decrypt_payload
from processing.image_stego import encode_image, decode_image
from processing.audio_stego import encode_audio, decode_audio
from processing.pdf_stego import encode_pdf, decode_pdf
from file_handler.handler import FileHandler
from utils.logger import get_logger
from utils.exceptions import UnsupportedOperationError

logger = get_logger(__name__)
file_handler = FileHandler()


def run_encode(input_path: Path, message: str, passphrase: str) -> Path:
    """
    Full encode pipeline:
        message → AES encrypt → stego engine → output file

    Returns:
        Path: Location of the generated stego file.
    """
    category = file_handler.categorize(input_path)
    logger.info(f"Encode pipeline: category={category}, input={input_path.name}")

    # Step 1: Encrypt
    encrypted_payload = encrypt_message(message, passphrase)

    # Step 2: Embed via the appropriate engine
    if category == "image":
        output_path = file_handler.reserve_output_path(".png")
        encode_image(input_path, encrypted_payload, output_path)

    elif category == "audio":
        output_path = file_handler.reserve_output_path(".wav")
        encode_audio(input_path, encrypted_payload, output_path)

    elif category == "pdf":
        output_path = file_handler.reserve_output_path(".pdf")
        encode_pdf(input_path, encrypted_payload, output_path)

    else:
        raise UnsupportedOperationError(detail=f"No encoder for category: {category}")

    logger.info(f"Encode complete → {output_path.name}")
    return output_path


def run_decode(stego_path: Path, passphrase: str) -> str:
    """
    Full decode pipeline:
        stego file → extract payload → AES decrypt → plaintext message

    Returns:
        str: The original plaintext secret message.
    """
    category = file_handler.categorize(stego_path)
    logger.info(f"Decode pipeline: category={category}, input={stego_path.name}")

    # Step 1: Extract raw encrypted payload
    if category == "image":
        encrypted_payload = decode_image(stego_path)
    elif category == "audio":
        encrypted_payload = decode_audio(stego_path)
    elif category == "pdf":
        encrypted_payload = decode_pdf(stego_path)
    else:
        raise UnsupportedOperationError(detail=f"No decoder for category: {category}")

    # Step 2: Decrypt
    message = decrypt_payload(encrypted_payload, passphrase)
    logger.info(f"Decode complete: {len(message)} chars recovered")
    return message
