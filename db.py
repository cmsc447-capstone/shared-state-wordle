import os                       # Allows reading of environment variables
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()   # Ensure you have correct values in .env file

_admin: Client | None = None # No client created at import time

# Singleton. First call builds a client from URL and secret key.
# Subsequent calls are handed back the same client. This enables
# a single client for the whole server, one connection for every
# request.
def admin() -> Client:
    global _admin # Module level vairiable
    if _admin is None:
        _admin = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"]) # Secret key bypasses RLS
    return _admin