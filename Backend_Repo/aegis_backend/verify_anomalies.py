import sys
import os
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(os.getcwd())))

from app.core.config import get_settings
from app.ml.detector import load_models

settings = get_settings()
CSV_PATH = "data/system_logs.csv"

def verify():
    print(f"--- AEGIS ANOMALY VERIFICATION ---")
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found")
        return

    try:
        models = load_models()
        iso = models["iso"]
        scaler = models["scaler"]
    except Exception as e:
        print(f"Error loading models: {e}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} logs.")

    # Window 1: 0 - 5000 (V1)
    df_v1 = df.iloc[0:5000].copy()
    # Window 2: 5000 - 10000 (V2)
    df_v2 = df.iloc[5000:10000].copy()

    def score_df(window_df, load_col):
        # Feature engineering matching detector.py EXACTLY
        X = pd.DataFrame()
        X["response_time_ms"] = window_df["response_time_ms"]
        X["http_response_code"] = window_df["http_response_code"]
        X["effective_load"] = window_df[load_col].fillna(0.3)
        X["is_throttled"] = (window_df["http_response_code"] == 429).astype(int)
        X["is_partial"] = (window_df["http_response_code"] == 206).astype(int)
        
        # Scikit-learn sometimes wants a DataFrame with names if trained with names
        X_scaled = scaler.transform(X)
        scores = iso.decision_function(X_scaled)
        anomalies = scores < settings.ANOMALY_THRESHOLD
        return anomalies.sum()

    count_v1 = score_df(df_v1, "load_val")
    count_v2 = score_df(df_v2, "L_V1")

    print(f"V1 Anomalies (using load_val): {count_v1}")
    print(f"V2 Anomalies (using L_V1):    {count_v2}")
    
    if count_v1 == 70:
        print("V1 count MATCHES expected 70.")
    else:
        print(f"V1 count MISMATCH (Expected 70, got {count_v1})")

    if count_v2 == 100:
        print("V2 count MATCHES expected 100.")
    else:
        print(f"V2 count MISMATCH (Expected 100, got {count_v2})")

if __name__ == "__main__":
    verify()
