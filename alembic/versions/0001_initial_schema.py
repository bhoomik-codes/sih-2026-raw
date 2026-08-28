"""create initial schema tables for supabase

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-28 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSON type with native JSONB on PostgreSQL/Supabase and JSON fallback on SQLite
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # ------------------------------------------------------------
    # 1. cameras
    # ------------------------------------------------------------
    op.create_table(
        "cameras",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("camera_code", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("manufacturer", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("serial_number", sa.Text(), nullable=True),
        sa.Column("location_name", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.Text(), nullable=False, server_default="UNKNOWN"),
        sa.Column(
            "inference_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("stream_url", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "source_type IN ('rtsp','http','mjpeg','usb','webcam','file','smartphone')",
            name="chk_cameras_source_type",
        ),
        sa.CheckConstraint(
            "status IN ('UNKNOWN','CONNECTING','ONLINE','DEGRADED','OFFLINE','RECONNECTING','ERROR')",
            name="chk_cameras_status",
        ),
    )
    op.create_index("idx_cameras_status", "cameras", ["status"])
    op.create_index("idx_cameras_enabled", "cameras", ["enabled"])

    # ------------------------------------------------------------
    # 2. camera_streams
    # ------------------------------------------------------------
    op.create_table(
        "camera_streams",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("stream_name", sa.Text(), nullable=False),
        sa.Column("protocol", sa.Text(), nullable=False),
        sa.Column("connection_string", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("stream_role", sa.Text(), nullable=False, server_default="primary"),
        sa.Column("resolution_width", sa.Integer(), nullable=True),
        sa.Column("resolution_height", sa.Integer(), nullable=True),
        sa.Column("source_fps", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("connection_timeout_ms", sa.Integer(), server_default="5000"),
        sa.Column(
            "reconnect_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("reconnect_attempts", sa.Integer(), server_default="5"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "protocol IN ('RTSP','HTTP','MJPEG','TCP','UDP')", name="chk_camera_streams_protocol"
        ),
        sa.CheckConstraint(
            "stream_role IN ('primary','secondary','snapshot')",
            name="chk_camera_streams_stream_role",
        ),
    )
    op.create_index("idx_streams_camera", "camera_streams", ["camera_id"])

    # ------------------------------------------------------------
    # 3. zones
    # ------------------------------------------------------------
    op.create_table(
        "zones",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("zone_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("severity_weight", sa.Integer(), server_default="0"),
        sa.Column("severity", sa.Text(), server_default="MEDIUM"),
        sa.Column("config", JSON_TYPE, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "zone_type IN ('safe','warning','restricted','checkpoint','border','vehicle_only','fence')",
            name="chk_zones_type",
        ),
        sa.CheckConstraint(
            "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="chk_zones_severity"
        ),
    )
    op.create_index("idx_zones_camera", "zones", ["camera_id"])

    # ------------------------------------------------------------
    # 4. zone_points
    # ------------------------------------------------------------
    op.create_table(
        "zone_points",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "zone_id", sa.Text(), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("point_index", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.UniqueConstraint("zone_id", "point_index", name="uq_zone_points_zone_idx"),
    )
    op.create_index("idx_zone_points_zone", "zone_points", ["zone_id"])

    # ------------------------------------------------------------
    # 5. rules
    # ------------------------------------------------------------
    op.create_table(
        "rules",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), server_default="0"),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("threshold_unit", sa.Text(), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), server_default="0"),
        sa.Column("risk_weight", sa.Float(), server_default="0"),
        sa.Column("severity", sa.Text(), server_default="MEDIUM"),
        sa.Column("configuration", JSON_TYPE, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "rule_type IN ('loitering','zone_entry','zone_exit','fence_crossing','night_movement','direction_violation','anpr_trigger','custom')",
            name="chk_rules_type",
        ),
        sa.CheckConstraint(
            "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="chk_rules_severity"
        ),
    )

    # ------------------------------------------------------------
    # 6. detection_tracks
    # ------------------------------------------------------------
    op.create_table(
        "detection_tracks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("object_class", sa.Text(), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("first_frame_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_frame_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence_avg", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("observation_count", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("status IN ('ACTIVE','LOST','CLOSED')", name="chk_tracks_status"),
    )
    op.create_index("idx_tracks_camera", "detection_tracks", ["camera_id"])
    op.create_index("idx_tracks_status", "detection_tracks", ["status"])

    # ------------------------------------------------------------
    # 7. observations
    # ------------------------------------------------------------
    op.create_table(
        "observations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "track_id",
            sa.Text(),
            sa.ForeignKey("detection_tracks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("capture_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingest_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("object_class", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("bbox_x1", sa.Float(), nullable=False),
        sa.Column("bbox_y1", sa.Float(), nullable=False),
        sa.Column("bbox_x2", sa.Float(), nullable=False),
        sa.Column("bbox_y2", sa.Float(), nullable=False),
        sa.Column("center_x", sa.Float(), nullable=True),
        sa.Column("center_y", sa.Float(), nullable=True),
        sa.Column(
            "zone_id", sa.Text(), sa.ForeignKey("zones.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("frame_number", sa.Integer(), nullable=True),
        sa.Column("inference_model", sa.Text(), nullable=True),
        sa.Column("inference_backend", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_observations_camera_time", "observations", ["camera_id", "capture_ts"])
    op.create_index("idx_observations_track", "observations", ["track_id"])

    # ------------------------------------------------------------
    # 8. events
    # ------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("event_code", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("track_id", sa.Text(), nullable=True),
        sa.Column(
            "zone_id", sa.Text(), sa.ForeignKey("zones.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "rule_id", sa.Text(), sa.ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False, server_default="LOW"),
        sa.Column("risk_score", sa.Float(), server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("capture_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ingest_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "event_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("display_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bbox_x1", sa.Float(), nullable=True),
        sa.Column("bbox_y1", sa.Float(), nullable=True),
        sa.Column("bbox_x2", sa.Float(), nullable=True),
        sa.Column("bbox_y2", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", JSON_TYPE, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="chk_events_severity"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','CONFIRMED','DISMISSED','RESOLVED')", name="chk_events_status"
        ),
    )
    op.create_index("idx_events_camera_time", "events", ["camera_id", sa.text("event_ts DESC")])
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index("idx_events_severity", "events", ["severity"])
    op.create_index("idx_events_status", "events", ["status"])
    op.create_index("idx_events_track", "events", ["track_id"])

    # ------------------------------------------------------------
    # 9. incidents
    # ------------------------------------------------------------
    op.create_table(
        "incidents",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("incident_code", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("track_id", sa.Text(), nullable=True),
        sa.Column("incident_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="OPEN"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("first_event_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="chk_incidents_severity"
        ),
        sa.CheckConstraint(
            "status IN ('OPEN','ACKNOWLEDGED','RESOLVED','FALSE_POSITIVE','DISMISSED')",
            name="chk_incidents_status",
        ),
    )
    op.create_index("idx_incidents_camera", "incidents", ["camera_id"])
    op.create_index("idx_incidents_status", "incidents", ["status"])
    op.create_index("idx_incidents_severity", "incidents", ["severity"])
    op.create_index("idx_incidents_time", "incidents", [sa.text("created_at DESC")])

    # ------------------------------------------------------------
    # 10. incident_events (Junction Table)
    # ------------------------------------------------------------
    op.create_table(
        "incident_events",
        sa.Column(
            "incident_id",
            sa.Text(),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id", sa.Text(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("contribution_score", sa.Float(), server_default="0"),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("incident_id", "event_id", name="pk_incident_events"),
    )
    op.create_index("idx_incident_events_incident", "incident_events", ["incident_id"])
    op.create_index("idx_incident_events_event", "incident_events", ["event_id"])

    # ------------------------------------------------------------
    # 11. evidence
    # ------------------------------------------------------------
    op.create_table(
        "evidence",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "incident_id",
            sa.Text(),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "event_id", sa.Text(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("evidence_type", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("capture_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hash_sha256", sa.Text(), nullable=True),
        sa.Column("metadata", JSON_TYPE, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "evidence_type IN ('snapshot','video_clip','plate_crop','face_crop','frame')",
            name="chk_evidence_type",
        ),
    )
    op.create_index("idx_evidence_incident", "evidence", ["incident_id"])
    op.create_index("idx_evidence_event", "evidence", ["event_id"])
    op.create_index("idx_evidence_camera", "evidence", ["camera_id"])

    # ------------------------------------------------------------
    # 12. anpr_results
    # ------------------------------------------------------------
    op.create_table(
        "anpr_results",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("track_id", sa.Text(), nullable=True),
        sa.Column(
            "event_id", sa.Text(), sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("vehicle_class", sa.Text(), nullable=True),
        sa.Column("plate_text", sa.Text(), nullable=True),
        sa.Column("normalized_plate", sa.Text(), nullable=True),
        sa.Column("detection_confidence", sa.Float(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("plate_bbox_x1", sa.Float(), nullable=True),
        sa.Column("plate_bbox_y1", sa.Float(), nullable=True),
        sa.Column("plate_bbox_x2", sa.Float(), nullable=True),
        sa.Column("plate_bbox_y2", sa.Float(), nullable=True),
        sa.Column("capture_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "evidence_id",
            sa.Text(),
            sa.ForeignKey("evidence.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("validation_status", sa.Text(), server_default="UNVERIFIED"),
        sa.Column("metadata", JSON_TYPE, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "validation_status IN ('UNVERIFIED','VERIFIED','FLAGGED')",
            name="chk_anpr_validation_status",
        ),
    )
    op.create_index("idx_anpr_camera", "anpr_results", ["camera_id"])
    op.create_index("idx_anpr_plate", "anpr_results", ["normalized_plate"])

    # ------------------------------------------------------------
    # 13. nodes
    # ------------------------------------------------------------
    op.create_table(
        "nodes",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("node_code", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("node_type", sa.Text(), nullable=False),
        sa.Column("hostname", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("operating_system", sa.Text(), nullable=True),
        sa.Column("cpu_model", sa.Text(), nullable=True),
        sa.Column("gpu_model", sa.Text(), nullable=True),
        sa.Column("gpu_vram_mb", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), server_default="ONLINE"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("node_type IN ('edge','backend','dashboard')", name="chk_nodes_type"),
    )

    # ------------------------------------------------------------
    # 14. camera_health
    # ------------------------------------------------------------
    op.create_table(
        "camera_health",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("dropped_frames", sa.Integer(), server_default="0"),
        sa.Column("dropped_frame_rate", sa.Float(), nullable=True),
        sa.Column("queue_depth", sa.Integer(), nullable=True),
        sa.Column("decode_errors", sa.Integer(), server_default="0"),
        sa.Column("reconnect_count", sa.Integer(), server_default="0"),
        sa.Column("last_frame_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stream_resolution", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('ONLINE','OFFLINE','DEGRADED','ERROR')", name="chk_camera_health_status"
        ),
    )
    op.create_index(
        "idx_health_camera_time", "camera_health", ["camera_id", sa.text("timestamp DESC")]
    )

    # ------------------------------------------------------------
    # 15. system_metrics
    # ------------------------------------------------------------
    op.create_table(
        "system_metrics",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "node_id", sa.Text(), sa.ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("ram_percent", sa.Float(), nullable=True),
        sa.Column("ram_used_mb", sa.Float(), nullable=True),
        sa.Column("gpu_utilization", sa.Float(), nullable=True),
        sa.Column("gpu_memory_used_mb", sa.Float(), nullable=True),
        sa.Column("gpu_memory_total_mb", sa.Float(), nullable=True),
        sa.Column("gpu_temperature_c", sa.Float(), nullable=True),
        sa.Column("inference_fps", sa.Float(), nullable=True),
        sa.Column("inference_latency_ms", sa.Float(), nullable=True),
        sa.Column("queue_depth", sa.Integer(), nullable=True),
        sa.Column("dropped_frames", sa.Integer(), nullable=True),
        sa.Column("active_cameras", sa.Integer(), nullable=True),
        sa.Column("detector_status", sa.Text(), nullable=True),
        sa.Column("tracker_status", sa.Text(), nullable=True),
        sa.Column("backend_status", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_metrics_node_time", "system_metrics", ["node_id", sa.text("timestamp DESC")]
    )

    # ------------------------------------------------------------
    # 16. system_logs
    # ------------------------------------------------------------
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "node_id", sa.Text(), sa.ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("component", sa.Text(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("exception_type", sa.Text(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column(
            "camera_id", sa.Text(), sa.ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "event_id", sa.Text(), sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "incident_id",
            sa.Text(),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata", JSON_TYPE, nullable=True),
        sa.CheckConstraint(
            "level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')", name="chk_system_logs_level"
        ),
    )
    op.create_index("idx_logs_timestamp", "system_logs", [sa.text("timestamp DESC")])
    op.create_index("idx_logs_level", "system_logs", ["level"])
    op.create_index("idx_logs_component", "system_logs", ["component"])
    op.create_index("idx_logs_camera", "system_logs", ["camera_id"])

    # ------------------------------------------------------------
    # 17. audit_logs
    # ------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("actor_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("old_value", JSON_TYPE, nullable=True),
        sa.Column("new_value", JSON_TYPE, nullable=True),
        sa.Column("source_ip", sa.Text(), nullable=True),
        sa.Column("client_type", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "client_type IN ('desktop','mobile','api')", name="chk_audit_logs_client_type"
        ),
    )
    op.create_index("idx_audit_timestamp", "audit_logs", [sa.text("timestamp DESC")])
    op.create_index("idx_audit_entity", "audit_logs", ["entity_type", "entity_id"])

    # ------------------------------------------------------------
    # Seed default rules
    # ------------------------------------------------------------
    op.execute(
        sa.text("""
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
        """)
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("system_logs")
    op.drop_table("system_metrics")
    op.drop_table("camera_health")
    op.drop_table("nodes")
    op.drop_table("anpr_results")
    op.drop_table("evidence")
    op.drop_table("incident_events")
    op.drop_table("incidents")
    op.drop_table("events")
    op.drop_table("observations")
    op.drop_table("detection_tracks")
    op.drop_table("rules")
    op.drop_table("zone_points")
    op.drop_table("zones")
    op.drop_table("camera_streams")
    op.drop_table("cameras")
