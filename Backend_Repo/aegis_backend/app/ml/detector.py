"""
app/ml/detector.py
ML Detection Layer — trains IsolationForest (unsupervised anomaly detection)
and XGBoost (supervised, using is_infected labels from node_registry).

Features used:
  - response_time_ms  (sleeper malware causes abnormal latency)
  - http_response_code (429 = DDoS indicator, not normal ops)
  - effective_load     (schema-resolved load metric; NaN-filled)

IsolationForest: no labels needed, detects outliers in telemetry stream.
XGBoost:         trained on node-level aggregates against is_infected label.
"""
import logging
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier

from app.core.config import get_settings

logger = logging.getLogger("aegis.ml")
settings = get_settings()

# ─── Feature Engineering ─────────────────────────────────────────────────────

ISO_FEATURES = ["response_time_ms", "http_response_code", "effective_load"]
XGB_FEATURES = [
    "avg_response_time_ms", "max_response_time_ms", "p95_response_time_ms",
    "throttled_ratio", "partial_ratio", "avg_load",
]


def build_iso_features(logs_df: pd.DataFrame) -> pd.DataFrame:
    """Per-log feature matrix for IsolationForest."""
    df = logs_df[ISO_FEATURES].copy()
    df["effective_load"] = df["effective_load"].fillna(df["effective_load"].median())
    # One-hot encode HTTP code as a numeric signal
    df["is_throttled"] = (logs_df["http_response_code"] == 429).astype(int)
    df["is_partial"] = (logs_df["http_response_code"] == 206).astype(int)
    return df


