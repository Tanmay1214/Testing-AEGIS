"""
app/services/ingestion.py
Ingestion Layer — reads raw CSVs, decodes Base64 serial numbers,
resolves schema rotation, and bulk-inserts into PostgreSQL.
"""
import base64
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import get_settings
from app.models.orm import Node, SystemLog, SchemaConfig

logger = logging.getLogger("aegis.ingestion")
settings = get_settings()


# ─── Base64 Decoding ──────────────────────────────────────────────────────────

def decode_serial_number(user_agent: str) -> str:
    """
    Extract and decode the Base64 serial number embedded in the user_agent string.
    Format: 'AEGIS-Node/2.0 (Linux) <base64>'
    Returns decoded string e.g. 'SN-9280', or raw token on failure.
    """
    try:
        token = user_agent.strip().split()[-1]
        decoded = base64.b64decode(token).decode("utf-8").strip()
        return decoded
    except Exception:
        logger.warning("Failed to decode serial from user_agent: %s", user_agent)
        return user_agent.split()[-1]  # fallback: keep raw


# ─── Schema Resolution ────────────────────────────────────────────────────────

def resolve_active_column(log_id: int, schema_df: pd.DataFrame) -> str:
    """
    Given a log_id, determine which column is active based on schema_config.
    Schema rotates: version 1 → load_val (log_id < 5000)
                    version 2 → L_V1     (log_id >= 5000)
    """
    active = schema_df[schema_df["time_start"] <= log_id].sort_values(
        "time_start", ascending=False
    ).iloc[0]["active_column"]
    return active


# ─── Node Registry Ingestion ─────────────────────────────────────────────────

def load_node_registry(path: str | None = None) -> pd.DataFrame:
    """
    Load and enrich node_registry.csv.
    Adds 'serial_number' column with decoded Base64 values.
    """
    path = path or settings.NODE_REGISTRY_PATH
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["serial_number"] = df["user_agent"].apply(decode_serial_number)
    logger.info("Loaded %d nodes (%d infected)", len(df), df["is_infected"].sum())
    return df


# ─── System Logs Ingestion ────────────────────────────────────────────────────

def load_system_logs(
    logs_path: str | None = None,
    schema_path: str | None = None,
) -> pd.DataFrame:
    """
    Load system_logs.csv and annotate each row with:
    - active_schema_version: which schema version was live
    - effective_load: the correct load metric per active schema
    - http_status_label: true status derived from HTTP code (NOT json_status)
    """
    logs_path = logs_path or settings.SYSTEM_LOGS_PATH
    schema_path = schema_path or settings.SCHEMA_CONFIG_PATH

    df = pd.read_csv(logs_path)
    schema_df = pd.read_csv(schema_path)

    # Normalise column names
    df.rename(columns={"L_V1": "l_v1"}, inplace=True)

    # Resolve schema version per log
    df["active_schema_version"] = df["log_id"].apply(
        lambda lid: 2 if lid >= settings.SCHEMA_ROTATION_LOG_ID else 1
    )
    df["effective_load"] = df.apply(
        lambda row: row["l_v1"] if row["active_schema_version"] == 2 else row["load_val"],
        axis=1,
    )

    # True status from HTTP, not the lying json_status
    def http_label(code: int) -> str:
        if code == 200:
            return "HEALTHY"
        elif code == 206:
            return "PARTIAL"
        elif code == 429:
            return "THROTTLED"
        elif code >= 500:
            return "CRITICAL"
        return "UNKNOWN"

    df["http_status_label"] = df["http_response_code"].apply(http_label)

    logger.info(
        "Loaded %d log entries. HTTP status dist: %s",
        len(df),
        df["http_status_label"].value_counts().to_dict(),
    )
    return df


# ─── Bulk DB Seed ─────────────────────────────────────────────────────────────

async def seed_nodes(session: AsyncSession, nodes_df: pd.DataFrame) -> int:
    """Insert all nodes. Skips duplicates via ON CONFLICT DO NOTHING."""
    records = nodes_df[["node_uuid", "user_agent", "serial_number", "is_infected"]].to_dict(
        orient="records"
    )
    stmt = pg_insert(Node).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=["node_uuid"])
    result = await session.execute(stmt)
    await session.commit()
    count = result.rowcount
    logger.info("Seeded %d new nodes", count)
    return count


async def seed_logs(session: AsyncSession, logs_df: pd.DataFrame, batch_size: int = 1000) -> int:
    """Bulk insert system logs in batches."""
    cols = ["log_id", "node_id", "json_status", "http_response_code",
            "response_time_ms", "load_val", "l_v1"]

    # Rename to match ORM column names
    insert_df = logs_df[cols].copy()
    total = 0

    for i in range(0, len(insert_df), batch_size):
        batch = insert_df.iloc[i : i + batch_size].to_dict(orient="records")
        stmt = pg_insert(SystemLog).values(batch)
        stmt = stmt.on_conflict_do_nothing(index_elements=["log_id"])
        result = await session.execute(stmt)
        await session.commit()
        total += result.rowcount

    logger.info("Seeded %d new log entries", total)
    return total


async def seed_schema_config(session: AsyncSession) -> None:
    """Insert schema_config rows."""
    schema_path = settings.SCHEMA_CONFIG_PATH
    df = pd.read_csv(schema_path)
    records = df.to_dict(orient="records")
    stmt = pg_insert(SchemaConfig).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=["version"])
    await session.execute(stmt)
    await session.commit()
    logger.info("Schema config seeded (%d versions)", len(records))
