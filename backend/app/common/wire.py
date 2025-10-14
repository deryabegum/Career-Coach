# backend/app/common/wire.py
from backend.app.db import get_db

def get_db_conn():
    """Return a live sqlite3 connection (row_factory=sqlite3.Row)."""
    return get_db()

# Can ignore
def get_db_and_models():
    """Return (sqlite_connection, models_dict). No ORM models for sqlite."""
    return get_db(), {}
