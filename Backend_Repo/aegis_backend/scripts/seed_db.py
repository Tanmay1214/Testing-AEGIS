"""
scripts/seed_db.py
Seed the PostgreSQL database from the three CSV intelligence assets.
Run AFTER docker-compose up -d and BEFORE starting the server:
    python scripts/seed_db.py
"""
import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal, create_all_tables
from app.services.ingestion import (
    load_node_registry,
    load_system_logs,
    seed_nodes,
    seed_logs,
    seed_schema_config,
)
from app.ml.detector import (
    train_isolation_forest,
    score_log_entry,
    build_iso_features,
)
from app.models.orm import AnomalyRecord
from app.core.config import get_settings
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("aegis.seed")
settings = get_settings()


async def seed_anomaly_records(session, logs_df):
    """Run IsolationForest on all historical logs and persist anomaly records."""
    logger.info("Loading trained models for anomaly labelling...")
    try:
        bundle = joblib.load("data/models/anomaly_detector.joblib")
        iso = bundle["iso"]
        scaler = bundle["scaler"]
    except FileNotFoundError:
        logger.warning("Models not found — skipping anomaly seeding. Run train_model.py first.")
        return

    from sklearn.preprocessing import StandardScaler
    import numpy as np

    X = build_iso_features(logs_df)
    X_scaled = scaler.transform(X)
    scores = iso.decision_function(X_scaled)

    anomaly_threshold = settings.ANOMALY_THRESHOLD
    anomaly_mask = scores < anomaly_threshold
    anomaly_logs = logs_df[anomaly_mask].copy()
    anomaly_logs["anomaly_score"] = scores[anomaly_mask]

    logger.info("Found %d anomalous logs to persist...", len(anomaly_logs))

    records = [
        {
            "node_id": int(row["node_id"]),
            "log_id": int(row["log_id"]),
            "anomaly_score": float(row["anomaly_score"]),
            "detector": "IsolationForest",
        }
        for _, row in anomaly_logs.iterrows()
    ]

    BATCH = 500
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    for i in range(0, len(records), BATCH):
        batch = records[i : i + BATCH]
        stmt = pg_insert(AnomalyRecord).values(batch)
        stmt = stmt.on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()

    logger.info("Anomaly records seeded: %d entries", len(records))


async def main():
    logger.info("═" * 60)
    logger.info("  AEGIS Database Seed")
    logger.info("═" * 60)

    await create_all_tables()

    logger.info("Loading CSVs...")
    nodes_df = load_node_registry()
    logs_df = load_system_logs()

    async with AsyncSessionLocal() as session:
        logger.info("Seeding schema config...")
        await seed_schema_config(session)

        logger.info("Seeding nodes (%d rows)...", len(nodes_df))
        n = await seed_nodes(session, nodes_df)
        logger.info("  → %d new nodes inserted", n)

        logger.info("Seeding system logs (%d rows)...", len(logs_df))
        n = await seed_logs(session, logs_df)
        logger.info("  → %d new log entries inserted", n)

        logger.info("Seeding anomaly records...")
        await seed_anomaly_records(session, logs_df)

    logger.info("\n✓ Database seeded. You can now start the server.")


if __name__ == "__main__":
    asyncio.run(main())
