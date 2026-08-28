-- =============================================================================
-- IBVAP — Supabase / PostgreSQL Migration
-- Migration: 001_initial_schema
-- Version:   v1.1 (Supabase-adapted from schema.md v1.0)
-- =============================================================================
--
-- Key changes vs schema.md (SQLite → Postgres/Supabase):
--   - INTEGER booleans → BOOLEAN
--   - TEXT JSON fields → JSONB (native queryable Postgres JSON)
--   - TIMESTAMP → TIMESTAMPTZ with DEFAULT NOW()
--   - CHECK constraints on all enum columns
--   - source_url added to cameras (used by current backend/dashboard)
--   - evidence table EXCLUDED (deferred per project decision)
--   - detection_tracks / observations EXCLUDED (edge pipeline not ready)
--   - nodes / system_metrics EXCLUDED (added in 002 once dual-laptop is live)
--
-- Run in Supabase Studio → SQL Editor
-- =============================================================================

-- ============================================================
-- 1. cameras
-- ============================================================
CREATE TABLE IF NOT EXISTS cameras (
    id                  TEXT        PRIMARY KEY,
    camera_code         TEXT        NOT NULL UNIQUE,
    name                TEXT        NOT NULL,
    description         TEXT,
    source_type         TEXT        NOT NULL
                        CHECK (source_type IN ('rtsp','http','mjpeg','usb','file','smartphone')),
    source_url          TEXT,
    manufacturer        TEXT,
    model               TEXT,
    serial_number       TEXT,
    location_name       TEXT,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    enabled             BOOLEAN     NOT NULL DEFAULT TRUE,
    status              TEXT        NOT NULL DEFAULT 'UNKNOWN'
                        CHECK (status IN ('UNKNOWN','CONNECTING','ONLINE','DEGRADED','OFFLINE','RECONNECTING','ERROR')),
    inference_enabled   BOOLEAN     NOT NULL DEFAULT TRUE,
    stream_url          TEXT,
    last_seen_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cameras_updated_at
    BEFORE UPDATE ON cameras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status);
CREATE INDEX IF NOT EXISTS idx_cameras_enabled ON cameras(enabled);


