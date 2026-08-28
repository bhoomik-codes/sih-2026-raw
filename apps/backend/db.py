"""
apps.backend.db
----------------
IBVAP Database Client (Supabase PostgreSQL / Connection Pooler).

Supports:
1. Direct PostgreSQL SQLAlchemy / pg8000 pooler client (via DATABASE_URL)
2. Supabase PostgREST Client (via SUPABASE_URL + SUPABASE_SERVICE_KEY)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Check configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")


class _SQLTableQuery:
    """Helper that provides a fluent Supabase-compatible table query API over SQLAlchemy."""

    def __init__(self, engine, table_name: str) -> None:
        self._engine = engine
        self._table = table_name
        self._action = "select"
        self._select_cols = "*"
        self._filters: List[str] = []
        self._params: Dict[str, Any] = {}
        self._order_by: Optional[str] = None
        self._order_desc: bool = False
        self._limit_val: Optional[int] = None
        self._insert_records: List[Dict[str, Any]] = []
        self._upsert_record: Optional[Dict[str, Any]] = None

    def select(self, columns: str = "*", count: Optional[str] = None) -> "_SQLTableQuery":
        self._action = "select"
        if columns == "count" or count == "exact":
            self._select_cols = "count(*)"
        else:
            self._select_cols = columns
        return self

    def eq(self, column: str, value: Any) -> "_SQLTableQuery":
        param_name = f"p_{len(self._params)}"
        self._filters.append(f"{column} = :{param_name}")
        self._params[param_name] = value
        return self

    def order(self, column: str, desc: bool = False) -> "_SQLTableQuery":
        self._order_by = column
        self._order_desc = desc
        return self

    def limit(self, count: int) -> "_SQLTableQuery":
        self._limit_val = count
        return self

    def insert(self, record_or_records: Dict[str, Any] | List[Dict[str, Any]]) -> "_SQLTableQuery":
        self._action = "insert"
        self._insert_records = (
            [record_or_records] if isinstance(record_or_records, dict) else record_or_records
        )
        return self

    def upsert(self, record: Dict[str, Any]) -> "_SQLTableQuery":
        self._action = "upsert"
        self._upsert_record = record
        return self

    def execute(self) -> Any:
        if self._action == "insert":
            return self._execute_insert()
        elif self._action == "upsert":
            return self._execute_upsert()
        else:
            return self._execute_select()

    def _execute_select(self) -> Any:
        import sqlalchemy as sa

        sql = f"SELECT {self._select_cols} FROM {self._table}"
        if self._filters:
            sql += " WHERE " + " AND ".join(self._filters)
        if self._order_by:
            direction = "DESC" if self._order_desc else "ASC"
            sql += f" ORDER BY {self._order_by} {direction}"
        if self._limit_val is not None:
            sql += f" LIMIT {self._limit_val}"

        with self._engine.connect() as conn:
            result = conn.execute(sa.text(sql), self._params)
            rows = [dict(row._mapping) for row in result]

            class Result:
                data = rows

            return Result()

    def _execute_insert(self) -> Any:
        import sqlalchemy as sa

        if not self._insert_records:

            class EmptyResult:
                data = []

            return EmptyResult()

        inserted_rows = []
        with self._engine.begin() as conn:
            for rec in self._insert_records:
                clean_rec = {}
                for k, v in rec.items():
                    if isinstance(v, (dict, list)):
                        clean_rec[k] = json.dumps(v)
                    else:
                        clean_rec[k] = v

                cols = list(clean_rec.keys())
                placeholders = [f":{c}" for c in cols]
                sql = f"INSERT INTO {self._table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                conn.execute(sa.text(sql), clean_rec)
                inserted_rows.append(rec)

        class Result:
            data = inserted_rows

        return Result()

    def _execute_upsert(self) -> Any:
        import sqlalchemy as sa

        if not self._upsert_record:

            class EmptyResult:
                data = []

            return EmptyResult()

        clean_rec = {}
        for k, v in self._upsert_record.items():
            if isinstance(v, (dict, list)):
                clean_rec[k] = json.dumps(v)
            else:
                clean_rec[k] = v

        cols = list(clean_rec.keys())
        placeholders = [f":{c}" for c in cols]
        update_set = [f"{c} = EXCLUDED.{c}" for c in cols if c != "id"]

        sql = f"INSERT INTO {self._table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
        if update_set:
            sql += f" ON CONFLICT (id) DO UPDATE SET {', '.join(update_set)}"
        else:
            sql += " ON CONFLICT (id) DO NOTHING"

        with self._engine.begin() as conn:
            conn.execute(sa.text(sql), clean_rec)

        class Result:
            data = [self._upsert_record]

        return Result()


class _SQLDatabaseClient:
    """Database client using SQLAlchemy / pg8000 pooler."""

    def __init__(self, db_url: str) -> None:
        import sqlalchemy as sa

        url = db_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+pg8000://", 1)
        self._engine = sa.create_engine(url, pool_pre_ping=True)

    def table(self, table_name: str) -> _SQLTableQuery:
        return _SQLTableQuery(self._engine, table_name)


_CACHED_CLIENT = None


def get_db():
    """Return initialized database client."""
    global _CACHED_CLIENT
    if _CACHED_CLIENT is not None:
        return _CACHED_CLIENT

    if DATABASE_URL:
        _CACHED_CLIENT = _SQLDatabaseClient(DATABASE_URL)
        return _CACHED_CLIENT

    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client

        _CACHED_CLIENT = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _CACHED_CLIENT

    raise RuntimeError(
        "Database is not configured. Set DATABASE_URL or SUPABASE_URL & SUPABASE_SERVICE_KEY in .env"
    )


def db_enabled() -> bool:
    """Return True if a database connection URL is configured."""
    return bool(DATABASE_URL or (SUPABASE_URL and SUPABASE_KEY))
