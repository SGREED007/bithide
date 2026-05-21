"""
BitHide Backend - Integration Test Suite
Tests the full encode → decode pipeline for all three engines:
  - Image LSB (PNG)
  - Audio WAV LSB
  - PDF EOF injection

Run with:
    python test_run.py
"""

import sys
import os
import struct
import wave
import io

# Bootstrap path
sys.path.insert(0, os.path.dirname(__file__))

# Force Windows-safe tmp dirs
os.environ.setdefault("UPLOAD_FOLDER", "C:/tmp/bithide_uploads")
os.environ.setdefault("OUTPUT_FOLDER", "C:/tmp/bithide_outputs")
os.makedirs("C:/tmp/bithide_uploads", exist_ok=True)
os.makedirs("C:/tmp/bithide_outputs", exist_ok=True)
os.makedirs("logs", exist_ok=True)

from pathlib import Path
from PIL import Image

# ─── Import modules under test ───────────────────────────────────────────────
from security.encryption import encrypt_message, decrypt_payload
from processing.image_stego import encode_image, decode_image
from processing.audio_stego import encode_audio, decode_audio
from processing.pdf_stego import encode_pdf, decode_pdf
from utils.exceptions import DecryptionError

PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"
results = []


def record(name: str, passed: bool, detail: str = ""):
    tag = PASS if passed else FAIL
    print(f"{tag}  {name}" + (f"  ({detail})" if detail else ""))
    results.append((name, passed))


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS: create minimal in-memory carrier files
# ─────────────────────────────────────────────────────────────────────────────

def make_png(path: Path, width: int = 200, height: int = 200) -> Path:
    img = Image.new("RGB", (width, height), color=(100, 149, 237))
    img.save(str(path), format="PNG")
    return path


def make_wav(path: Path, n_frames: int = 44100) -> Path:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(44100)
        # Generate a simple sine-like pattern as 16-bit signed samples
        samples = [int(32767 * (i % 100) / 100) for i in range(n_frames)]
        wf.writeframes(struct.pack(f"<{n_frames}h", *samples))
    return path


def make_pdf(path: Path) -> Path:
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
        b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]>>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"trailer\n<</Size 4 /Root 1 0 R>>\nstartxref\n9\n%%EOF"
    )
    path.write_bytes(minimal_pdf)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# 1. ENCRYPTION UNIT TESTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n═══ Encryption Layer ═══")

SECRET = "Hello from BitHide -- this is a secret message with special chars: @#$%!"
KEY = "strong-passphrase-42"
WRONG_KEY = "wrong-key-000"

try:
    blob = encrypt_message(SECRET, KEY)
    recovered = decrypt_payload(blob, KEY)
    record("encrypt → decrypt roundtrip", recovered == SECRET, f"{len(blob)} bytes")
except Exception as e:
    record("encrypt → decrypt roundtrip", False, str(e))

try:
    blob = encrypt_message(SECRET, KEY)
    decrypt_payload(blob, WRONG_KEY)
    record("wrong key raises DecryptionError", False, "no exception raised")
except DecryptionError:
    record("wrong key raises DecryptionError", True)
except Exception as e:
    record("wrong key raises DecryptionError", False, str(e))

try:
    # Salt uniqueness: two encryptions of same plaintext must differ
    b1 = encrypt_message(SECRET, KEY)
    b2 = encrypt_message(SECRET, KEY)
    record("unique ciphertexts per call (salt randomness)", b1 != b2)
