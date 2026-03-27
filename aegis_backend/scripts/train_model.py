"""
scripts/train_model.py
Train IsolationForest + XGBoost on the AEGIS datasets and save to disk.
Run this ONCE before starting the server:
    python scripts/train_model.py
"""
import sys
import logging
from pathlib import Path

# Make sure imports resolve from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from app.services.ingestion import load_node_registry, load_system_logs
from app.ml.detector import (
    train_isolation_forest,
    train_xgboost,
    save_models,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("aegis.train")


def main():
    logger.info("═" * 60)
    logger.info("  AEGIS ML Training Pipeline")
    logger.info("═" * 60)

    # ── Load data ────────────────────────────────────────────
    logger.info("Loading datasets...")
    nodes_df = load_node_registry()
    logs_df = load_system_logs()

    logger.info(
        "Dataset summary — Nodes: %d (%d infected) | Logs: %d",
        len(nodes_df),
        nodes_df["is_infected"].sum(),
        len(logs_df),
    )
    logger.info(
        "HTTP distribution: %s",
        logs_df["http_response_code"].value_counts().to_dict(),
    )
    logger.info(
        "True status distribution: %s",
        logs_df["http_status_label"].value_counts().to_dict(),
    )

    # ── IsolationForest ──────────────────────────────────────
    logger.info("\n[1/2] Training IsolationForest (unsupervised anomaly detection)...")
    iso, scaler = train_isolation_forest(logs_df)

    # ── XGBoost ──────────────────────────────────────────────
    logger.info("\n[2/2] Training XGBoost (supervised infection classifier)...")
    xgb = train_xgboost(logs_df, nodes_df)

    # ── Save ─────────────────────────────────────────────────
    logger.info("\nSaving models...")
    save_models(iso, scaler, xgb)

    logger.info("\n✓ Training complete. Models saved. You can now start the server.")
    logger.info("  uvicorn main:app --reload --port 8000")


if __name__ == "__main__":
    main()