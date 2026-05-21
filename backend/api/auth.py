import hashlib
import secrets
from flask import Blueprint, request, jsonify

from core.database import get_supabase
from utils.exceptions import BitHideException
from utils.logger import get_logger

logger = get_logger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _verify_supabase_jwt(auth_header: str) -> str:
    """Verifies the Supabase JWT and returns the user ID."""
    if not auth_header or not auth_header.startswith("Bearer "):
        raise BitHideException(message="Missing or invalid Authorization header.", status_code=401, error_code="UNAUTHORIZED")

    token = auth_header.split("Bearer ")[1].strip()
    supabase = get_supabase()

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise BitHideException(message="Invalid authentication token.", status_code=401, error_code="UNAUTHORIZED")
        return user_response.user.id
    except Exception as e:
        logger.warning(f"JWT Verification failed: {e}")
        raise BitHideException(message="Invalid authentication token.", status_code=401, error_code="UNAUTHORIZED")


@auth_bp.route("/keys/generate", methods=["POST"])
def generate_api_key():
    """Endpoint for logged-in users to generate a fresh API key."""
    auth_header = request.headers.get("Authorization")
    user_id = _verify_supabase_jwt(auth_header)

    prefix = "bh_live_"
    entropy = secrets.token_hex(32)
    new_api_key = f"{prefix}{entropy}"

    key_hash = hashlib.sha256(new_api_key.encode("utf-8")).hexdigest()
    masked_key = f"{prefix}****{new_api_key[-4:]}"

    supabase = get_supabase()

    try:
        # Revoke existing keys
        supabase.table("api_keys").update({"is_active": False}).eq("user_id", user_id).execute()

        # Insert new key
        data = {
            "user_id": user_id,
            "api_key_hash": key_hash,
            "prefix": prefix,
            "masked_key": masked_key,
            "is_active": True
        }
        supabase.table("api_keys").insert(data).execute()

        logger.info(f"[AUTH] New API key generated for User:{user_id}")
        return jsonify({
            "success": True,
            "api_key": new_api_key,
            "masked_key": masked_key,
            "message": "Key generated successfully. Save this immediately, it will not be shown again."
        }), 201

    except Exception as e:
        logger.error(f"[AUTH] Failed to generate API key for User:{user_id}. Error: {e}")
        raise BitHideException(message="Failed to generate API key.", status_code=500, error_code="INTERNAL_ERROR")


@auth_bp.route("/keys/current", methods=["GET"])
def get_current_key():
    """Fetch user's current active API key info for dashboard."""
    auth_header = request.headers.get("Authorization")
    user_id = _verify_supabase_jwt(auth_header)

    supabase = get_supabase()
    
    try:
        response = supabase.table("api_keys").select("masked_key, created_at").eq("user_id", user_id).eq("is_active", True).execute()

        if not response.data:
            return jsonify({"success": True, "has_key": False}), 200

        key_info = response.data[0]
        return jsonify({
            "success": True,
            "has_key": True,
            "masked_key": key_info["masked_key"],
            "created_at": key_info["created_at"]
        }), 200
    except Exception as e:
        logger.error(f"[AUTH] Failed to fetch API key info for User:{user_id}. Error: {e}")
        raise BitHideException(message="Failed to fetch key info.", status_code=500, error_code="INTERNAL_ERROR")
