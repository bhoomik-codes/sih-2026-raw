"""
apps.backend.db
----------------
Supabase PostgreSQL & SQLite Database Manager for IBVAP.
Handles database initialization, connection pooling, and CRUD operations.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("ibvap.backend.db")

# Load environment variables from .env if present
root_env = Path(__file__).resolve().parent.parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1qq0dkRbHVHb6L5v@db.pqenukgoizdlgplngpbc.supabase.co:5432/postgres"
)
DATABASE_ENABLED = os.getenv("DATABASE_ENABLED", "true").lower() in ("1", "true", "yes")

# Try importing asyncpg or psycopg2 / sqlalchemy
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class DatabaseManager:
    """Manages connection and query execution for Supabase PostgreSQL."""

    def __init__(self, uri: str = DATABASE_URL):
        self.uri = uri
        self.is_connected = False
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> bool:
        """Establish database connection pool and run migration/schema initialization."""
        if not DATABASE_ENABLED:
            logger.info("Database connection disabled via configuration.")
            return False

        if HAS_ASYNCPG:
            try:
                # Supabase requires SSL or direct TCP
                self.pool = await asyncpg.create_pool(
                    self.uri,
                    min_size=1,
                    max_size=10,
                    timeout=10.0,
                    command_timeout=10.0,
                    ssl="require" if "supabase.co" in self.uri or "supabase.com" in self.uri else False
                )
                self.is_connected = True
                logger.info("Connected to Supabase PostgreSQL via asyncpg.")
                await self.init_schema()
                return True
            except Exception as exc:
                logger.warning(f"Failed to connect to Supabase via asyncpg: {exc}")
                self.is_connected = False
        
        # Fallback test with psycopg2 if asyncpg failed or not present
        if HAS_PSYCOPG2:
            try:
                conn = psycopg2.connect(self.uri, connect_timeout=5)
                conn.close()
                self.is_connected = True
                logger.info("Verified Supabase PostgreSQL connection via psycopg2.")
                return True
            except Exception as exc:
                logger.warning(f"Failed to connect to Supabase via psycopg2: {exc}")
                self.is_connected = False

        return self.is_connected

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.is_connected = False
            logger.info("Supabase PostgreSQL connection pool closed.")

    async def init_schema(self) -> None:
        """Create necessary tables if they do not exist."""
        if not self.pool:
            return

        schema_sql = """
        CREATE TABLE IF NOT EXISTS cameras (
            camera_id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            source_url TEXT NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            status VARCHAR(32) DEFAULT 'OFFLINE',
            location JSONB DEFAULT '{}'::jsonb,
            inference_enabled BOOLEAN DEFAULT TRUE,
            stream_url TEXT,
            zones JSONB DEFAULT '[]'::jsonb,
            lines JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id VARCHAR(64) PRIMARY KEY,
            camera_id VARCHAR(64) REFERENCES cameras(camera_id) ON DELETE SET NULL,
            event_type VARCHAR(64) NOT NULL,
            severity VARCHAR(32) NOT NULL,
            track_id INT,
            rule_name VARCHAR(128),
            details JSONB DEFAULT '{}'::jsonb,
            timestamp DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id VARCHAR(64) PRIMARY KEY,
            camera_id VARCHAR(64),
            track_id INT,
            risk_score DOUBLE PRECISION NOT NULL,
            severity VARCHAR(32) NOT NULL,
            status VARCHAR(32) DEFAULT 'active',
            description TEXT,
            triggering_events JSONB DEFAULT '[]'::jsonb,
            acknowledged_at DOUBLE PRECISION,
            acknowledged_by VARCHAR(128),
            timestamp DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS system_metrics (
            id BIGSERIAL PRIMARY KEY,
            active_cameras INT DEFAULT 0,
            total_detections_today INT DEFAULT 0,
            active_incidents INT DEFAULT 0,
            system_health VARCHAR(64) DEFAULT 'Optimal',
            recorded_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
            logger.info("Supabase database tables verified and initialized.")

    async def get_cameras(self) -> List[Dict[str, Any]]:
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cameras ORDER BY created_at ASC")
            results = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("location"), str):
                    d["location"] = json.loads(d["location"])
                if isinstance(d.get("zones"), str):
                    d["zones"] = json.loads(d["zones"])
                if isinstance(d.get("lines"), str):
                    d["lines"] = json.loads(d["lines"])
                results.append(d)
            return results

    async def upsert_camera(self, camera: Dict[str, Any]) -> None:
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            query = """
            INSERT INTO cameras (camera_id, name, source_url, source_type, status, location, inference_enabled, stream_url, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, NOW())
            ON CONFLICT (camera_id) DO UPDATE SET
                name = EXCLUDED.name,
                source_url = EXCLUDED.source_url,
                source_type = EXCLUDED.source_type,
                status = EXCLUDED.status,
                location = EXCLUDED.location,
                inference_enabled = EXCLUDED.inference_enabled,
                stream_url = EXCLUDED.stream_url,
                updated_at = NOW();
            """
            await conn.execute(
                query,
                camera["camera_id"],
                camera["name"],
                camera["source_url"],
                camera["source_type"],
                camera.get("status", "OFFLINE"),
                json.dumps(camera.get("location") or {}),
                camera.get("inference_enabled", True),
                camera.get("stream_url"),
            )

    async def delete_camera(self, camera_id: str) -> None:
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM cameras WHERE camera_id = $1", camera_id)

    async def save_event(self, event: Dict[str, Any]) -> None:
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            query = """
            INSERT INTO events (event_id, camera_id, event_type, severity, track_id, rule_name, details, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
            ON CONFLICT (event_id) DO NOTHING;
            """
            await conn.execute(
                query,
                event["event_id"],
                event.get("camera_id"),
                event["event_type"],
                event["severity"],
                event.get("track_id"),
                event.get("rule_name"),
                json.dumps(event.get("details") or {}),
                event.get("timestamp", 0.0),
            )

    async def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM events ORDER BY timestamp DESC LIMIT $1", limit)
            results = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("details"), str):
                    d["details"] = json.loads(d["details"])
                results.append(d)
            return results

    async def save_incident(self, incident: Dict[str, Any]) -> None:
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            query = """
            INSERT INTO incidents (incident_id, camera_id, track_id, risk_score, severity, status, description, triggering_events, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
            ON CONFLICT (incident_id) DO UPDATE SET
                risk_score = EXCLUDED.risk_score,
                severity = EXCLUDED.severity,
                status = EXCLUDED.status,
                description = EXCLUDED.description,
                triggering_events = EXCLUDED.triggering_events;
            """
            await conn.execute(
                query,
                incident["incident_id"],
                incident.get("camera_id"),
                incident.get("track_id"),
                incident["risk_score"],
                incident["severity"],
                incident.get("status", "active"),
                incident.get("description"),
                json.dumps(incident.get("triggering_events") or []),
                incident.get("timestamp", 0.0),
            )

    async def get_incidents(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT $1", limit)
            results = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("triggering_events"), str):
                    d["triggering_events"] = json.loads(d["triggering_events"])
                results.append(d)
            return results

    async def check_health(self) -> Dict[str, Any]:
        """Verify database connectivity status."""
        if not DATABASE_ENABLED:
            return {"status": "disabled", "provider": "supabase"}
        if not self.pool:
            return {"status": "offline", "provider": "supabase"}
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return {"status": "online", "provider": "supabase"}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "provider": "supabase"}


# Global database instance
db = DatabaseManager()
