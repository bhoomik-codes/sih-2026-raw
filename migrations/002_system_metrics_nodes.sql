-- =============================================================================
-- IBVAP — Supabase / PostgreSQL Migration
-- Migration: 002_system_metrics_nodes
-- Version:   v1.1 (Supabase-adapted from schema.md v1.0)
-- =============================================================================
--
-- This migration implements Phase 2 of the database schema:
--   - nodes: Tracks physical edge processing devices and backend servers.
--   - system_metrics: Time-series observability data for AI inference.
--   - audit_logs: Human/operator action tracking for compliance.
--
-- Run in Supabase Studio → SQL Editor
-- =============================================================================

-- ============================================================
-- 1. nodes
-- ============================================================
CREATE TABLE IF NOT EXISTS nodes (
    id                  TEXT        PRIMARY KEY,
    node_code           TEXT        NOT NULL UNIQUE,
    name                TEXT        NOT NULL,
    node_type           TEXT        NOT NULL
                        CHECK (node_type IN ('edge', 'backend', 'dashboard')),
    hostname            TEXT,
    ip_address          TEXT,
    operating_system    TEXT,
    cpu_model           TEXT,
    gpu_model           TEXT,
    gpu_vram_mb         INTEGER,
    status              TEXT        DEFAULT 'ONLINE'
                        CHECK (status IN ('ONLINE', 'OFFLINE', 'DEGRADED', 'ERROR')),
    last_heartbeat_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Note: update_updated_at() was created in 001_initial_schema.sql
CREATE TRIGGER nodes_updated_at
    BEFORE UPDATE ON nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);

-- ============================================================
-- 2. system_metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS system_metrics (
    id                  TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    node_id             TEXT        NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    cpu_percent         DOUBLE PRECISION,
    ram_percent         DOUBLE PRECISION,
    ram_used_mb         DOUBLE PRECISION,
    
    gpu_utilization     DOUBLE PRECISION,
    gpu_memory_used_mb  DOUBLE PRECISION,
    gpu_memory_total_mb DOUBLE PRECISION,
    gpu_temperature_c   DOUBLE PRECISION,
    
    inference_fps       DOUBLE PRECISION,
    inference_latency_ms DOUBLE PRECISION,
    queue_depth         INTEGER,
    dropped_frames      INTEGER,
    
    active_cameras      INTEGER,
    
    detector_status     TEXT,
    tracker_status      TEXT,
    backend_status      TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_node_time ON system_metrics(node_id, timestamp DESC);

-- ============================================================
-- 3. audit_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id                  TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id            TEXT        NOT NULL,
    action              TEXT        NOT NULL,
    entity_type         TEXT        NOT NULL,
    entity_id           TEXT,
    old_value           JSONB,
    new_value           JSONB,
    source_ip           TEXT,
    client_type         TEXT        CHECK (client_type IN ('desktop', 'mobile', 'api')),
    description         TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity    ON audit_logs(entity_type, entity_id);
