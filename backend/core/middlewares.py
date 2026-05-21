import hashlib
from functools import wraps
from flask import request, g

from core.database import get_supabase
from utils.exceptions import BitHideException


class UnauthorizedError(BitHideException):
    def __init__(self, detail: str = "Invalid API Key"):
        super().__init__(
            message=detail,
            status_code=401,
            error_code="UNAUTHORIZED"
        )


def require_api_key(f):
    """
    Decorator that checks for 'X-API-Key' or 'Authorization: Bearer <key>'.
    It hashes the key using SHA-256 and checks it against the 'api_keys' table in Supabase.
    If valid, it injects the 'user_id' and 'api_key_id' into Flask's `g` context.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Extract API Key
        raw_key = request.headers.get("X-API-Key")
        if not raw_key:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                raw_key = auth_header.split("Bearer ")[1].strip()
        
        if not raw_key:
            raise UnauthorizedError("Missing API Key. Provide 'X-API-Key' header or 'Authorization: Bearer <key>'.")

        # 2. Hash the key (must match how we will generate them later)
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        try:
            supabase = get_supabase()
            
            # 3. Lookup the hashed key
            response = supabase.table("api_keys").select("id, user_id, is_active").eq("api_key_hash", key_hash).execute()
            
            if not response.data:
                raise UnauthorizedError("Invalid API Key.")
            
            key_data = response.data[0]
            
            # 4. Check revocation status
            if not key_data.get("is_active"):
                raise UnauthorizedError("This API Key has been revoked.")

            # 5. Inject auth details into Flask context for downstream handlers and logging
            g.api_key_id = key_data["id"]
            g.user_id = key_data["user_id"]
            
        except BitHideException:
            raise
        except Exception as e:
            # Catch Supabase connectivity or logic errors and mask them into a clean 500
            raise BitHideException(
                message=f"Authentication service error: {e}",
                status_code=500,
                error_code="AUTH_FAILED"
            )

        return f(*args, **kwargs)
    return decorated_function


def optional_api_key(f):
    """
    Decorator that checks for an API key. If present, it validates it.
    If not, it allows the request to proceed anonymously.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        raw_key = request.headers.get("X-API-Key")
        if not raw_key:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                raw_key = auth_header.split("Bearer ")[1].strip()
        
        if not raw_key:
            # Proceed anonymously
            return f(*args, **kwargs)

        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        try:
            supabase = get_supabase()
            response = supabase.table("api_keys").select("id, user_id, is_active").eq("api_key_hash", key_hash).execute()
            
            if not response.data:
                raise UnauthorizedError("Invalid API Key.")
            
            key_data = response.data[0]
            
            if not key_data.get("is_active"):
                raise UnauthorizedError("This API Key has been revoked.")

            g.api_key_id = key_data["id"]
            g.user_id = key_data["user_id"]
            
        except BitHideException:
            raise
        except Exception as e:
            raise BitHideException(
                message=f"Authentication service error: {e}",
                status_code=500,
                error_code="AUTH_FAILED"
            )

        return f(*args, **kwargs)
    return decorated_function