except Exception as e:
    record("unique ciphertexts per call (salt randomness)", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 2. IMAGE STEGANOGRAPHY TESTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n═══ Image Steganography (PNG) ═══")

carrier_png = Path("C:/tmp/bithide_uploads/test_carrier.png")
stego_png   = Path("C:/tmp/bithide_outputs/test_stego.png")

try:
    make_png(carrier_png, 200, 200)
    payload_bytes = encrypt_message(SECRET, KEY)
    encode_image(carrier_png, payload_bytes, stego_png)
    record("encode_image (200×200 PNG)", stego_png.exists(), f"{stego_png.stat().st_size} bytes")
except Exception as e:
    record("encode_image (200×200 PNG)", False, str(e))

try:
    recovered_bytes = decode_image(stego_png)
    message = decrypt_payload(recovered_bytes, KEY)
    record("decode_image → correct message", message == SECRET, repr(message[:40]))
except Exception as e:
    record("decode_image → correct message", False, str(e))

try:
    # Tiny image should reject oversized payload
    tiny_png = Path("C:/tmp/bithide_uploads/tiny.png")
    make_png(tiny_png, 4, 4)   # 4×4 = 48 channels = 6 bytes capacity
    big_payload = b"X" * 100
    encode_image(tiny_png, big_payload, Path("C:/tmp/bithide_outputs/should_fail.png"))
    record("over-capacity image raises error", False, "no exception raised")
except Exception as e:
    record("over-capacity image raises error", True, type(e).__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 3. AUDIO STEGANOGRAPHY TESTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n═══ Audio Steganography (WAV) ═══")

carrier_wav = Path("C:/tmp/bithide_uploads/test_carrier.wav")
stego_wav   = Path("C:/tmp/bithide_outputs/test_stego.wav")

try:
    make_wav(carrier_wav, 44100)
    payload_bytes = encrypt_message(SECRET, KEY)
    encode_audio(carrier_wav, payload_bytes, stego_wav)
    record("encode_audio (44100 frames WAV)", stego_wav.exists(), f"{stego_wav.stat().st_size} bytes")
except Exception as e:
    record("encode_audio (44100 frames WAV)", False, str(e))

try:
    recovered_bytes = decode_audio(stego_wav)
    message = decrypt_payload(recovered_bytes, KEY)
    record("decode_audio → correct message", message == SECRET, repr(message[:40]))
except Exception as e:
    record("decode_audio → correct message", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 4. PDF STEGANOGRAPHY TESTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n═══ PDF Steganography ═══")

carrier_pdf = Path("C:/tmp/bithide_uploads/test_carrier.pdf")
stego_pdf   = Path("C:/tmp/bithide_outputs/test_stego.pdf")

try:
    make_pdf(carrier_pdf)
    payload_bytes = encrypt_message(SECRET, KEY)
    encode_pdf(carrier_pdf, payload_bytes, stego_pdf)
    record("encode_pdf (minimal PDF)", stego_pdf.exists(), f"{stego_pdf.stat().st_size} bytes")
except Exception as e:
    record("encode_pdf (minimal PDF)", False, str(e))

try:
    recovered_bytes = decode_pdf(stego_pdf)
    message = decrypt_payload(recovered_bytes, KEY)
    record("decode_pdf → correct message", message == SECRET, repr(message[:40]))
except Exception as e:
    record("decode_pdf → correct message", False, str(e))

try:
    # No hidden data in clean PDF
    clean_pdf = Path("C:/tmp/bithide_uploads/clean.pdf")
    make_pdf(clean_pdf)
    from utils.exceptions import ExtractionError
    decode_pdf(clean_pdf)
    record("decode_pdf on clean file raises ExtractionError", False, "no exception")
except ExtractionError:
    record("decode_pdf on clean file raises ExtractionError", True)
except Exception as e:
    record("decode_pdf on clean file raises ExtractionError", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 5. FLASK API INTEGRATION TEST
# ─────────────────────────────────────────────────────────────────────────────
print("\n═══ Flask API (Test Client) ═══")

try:
    from app import create_app
    from unittest.mock import patch

    # Mock the DB call in the middleware so tests don't require an actual JWT/API Key in Supabase.
    class MockQuery:
        def select(self, *args): return self
        def eq(self, *args): return self
        def execute(self):
            class Resp:
                data = [{"id": "mock_id", "user_id": "mock_uid", "is_active": True}]
            return Resp()

    class MockSupabase:
        def table(self, *args): return MockQuery()

    app = create_app("development")
    client = app.test_client()

    # Health check
    resp = client.get("/health")
    record("GET /health → 200", resp.status_code == 200, resp.get_json().get("status"))
except Exception as e:
    record("GET /health → 200", False, str(e))
    client = None

if client:
    AUTH_HEADER = {"X-API-Key": "test-key-bypass"}

    # Missing file
    try:
        with patch("core.middlewares.get_supabase", return_value=MockSupabase()):
            resp = client.post("/encode", data={"message": "hi", "key": "abcdefgh"}, headers=AUTH_HEADER)
        record("POST /encode missing file → 400", resp.status_code == 400)
    except Exception as e:
        record("POST /encode missing file → 400", False, str(e))

    # Weak key
    try:
        with open(str(carrier_png), "rb") as f:
            with patch("core.middlewares.get_supabase", return_value=MockSupabase()):
                resp = client.post("/encode", data={
                    "message": "test", "key": "short",
                    "file": (f, "carrier.png", "image/png")
                }, content_type="multipart/form-data", headers=AUTH_HEADER)
        record("POST /encode weak key → 422", resp.status_code == 422)
    except Exception as e:
        record("POST /encode weak key → 422", False, str(e))

    # Full encode roundtrip via API
    try:
        with open(str(carrier_png), "rb") as f:
            with patch("core.middlewares.get_supabase", return_value=MockSupabase()):
                resp = client.post("/encode", data={
                    "message": SECRET, "key": KEY,
                    "file": (f, "carrier.png", "image/png")
                }, content_type="multipart/form-data", headers=AUTH_HEADER)
        record("POST /encode full roundtrip → 200", resp.status_code == 200,
               f"content-type={resp.content_type}")
    except Exception as e:
        record("POST /encode full roundtrip → 200", False, str(e))

    # Decode with wrong key via API
    try:
        stego_png_fresh = Path("C:/tmp/bithide_outputs/api_stego.png")
        make_png(carrier_png, 200, 200)
        payload = encrypt_message(SECRET, KEY)
        encode_image(carrier_png, payload, stego_png_fresh)
        with open(str(stego_png_fresh), "rb") as f:
            with patch("core.middlewares.get_supabase", return_value=MockSupabase()):
                resp = client.post("/decode", data={
                    "key": WRONG_KEY,
                    "file": (f, "stego.png", "image/png")
                }, content_type="multipart/form-data", headers=AUTH_HEADER)
        record("POST /decode wrong key → 422", resp.status_code == 422)
    except Exception as e:
        record("POST /decode wrong key → 422", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
total  = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed

print(f"\n{'═'*48}")
print(f"  Results: {passed}/{total} passed"
      + (f"  ·  {failed} FAILED" if failed else "  · All tests passed ✓"))
print(f"{'═'*48}\n")

sys.exit(0 if failed == 0 else 1)
