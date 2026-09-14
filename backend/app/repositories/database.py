"""SQLAlchemy engine/table definitions.

SQLite is used for local development; the same Core table definition works on
PostgreSQL (set ``DATABASE_URL=postgresql+psycopg://...``). Only metadata and
artifact references are stored here - large artifacts stay on the filesystem
(later S3).
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import JSON, Column, DateTime, Float, Integer, MetaData, String, Table, Text, create_engine, event
from sqlalchemy.engine import Engine

metadata = MetaData()

simulations_table = Table(
    "simulations",
    metadata,
    Column("simulation_id", String(64), primary_key=True),
    Column("scenario_id", String(128), nullable=False, index=True),
    Column("model_version", String(128), nullable=False),
    Column("processing_version", String(128), nullable=False),
    Column("application_version", String(32), nullable=False),
    Column("status", String(16), nullable=False, index=True),
    Column("stage", String(32), nullable=False),
    Column("progress", Integer, nullable=False),
    Column("parameters", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)),
    Column("error_code", String(64)),
    Column("error_message", Text),
    Column("error_details", JSON),
    Column("model_sha256", String(64)),
    Column("rainfall_sha256", String(64)),
    Column("engine_version", String(32)),
    Column("swmm_exit_code", Integer),
    Column("swmm_elapsed_seconds", Float),
    Column("artifacts", JSON, nullable=False),
)


def create_db_engine(url: str) -> Engine:
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30}, future=True)

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        engine = create_engine(url, pool_pre_ping=True, future=True)
    metadata.create_all(engine)
    return engine