def build_node_features(logs_df: pd.DataFrame, nodes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate log-level features to node level for XGBoost.
    This surfaces nodes whose aggregate behaviour matches infected patterns.
    """
    agg = logs_df.groupby("node_id").agg(
        avg_response_time_ms=("response_time_ms", "mean"),
        max_response_time_ms=("response_time_ms", "max"),
        p95_response_time_ms=("response_time_ms", lambda x: np.percentile(x, 95)),
        throttled_ratio=("http_response_code", lambda x: (x == 429).mean()),
        partial_ratio=("http_response_code", lambda x: (x == 206).mean()),
        avg_load=("effective_load", lambda x: x.fillna(x.median()).mean()),
        log_count=("log_id", "count"),
    ).reset_index()

    merged = agg.merge(
        nodes_df[["node_uuid", "is_infected"]],
        left_on="node_id",
        right_on="node_uuid",
        how="inner",
    )
    return merged


# ─── Model Training ──────────────────────────────────────────────────────────

def train_isolation_forest(logs_df: pd.DataFrame) -> tuple[IsolationForest, StandardScaler]:
    """
    Train IsolationForest on raw log telemetry.
    Contamination is set to the observed ~8% infection rate.
    """
    logger.info("Training IsolationForest on %d log entries...", len(logs_df))
    X = build_iso_features(logs_df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        n_estimators=200,
        contamination=settings.ISOLATION_FOREST_CONTAMINATION,
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_scaled)

    scores = iso.decision_function(X_scaled)
    predictions = iso.predict(X_scaled)
    anomaly_count = (predictions == -1).sum()
    logger.info(
        "IsolationForest trained. Flagged %d / %d logs as anomalies (%.1f%%)",
        anomaly_count, len(logs_df), 100 * anomaly_count / len(logs_df),
    )
    return iso, scaler


def train_xgboost(logs_df: pd.DataFrame, nodes_df: pd.DataFrame) -> XGBClassifier:
    """
    Train XGBoost classifier on node-level aggregated features
    against the is_infected ground-truth label from node_registry.
    """
    logger.info("Building node-level features for XGBoost...")
    node_df = build_node_features(logs_df, nodes_df)

    X = node_df[XGB_FEATURES]
    y = node_df["is_infected"].astype(int)

    pos = y.sum()
    neg = len(y) - pos
    scale_pos_weight = neg / pos if pos > 0 else 1.0

    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,  # handle class imbalance
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    xgb.fit(X, y)

    preds = xgb.predict(X)
    probas = xgb.predict_proba(X)[:, 1]
    auc = roc_auc_score(y, probas)

    logger.info("XGBoost trained. AUC=%.4f", auc)
    logger.info("\n%s", classification_report(y, preds, target_names=["Clean", "Infected"]))
    return xgb


# ─── Save / Load ─────────────────────────────────────────────────────────────

def save_models(iso: IsolationForest, scaler: StandardScaler, xgb: XGBClassifier) -> None:
    model_dir = Path(settings.MODEL_PATH).parent
    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump({"iso": iso, "scaler": scaler}, model_dir / "anomaly_detector.joblib")
    joblib.dump(xgb, model_dir / "xgb_classifier.joblib")
    logger.info("Models saved to %s", model_dir)


def load_models() -> dict:
    """
    Load trained models. Returns dict with keys: iso, scaler, xgb.
    Call once at startup; store result in app.state.
    """
    model_dir = Path(settings.MODEL_PATH).parent
    iso_path = model_dir / "anomaly_detector.joblib"
    xgb_path = model_dir / "xgb_classifier.joblib"

    if not iso_path.exists() or not xgb_path.exists():
        raise FileNotFoundError(
            f"Models not found at {model_dir}. Run `python scripts/train_model.py` first."
        )

    iso_bundle = joblib.load(iso_path)
    xgb = joblib.load(xgb_path)
    logger.info("Models loaded from %s", model_dir)
    return {"iso": iso_bundle["iso"], "scaler": iso_bundle["scaler"], "xgb": xgb}


# ─── Inference ────────────────────────────────────────────────────────────────

def score_log_entry(
    models: dict,
    response_time_ms: int,
    http_response_code: int,
    effective_load: float | None,
) -> tuple[bool, float]:
    """
    Score a single incoming log entry with IsolationForest.
    Returns (is_anomaly: bool, anomaly_score: float).
    Lower score = more anomalous (IsolationForest convention).
    """
    load = effective_load if effective_load is not None else 0.3  # median fallback
    features = np.array([[
        response_time_ms,
        http_response_code,
        load,
        int(http_response_code == 429),
        int(http_response_code == 206),
    ]])

    scaler: StandardScaler = models["scaler"]
    iso: IsolationForest = models["iso"]

    X_scaled = scaler.transform(features)
    score = float(iso.decision_function(X_scaled)[0])
    is_anomaly = score < settings.ANOMALY_THRESHOLD
    return is_anomaly, score


def score_log_batch(
    models: dict,
    logs: list,
    threshold: float,
) -> list[tuple[bool, float]]:
    """
    Vectorized scoring for a batch of log entries.
    """
    if not logs:
        return []
        
    features = np.array([
        [
            l.response_time_ms,
            l.http_response_code,
            l.load_val if l.load_val is not None else (l.l_v1 if l.l_v1 is not None else 0.3),
            int(l.http_response_code == 429),
            int(l.http_response_code == 206),
        ]
        for l in logs
    ])

    scaler: StandardScaler = models["scaler"]
    iso: IsolationForest = models["iso"]

    X_scaled = scaler.transform(features)
    scores = iso.decision_function(X_scaled)
    
    return [
        (float(score) < threshold, float(score))
        for score in scores
    ]


def score_node_batch(models: dict, node_features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Score a DataFrame of node-level aggregated features with XGBoost.
    Adds 'xgb_infected_prob' and 'xgb_predicted_infected' columns.
    """
    xgb: XGBClassifier = models["xgb"]
    X = node_features_df[XGB_FEATURES].fillna(0)
    probs = xgb.predict_proba(X)[:, 1]
    preds = (probs >= 0.5).astype(bool)
    result = node_features_df.copy()
    result["xgb_infected_prob"] = probs
    result["xgb_predicted_infected"] = preds
    return result
