"""
IBVAP Backend — Supabase database client
----------------------------------------
Single module that owns the Supabase connection.
All route handlers import `get_db()` from here.

Requires in .env:
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...   (service-role key — never exposed to browser)
"""

import os
from functools import lru_cache
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()  # reads .env from project root


@lru_cache(maxsize=1)
def get_db() -> Client:
    """Return a cached Supabase client (singleton per process)."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env\n"
            "Copy .env.example → .env and fill in your project credentials."
        )

    return create_client(url, key)


def db_enabled() -> bool:
    """Return True only when Supabase credentials are configured."""
    return bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_SERVICE_KEY"))
