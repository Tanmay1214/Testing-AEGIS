"""
tests/test_backend.py
Pytest test suite for AEGIS backend.
Tests: ingestion decoding, schema resolution, ML scoring, API contracts.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import base64
import pytest
import pandas as pd
import numpy as np

from app.services.ingestion import decode_serial_number, load_node_registry, load_system_logs
from app.ml.detector import build_iso_features, train_isolation_forest, score_log_entry
from app.core.config import get_settings

settings = get_settings()


# ─── Ingestion / Decoding Tests ───────────────────────────────────────────────

class TestSerialDecoding:
    def test_decode_valid_base64(self):
        encoded = base64.b64encode(b"SN-9280").decode()
        user_agent = f"AEGIS-Node/2.0 (Linux) {encoded}"
        result = decode_serial_number(user_agent)
        assert result == "SN-9280"

    def test_decode_all_nodes(self):
        df = load_node_registry()
        assert "serial_number" in df.columns
        # All serial numbers should start with 'SN-'
        assert df["serial_number"].str.startswith("SN-").all(), \
            "Some serial numbers failed to decode"

    def test_duplicate_serials_detected_as_cloned_identities(self):
        """
        The Shadow Controller clones node identities (same serial, different UUID).
        The system must DETECT these — they are intentional data anomalies per the problem statement.
        """
        df = load_node_registry()
        dupes = df[df.duplicated("serial_number", keep=False)]
        # There are known duplicate serials in the dataset by design
        assert len(dupes) > 0, "Expected cloned identity anomalies in registry — none found"
        # All duplicated serial nodes should be flagged as suspicious (high infected rate)
        infected_rate = dupes["is_infected"].mean()
        all_rate = df["is_infected"].mean()
        assert infected_rate >= all_rate, \
            f"Cloned nodes should have >= avg infection rate: {infected_rate:.2%} vs {all_rate:.2%}"


# ─── Schema Rotation Tests ────────────────────────────────────────────────────

class TestSchemaRotation:
    def test_schema_v1_active_before_5000(self):
        logs_df = load_system_logs()
        v1_logs = logs_df[logs_df["log_id"] < 5000]
        assert (v1_logs["active_schema_version"] == 1).all()

    def test_schema_v2_active_from_5000(self):
        logs_df = load_system_logs()
        v2_logs = logs_df[logs_df["log_id"] >= 5000]
        assert (v2_logs["active_schema_version"] == 2).all()

    def test_effective_load_v1_uses_load_val(self):
        logs_df = load_system_logs()
        v1 = logs_df[logs_df["active_schema_version"] == 1].head(10)
        for _, row in v1.iterrows():
            assert row["effective_load"] == row["load_val"] or \
                (pd.isna(row["effective_load"]) and pd.isna(row["load_val"]))

    def test_effective_load_v2_uses_l_v1(self):
        logs_df = load_system_logs()
        v2 = logs_df[logs_df["active_schema_version"] == 2].head(10)
        for _, row in v2.iterrows():
            assert row["effective_load"] == row["l_v1"] or \
                (pd.isna(row["effective_load"]) and pd.isna(row["l_v1"]))

    def test_no_overlap_in_load_columns(self):
        """v1 logs should have NaN L_V1, v2 logs should have NaN load_val."""
        logs_df = load_system_logs()
        v1_logs = logs_df[logs_df["active_schema_version"] == 1]
        v2_logs = logs_df[logs_df["active_schema_version"] == 2]
        assert v1_logs["l_v1"].isna().all(), "v1 logs should not have L_V1 values"
        assert v2_logs["load_val"].isna().all(), "v2 logs should not have load_val values"


# ─── Status Truth Tests ───────────────────────────────────────────────────────

class TestStatusTruth:
    def test_json_status_always_operational(self):
        """The lie: json_status is always OPERATIONAL."""
        logs_df = load_system_logs()
        assert (logs_df["json_status"] == "OPERATIONAL").all(), \
            "json_status should always be 'OPERATIONAL' (deceptive field)"

    def test_http_codes_reveal_truth(self):
        logs_df = load_system_logs()
        codes = set(logs_df["http_response_code"].unique())
        assert codes == {200, 206, 429}, f"Expected {{200, 206, 429}}, got {codes}"

    def test_http_status_labels(self):
        logs_df = load_system_logs()
        label_map = {"HEALTHY": 200, "PARTIAL": 206, "THROTTLED": 429}
        for label, code in label_map.items():
            subset = logs_df[logs_df["http_response_code"] == code]
            assert (subset["http_status_label"] == label).all(), \
                f"HTTP {code} should map to {label}"


# ─── ML Tests ────────────────────────────────────────────────────────────────

class TestMLDetector:
    @pytest.fixture(scope="class")
    def trained_models(self):
        logs_df = load_system_logs()
        iso, scaler = train_isolation_forest(logs_df)
        return {"iso": iso, "scaler": scaler}

    def test_isolation_forest_trains(self, trained_models):
        assert trained_models["iso"] is not None
        assert trained_models["scaler"] is not None

    def test_anomaly_score_for_normal_log(self, trained_models):
        is_anomaly, score = score_log_entry(
            models=trained_models,
            response_time_ms=120,      # normal
            http_response_code=200,    # healthy
            effective_load=0.3,
        )
        # Normal log should have score above threshold
        assert score > settings.ANOMALY_THRESHOLD, \
            f"Normal log scored {score}, expected > {settings.ANOMALY_THRESHOLD}"

    def test_anomaly_score_for_suspicious_log(self, trained_models):
        is_anomaly, score = score_log_entry(
            models=trained_models,
            response_time_ms=250,      # max observed — very slow
            http_response_code=429,    # DDoS throttled
            effective_load=0.99,       # extreme load
        )
        # Suspicious log should score below normal (lower = more anomalous)
        normal_score = score_log_entry(
            models=trained_models,
            response_time_ms=120,
            http_response_code=200,
            effective_load=0.3,
        )[1]
        assert score < normal_score, \
            f"Suspicious log ({score:.4f}) should score lower than normal ({normal_score:.4f})"

    def test_infected_nodes_have_more_anomalies(self):
        """Infected nodes should produce more anomalous telemetry on average."""
        logs_df = load_system_logs()
        nodes_df = load_node_registry()
        iso, scaler = train_isolation_forest(logs_df)

        X = build_iso_features(logs_df)
        import numpy as np
        X_scaled = scaler.transform(X)
        scores = iso.decision_function(X_scaled)
        logs_df = logs_df.copy()
        logs_df["anomaly_score"] = scores

        merged = logs_df.merge(
            nodes_df[["node_uuid", "is_infected"]],
            left_on="node_id", right_on="node_uuid",
        )

        infected_avg = merged[merged["is_infected"]]["anomaly_score"].mean()
        clean_avg = merged[~merged["is_infected"]]["anomaly_score"].mean()

        assert infected_avg < clean_avg, \
            f"Infected nodes should score lower (more anomalous): {infected_avg:.4f} vs {clean_avg:.4f}"


# ─── Data Integrity Tests ────────────────────────────────────────────────────

class TestDataIntegrity:
    def test_all_log_nodes_exist_in_registry(self):
        logs_df = load_system_logs()
        nodes_df = load_node_registry()
        log_node_ids = set(logs_df["node_id"].unique())
        registry_ids = set(nodes_df["node_uuid"].unique())
        orphans = log_node_ids - registry_ids
        assert len(orphans) == 0, f"Logs reference unknown node IDs: {orphans}"

    def test_log_ids_are_unique(self):
        logs_df = load_system_logs()
        assert logs_df["log_id"].nunique() == len(logs_df), "Duplicate log_ids found"

    def test_response_times_in_range(self):
        logs_df = load_system_logs()
        assert logs_df["response_time_ms"].min() >= 0
        assert logs_df["response_time_ms"].max() <= 10000  # sanity upper bound