-- ============================================================
-- 2. camera_streams
-- ============================================================
CREATE TABLE IF NOT EXISTS camera_streams (
    id                      TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    camera_id               TEXT        NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    stream_name             TEXT        NOT NULL,
    protocol                TEXT        NOT NULL
                            CHECK (protocol IN ('RTSP','HTTP','MJPEG','TCP','UDP')),
    connection_string       TEXT        NOT NULL,
    username                TEXT,
    password_encrypted      TEXT,
    stream_role             TEXT        NOT NULL DEFAULT 'primary'
                            CHECK (stream_role IN ('primary','secondary','snapshot')),
    resolution_width        INTEGER,
    resolution_height       INTEGER,
    source_fps              DOUBLE PRECISION,
    enabled                 BOOLEAN     NOT NULL DEFAULT TRUE,
    connection_timeout_ms   INTEGER     DEFAULT 5000,
    reconnect_enabled       BOOLEAN     NOT NULL DEFAULT TRUE,
    reconnect_attempts      INTEGER     DEFAULT 5,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER camera_streams_updated_at
    BEFORE UPDATE ON camera_streams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_streams_camera ON camera_streams(camera_id);


-- ============================================================
-- 3. zones
-- ============================================================
CREATE TABLE IF NOT EXISTS zones (
    id                  TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    camera_id           TEXT        NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    name                TEXT        NOT NULL,
    zone_type           TEXT        NOT NULL
                        CHECK (zone_type IN ('safe','warning','restricted','checkpoint','border','vehicle_only','fence')),
    description         TEXT,
    enabled             BOOLEAN     NOT NULL DEFAULT TRUE,
    severity_weight     INTEGER     DEFAULT 0,
    severity            TEXT        DEFAULT 'MEDIUM'
                        CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    config              JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER zones_updated_at
    BEFORE UPDATE ON zones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_zones_camera ON zones(camera_id);


-- ============================================================
-- 4. zone_points
-- ============================================================
CREATE TABLE IF NOT EXISTS zone_points (
    id          TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    zone_id     TEXT        NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    point_index INTEGER     NOT NULL,
    x           DOUBLE PRECISION NOT NULL,
    y           DOUBLE PRECISION NOT NULL,
    UNIQUE (zone_id, point_index)
);

CREATE INDEX IF NOT EXISTS idx_zone_points_zone ON zone_points(zone_id);


-- ============================================================
-- 5. rules
-- ============================================================
CREATE TABLE IF NOT EXISTS rules (
    id                  TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    name                TEXT        NOT NULL,
    rule_type           TEXT        NOT NULL
                        CHECK (rule_type IN ('loitering','zone_entry','zone_exit','fence_crossing','night_movement','direction_violation','anpr_trigger','custom')),
    description         TEXT,
    enabled             BOOLEAN     NOT NULL DEFAULT TRUE,
    priority            INTEGER     DEFAULT 0,
    threshold_value     DOUBLE PRECISION,
    threshold_unit      TEXT,
    cooldown_seconds    INTEGER     DEFAULT 0,
    risk_weight         DOUBLE PRECISION DEFAULT 0,
    severity            TEXT        DEFAULT 'MEDIUM'
                        CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    configuration       JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER rules_updated_at
    BEFORE UPDATE ON rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- 6. events
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id                  TEXT        PRIMARY KEY,
    event_code          TEXT        NOT NULL UNIQUE,
    camera_id           TEXT        NOT NULL REFERENCES cameras(id),
    track_id            TEXT,
    zone_id             TEXT        REFERENCES zones(id),
    rule_id             TEXT        REFERENCES rules(id),
    event_type          TEXT        NOT NULL,
    severity            TEXT        NOT NULL DEFAULT 'LOW'
                        CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    risk_score          DOUBLE PRECISION DEFAULT 0,
    confidence          DOUBLE PRECISION,
    capture_ts          TIMESTAMPTZ,
    ingest_ts           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_ts            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    display_ts          TIMESTAMPTZ,
    bbox_x1             DOUBLE PRECISION,
    bbox_y1             DOUBLE PRECISION,
    bbox_x2             DOUBLE PRECISION,
    bbox_y2             DOUBLE PRECISION,
    status              TEXT        NOT NULL DEFAULT 'ACTIVE'
                        CHECK (status IN ('ACTIVE','CONFIRMED','DISMISSED','RESOLVED')),
    description         TEXT,
    metadata            JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_camera_time ON events(camera_id, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_type        ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_severity    ON events(severity);
CREATE INDEX IF NOT EXISTS idx_events_status      ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_track       ON events(track_id);


-- ============================================================
-- 7. incidents
-- ============================================================
CREATE TABLE IF NOT EXISTS incidents (
    id                  TEXT        PRIMARY KEY,
    incident_code       TEXT        NOT NULL UNIQUE,
    camera_id           TEXT        NOT NULL REFERENCES cameras(id),
    track_id            TEXT,
    incident_type       TEXT        NOT NULL,
    severity            TEXT        NOT NULL
                        CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    risk_score          DOUBLE PRECISION NOT NULL DEFAULT 0,
    status              TEXT        NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN','ACKNOWLEDGED','RESOLVED','FALSE_POSITIVE','DISMISSED')),
    title               TEXT        NOT NULL,
    description         TEXT,
    first_event_ts      TIMESTAMPTZ,
    last_event_ts       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at     TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ,
    acknowledged_by     TEXT,
    resolved_by         TEXT
);

CREATE TRIGGER incidents_updated_at
    BEFORE UPDATE ON incidents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_incidents_camera   ON incidents(camera_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status   ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_time     ON incidents(created_at DESC);


-- ============================================================
-- 8. incident_events  (junction table — enables explainability)
-- ============================================================
CREATE TABLE IF NOT EXISTS incident_events (
    incident_id         TEXT        NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    event_id            TEXT        NOT NULL REFERENCES events(id)    ON DELETE CASCADE,
    contribution_score  DOUBLE PRECISION DEFAULT 0,
    is_primary          BOOLEAN     DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (incident_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_incident_events_incident ON incident_events(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_events_event    ON incident_events(event_id);


-- ============================================================
-- 9. anpr_results
-- ============================================================
CREATE TABLE IF NOT EXISTS anpr_results (
    id                      TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    camera_id               TEXT        NOT NULL REFERENCES cameras(id),
    track_id                TEXT,
    event_id                TEXT        REFERENCES events(id),
    vehicle_class           TEXT,
    plate_text              TEXT,
    normalized_plate        TEXT,
    detection_confidence    DOUBLE PRECISION,
    ocr_confidence          DOUBLE PRECISION,
    plate_bbox_x1           DOUBLE PRECISION,
    plate_bbox_y1           DOUBLE PRECISION,
    plate_bbox_x2           DOUBLE PRECISION,
    plate_bbox_y2           DOUBLE PRECISION,
    capture_ts              TIMESTAMPTZ,
    validation_status       TEXT        DEFAULT 'UNVERIFIED'
                            CHECK (validation_status IN ('UNVERIFIED','VERIFIED','FLAGGED')),
    metadata                JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anpr_camera ON anpr_results(camera_id);
CREATE INDEX IF NOT EXISTS idx_anpr_plate  ON anpr_results(normalized_plate);


-- ============================================================
-- 10. camera_health  (time-series — INSERT new row, never UPDATE)
-- ============================================================
CREATE TABLE IF NOT EXISTS camera_health (
    id                  TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    camera_id           TEXT        NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              TEXT        NOT NULL
                        CHECK (status IN ('ONLINE','OFFLINE','DEGRADED','ERROR')),
    fps                 DOUBLE PRECISION,
    latency_ms          DOUBLE PRECISION,
    dropped_frames      INTEGER     DEFAULT 0,
    dropped_frame_rate  DOUBLE PRECISION,
    queue_depth         INTEGER,
    decode_errors       INTEGER     DEFAULT 0,
    reconnect_count     INTEGER     DEFAULT 0,
    last_frame_at       TIMESTAMPTZ,
    stream_resolution   TEXT,
    error_message       TEXT
);

CREATE INDEX IF NOT EXISTS idx_health_camera_time ON camera_health(camera_id, timestamp DESC);


-- ============================================================
-- 11. system_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS system_logs (
    id                  TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    node_id             TEXT,
    component           TEXT        NOT NULL,
    level               TEXT        NOT NULL
                        CHECK (level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')),
    category            TEXT,
    message             TEXT        NOT NULL,
    exception_type      TEXT,
    stack_trace         TEXT,
    camera_id           TEXT        REFERENCES cameras(id),
    event_id            TEXT        REFERENCES events(id),
    incident_id         TEXT        REFERENCES incidents(id),
    metadata            JSONB
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level     ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_component ON system_logs(component);
CREATE INDEX IF NOT EXISTS idx_logs_camera    ON system_logs(camera_id);


-- ============================================================
-- 12. audit_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id                  TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id            TEXT,
    action              TEXT        NOT NULL,
    entity_type         TEXT        NOT NULL,
    entity_id           TEXT,
    old_value           JSONB,
    new_value           JSONB,
    source_ip           TEXT,
    client_type         TEXT        CHECK (client_type IN ('desktop','mobile','api')),
    description         TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity    ON audit_logs(entity_type, entity_id);


-- ============================================================
-- Seed: Default Rules
-- ============================================================
INSERT INTO rules (id, name, rule_type, description, enabled, threshold_value, threshold_unit, cooldown_seconds, risk_weight, severity, configuration)
VALUES
    ('rule_loitering_default',     'Restricted Zone Loitering',   'loitering',          'Person loiters in restricted zone',       TRUE, 30,   'seconds', 60,  20, 'HIGH',   '{"zone_types": ["restricted", "border"]}'),
    ('rule_fence_crossing',        'Virtual Fence Crossing',      'fence_crossing',     'Object crosses a virtual fence line',     TRUE, NULL, NULL,      10,  35, 'HIGH',   '{"directions": ["any"]}'),
    ('rule_zone_entry_restricted', 'Restricted Zone Entry',       'zone_entry',         'Object enters a restricted zone',         TRUE, NULL, NULL,      30,  20, 'MEDIUM', '{"zone_types": ["restricted"]}'),
    ('rule_zone_entry_border',     'Border Zone Entry',           'zone_entry',         'Object enters the border zone',           TRUE, NULL, NULL,      30,  25, 'HIGH',   '{"zone_types": ["border"]}'),
    ('rule_night_movement',        'Night Movement',              'night_movement',     'Movement detected during nighttime',      TRUE, NULL, NULL,      120, 25, 'HIGH',   '{"hours_start": 22, "hours_end": 5}'),
    ('rule_direction_violation',   'Wrong Direction Crossing',    'direction_violation','Object crosses in forbidden direction',   TRUE, NULL, NULL,      60,  15, 'MEDIUM', '{}'),
    ('rule_anpr_checkpoint',       'ANPR Checkpoint Trigger',     'anpr_trigger',       'Vehicle at checkpoint triggers ANPR',     TRUE, NULL, NULL,      5,   5,  'LOW',    '{}')
ON CONFLICT (id) DO NOTHING;
