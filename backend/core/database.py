import os
from supabase import create_client, Client

_supabase_client = None

def get_supabase() -> Client:
    """Returns a singleton Supabase Client configured with the Service Role Key."""
    global _supabase_client
    if _supabase_client is None:
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_SERVICE_KEY", "")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in the environment.")
        
        # We must use the service_role key to bypass RLS and authenticate API keys
        _supabase_client = create_client(url, key)
        
    return _supabase_client
