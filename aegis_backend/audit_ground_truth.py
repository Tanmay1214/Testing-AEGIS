import pandas as pd
import joblib
import numpy as np
import os

# Paths
BASE_DIR = r"c:\Users\tanma\OneDrive\เอกสาร\Hackathon\Backend_Repo\aegis_backend"
LOGS_PATH = os.path.join(BASE_DIR, "data", "system_logs.csv")
REGISTRY_PATH = os.path.join(BASE_DIR, "data", "node_registry.csv")
MODEL_PATH = os.path.join(BASE_DIR, "data", "models", "anomaly_detector.joblib")

def run_audit():
    # 1. Load Ground Truth
    registry = pd.read_csv(REGISTRY_PATH)
    registry.columns = [c.strip().lower() for c in registry.columns]
    infected_nodes = set(registry[registry['is_infected'] == True]['node_uuid'])
    print(f"[+] Ground Truth: {len(infected_nodes)} infected nodes in registry.")

    # 2. Load Logs
    logs = pd.read_csv(LOGS_PATH)
    
    # 3. Load ML Model
    model_bundle = joblib.load(MODEL_PATH)
    iso = model_bundle['iso']
    scaler = model_bundle['scaler']
    
    # 4. Process Windows
    # V1: 0 -> 5000 (Uses load_val)
    # V2: 5000 -> 10000 (Uses L_V1)
    
    v1_logs = logs[logs['log_id'] < 5000].copy()
    v2_logs = logs[(logs['log_id'] >= 5000) & (logs['log_id'] <= 10001)].copy()
    
    def get_features(df, load_col):
        # Must match detector.py inference logic exactly
        features = []
        for _, row in df.iterrows():
            rt = row['response_time_ms']
            rtc = row['http_response_code']
            load = row[load_col] if pd.notna(row[load_col]) else 0.3
            features.append([
                rt,
                rtc,
                load,
                int(rtc == 429),
                int(rtc == 206)
            ])
        return np.array(features)

    print("[*] Processing V1 Anomaly Detection...")
    X1 = get_features(v1_logs, 'load_val')
    X1_scaled = scaler.transform(X1)
    v1_scores = iso.decision_function(X1_scaled)
    v1_logs['is_anomaly'] = v1_scores < 0
    
    print("[*] Processing V2 Anomaly Detection...")
    X2 = get_features(v2_logs, 'L_V1')
    X2_scaled = scaler.transform(X2)
    v2_scores = iso.decision_function(X2_scaled)
    v2_logs['is_anomaly'] = v2_scores < 0
    
    # 5. Extract Unique Node IDs
    v1_anomalous_nodes = set(v1_logs[v1_logs['is_anomaly'] == True]['node_id'])
    v2_anomalous_nodes = set(v2_logs[v2_logs['is_anomaly'] == True]['node_id'])
    
    print(f"\n[ RESULTS: V1 (0-5000) ]")
    print(f"  - Total Unique Anomalous Nodes Found: {len(v1_anomalous_nodes)}")
    v1_correct = v1_anomalous_nodes.intersection(infected_nodes)
    print(f"  - Intersection with Ground Truth (Correct Hits): {len(v1_correct)}")
    
    print(f"\n[ RESULTS: V2 (5000-10000) ]")
    print(f"  - Total Unique Anomalous Nodes Found: {len(v2_anomalous_nodes)}")
    v2_correct = v2_anomalous_nodes.intersection(infected_nodes)
    print(f"  - Intersection with Ground Truth (Correct Hits): {len(v2_correct)}")
    
    v2_missing = infected_nodes.difference(v2_anomalous_nodes)
    print(f"  - Missing Infected Nodes in V2: {list(v2_missing)}")
    
    # Combined unique detected nodes
    all_detected = v1_anomalous_nodes.union(v2_anomalous_nodes)
    all_correct = all_detected.intersection(infected_nodes)
    print(f"\n[ TOTAL SUMMARY (0-10000) ]")
    print(f"  - Global Unique Anomalous Nodes Detected: {len(all_detected)}")
    print(f"  - Global Ground Truth Coverage: {len(all_correct)} / {len(infected_nodes)} ({len(all_correct)/len(infected_nodes)*100:.1f}%)")

if __name__ == "__main__":
    run_audit()