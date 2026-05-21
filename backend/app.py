"""
BitHide Backend - Application Entry Point
Creates the Flask app, registers blueprints, error handlers, CORS, and rate limiting.
"""

import os
import sys
import uuid

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config, config_map
from utils.logger import get_logger
from utils.exceptions import BitHideException

logger = get_logger("bithide.app")

def get_client_identity():
    """Identify client by API Key if present, else IP address"""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    return get_remote_address()


def create_app(env: str = "default") -> Flask:
    """Application factory pattern."""
    cfg = config_map.get(env, config_map["default"])
    cfg.ensure_directories()

    app = Flask(__name__)
    app.config.from_object(cfg)

    # ─── Extensions ──────────────────────────────────────────────────────────

    # CORS — Allow all origins to prevent preflight OPTIONS failures
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
    )

    # Rate limiter (in-memory; swap to Redis in production)
    limiter = Limiter(
        key_func=get_client_identity,
        app=app,
        default_limits=[cfg.RATE_LIMIT_DEFAULT],
        storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://"),
        headers_enabled=True, # Injects X-RateLimit limits in response headers!
    )

    # ─── SaaS Middlewares ────────────────────────────────────────────────────
    
    @app.before_request
    def attach_request_id():
        g.request_id = str(uuid.uuid4())
        
    @app.after_request
    def inject_request_id_header(response):
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        return response

    # ─── Blueprints ──────────────────────────────────────────────────────────
    # FIX #1: Import blueprint AFTER limiter is created, then register.
    # Apply per-route limits post-registration so view_functions dict is populated.
    from api.routes import stego_bp  # noqa: E402
    from api.auth import auth_bp
    
    app.register_blueprint(stego_bp)
    app.register_blueprint(auth_bp)

    # Apply per-route rate limits now that the view functions are registered
    limiter.limit(cfg.RATE_LIMIT_ENCODE)(app.view_functions["stego.encode"])
    limiter.limit(cfg.RATE_LIMIT_DECODE)(app.view_functions["stego.decode"])
    limiter.limit("5 per minute")(app.view_functions["auth.generate_api_key"])

    # ─── Centralised Error Handlers ──────────────────────────────────────────
    
    def _std_error(error_code: str, message: str, status_code: int):
        req_id = getattr(g, "request_id", "unknown")
        return jsonify({
            "success": False,
            "error_code": error_code,
            "message": message,
            "request_id": req_id
        }), status_code

    @app.errorhandler(BitHideException)
    def handle_bithide_exception(e):
        logger.warning(f"REJECTED | {e.error_code} | {e.message}")
        req_id = getattr(g, "request_id", "unknown")
        return jsonify(e.to_dict(req_id)), e.status_code

    @app.errorhandler(404)
    def not_found(_e):
        return _std_error("ENDPOINT_NOT_FOUND", "Endpoint not found.", 404)

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return _std_error("METHOD_NOT_ALLOWED", "Method not allowed.", 405)

    @app.errorhandler(413)
    def request_entity_too_large(_e):
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024) // (1024 * 1024)
        return _std_error("PAYLOAD_TOO_LARGE", f"File too large. Max {max_mb} MB.", 413)

    @app.errorhandler(429)
    def rate_limit_exceeded(_e):
        return _std_error("RATE_LIMIT_EXCEEDED", "Too many requests. Please slow down.", 429)

    @app.errorhandler(Exception)
    def internal_error(e):
        logger.error(f"Unhandled Exception: {e}", exc_info=True)
        return _std_error("INTERNAL_SERVER_ERROR", "An unexpected error occurred.", 500)

    logger.info(f"BitHide app created [env={env}]")
    return app


# ─── Dev Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Ensure imports resolve when running `python app.py` directly
    sys.path.insert(0, os.path.dirname(__file__))
    env = os.getenv("FLASK_ENV", "development")
    app = create_app(env)
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=app.config["DEBUG"],
    )
