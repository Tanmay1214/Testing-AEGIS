# AEGIS Backend — Cyber-Infrastructure Defense System

> **Project AEGIS** — Identify the "Shadow Controller" infiltrating Nexus City's infrastructure
> by cutting through deceptive telemetry data to expose real attack patterns.
>
> Built by **Code Blooded** — Tanmay, Anvay, Devesh, Aarin @ LNMIIT Jaipur

---

## Architecture

```
Data Sources  →  Ingestion Layer      →  Processing Layer  →  Detection Brain        →  Storage      →  API Layer
(CSVs/Stream)    (FastAPI + Pipeline)     (Pandas/Polars)      (Rules + IsoForest)      (PG + Redis)    (FastAPI)
```

### Detection Stack

```
Raw Telemetry
     │
     ▼
┌─────────────────────────────────────────┐
│           INGESTION PIPELINE            │
│  LogAdapter → Preprocessor → Router    │
│  RegistryAdapter (Base64 decode)        │
│  SchemaAdapter (v1/v2 rotation)         │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│         RULE-BASED DETECTION ENGINE     │
│                                         │
│  Rule 1 → DDoS Detector                 │
│           (429 spikes per node > 5x)    │
│                                         │
│  Rule 2 → Latency Anomaly Detector      │
│           (response_time_ms > 200ms)    │
│                                         │
│  Rule 3 → Status Mismatch Detector      │
│           (OPERATIONAL lie detection)   │
│                                         │
│  Rule 4 → Infected Node Detector        │
│           (registry cross-reference)    │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│         ML DETECTION LAYER              │
│  IsolationForest on:                    │
│  response_time_ms + http_code + load    │
└─────────────────────────────────────────┘
     │
     ▼
  ThreatAlert  (severity + evidence + details)
```

---

## Project Structure

```
aegis_backend/
├── app/
│   ├── api/
│   │   ├── routes.py          # Core FastAPI route handlers
│   │   └── alert_routes.py    # Day 2: Threat alert endpoints (NEW)
│   ├── core/                  # Config, DB, Redis, startup
│   ├── models/
│   │   ├── orm.py             # SQLAlchemy ORM (Node, SystemLog, AnomalyRecord)
│   │   └── schemas.py         # Pydantic response schemas
│   ├── services/
│   │   ├── ingestion.py       # CSV loading + Base64 decoding + schema rotation
│   │   ├── analytics.py       # City map, heatmap, schema console logic
│   │   ├── forensics.py       # Cloned identity detection
│   │   └── detection_engine.py  # Day 2: 4 rule-based detectors (NEW)
│   └── ml/
│       └── detector.py        # IsolationForest inference
├── data/
│   ├── system_logs.csv        # 10,000 telemetry events (schema split at log_id=5000)
│   ├── node_registry.csv      # 500 nodes (70 infected, serials Base64 encoded)
│   └── schema_config.csv      # 2 schema versions (load_val → L_V1)
├── scripts/
│   ├── train_model.py         # Train IsolationForest + save to data/models/
│   └── seed_db.py             # Load CSVs → decode → bulk insert PostgreSQL
├── tests/
│   └── test_detection_engine.py  # pytest suite for all 4 detectors (NEW)
├── main.py
├── requirements.txt
└── docker-compose.yml
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start infrastructure (PostgreSQL + Redis)
docker-compose up -d

# 3. Train the ML model
python scripts/train_model.py

# 4. Seed the database (loads CSVs, decodes serials, runs IsolationForest)
python scripts/seed_db.py

# 5. Start the API server
uvicorn main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health — DB, Redis, ML model status |
| GET | `/api/nodes` | All 500 nodes with decoded serial numbers |
| GET | `/api/nodes/{node_id}/status` | Full forensic status for a single node |
| GET | `/api/city-map` | All nodes colored by TRUE HTTP status (not JSON label) |
| GET | `/api/heatmap` | Response-time heatmap — identifies sleeper malware nodes |
| GET | `/api/schema-console` | Active schema version (cookie-based log_id lookup) |
| GET | `/api/anomalies` | ML-detected anomalous nodes (IsolationForest) |
| POST | `/api/ingest` | Ingest a new log entry + run live ML inference |
| GET | `/api/forensics/cloned-identities` | Nodes sharing the same decoded serial number |

### Threat Detection Endpoints (Day 2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts` | All ThreatAlerts from all 4 rule-based detectors |
| GET | `/api/alerts?severity=CRITICAL` | Filter alerts by severity |
| GET | `/api/alerts?threat_type=DDOS` | Filter alerts by detector type |
| GET | `/api/alerts?node_id=80` | All alerts for a specific node |
| GET | `/api/threat-summary` | Aggregated counts + top 5 offending nodes |
| GET | `/api/infected-nodes` | CRITICAL: known-infected nodes with live traffic |

### Sample `/api/threat-summary` Response

```json
{
  "total_alerts": 312,
  "critical_count": 70,
  "high_count": 89,
  "medium_count": 114,
  "low_count": 39,
  "ddos_nodes": 21,
  "latency_nodes": 187,
  "mismatch_nodes": 104,
  "infected_nodes": 70,
  "top_offenders": [
    { "node_id": 80,  "alert_count": 4 },
    { "node_id": 338, "alert_count": 3 }
  ],
  "alerts": [ "..." ]
}
```

---

## Key Design Decisions

### 1. Status Truth — HTTP over JSON
Every single log entry has `json_status = "OPERATIONAL"` — this is the Shadow Controller's
deception. The pipeline **never trusts json_status**. HTTP response codes are ground truth:

| HTTP Code | Real Meaning |
|-----------|-------------|
| 200 | HEALTHY |
| 206 | PARTIAL — partial content hijack signal |
| 429 | THROTTLED — DDoS indicator |

### 2. Schema Rotation at log_id = 5000
The load metric column rotates mid-stream with no signal in the log data itself:
- **Schema v1** (log_id 0–4999): active column = `load_val`
- **Schema v2** (log_id 5000–9999): active column = `L_V1`

The ingestion layer detects this from `schema_config.csv` and tags every event correctly.

### 3. Serial Number Decoding
Node serial numbers are Base64-encoded and hidden inside the `user_agent` field:
```
user_agent: "AEGIS-Node/2.0 (Linux) U04tOTI4MA=="
                                     └── base64 → "SN-9280"
```
Decoded at ingestion time and stored as `serial_number` in the `nodes` table.

### 4. Two-Layer Detection
- **Rule engine** — deterministic, fast, explainable. Catches known patterns (DDoS, mismatch, infected nodes).
- **IsolationForest** — catches unknown anomalies the rules don't cover. Trained on `response_time_ms`, `http_response_code`, and `effective_load`.

### 5. Caching
Redis caches `/api/city-map` and `/api/heatmap` for 30 seconds to support fast dashboard refresh without hammering PostgreSQL.

---

## Dataset Intelligence

| Dataset | Rows | Key Anomaly |
|---------|------|-------------|
| `system_logs.csv` | 10,000 | `json_status` always OPERATIONAL — lies about 1,441 anomalous events |
| `node_registry.csv` | 500 nodes | 70 infected (14%) — serials hidden in Base64 |
| `schema_config.csv` | 2 versions | Silent column rotation at log_id 5000 |

### Threat Signals Found

| Signal | Count | Detector |
|--------|-------|----------|
| HTTP 429 (DDoS) | 727 events | DDoS Detector |
| HTTP 206 (Partial hijack) | 714 events | Status Mismatch Detector |
| Latency anomalies >200ms | 1,441 events | Latency Detector |
| Status mismatches | 727 nodes | Status Mismatch Detector |
| Known infected nodes active | 70 nodes | Infected Node Detector |

---

## Running Tests

```bash
cd aegis_backend
pip install pytest pytest-asyncio
pytest tests/test_detection_engine.py -v
```

Tests use mock SQLAlchemy sessions — no database or Docker required to run them.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `SCHEMA_ROTATION_LOG_ID` | `5000` | log_id where schema switches v1 → v2 |
| `ANOMALY_THRESHOLD` | `-0.1` | IsolationForest decision boundary |
| `DDOS_THRESHOLD` | `5` | Min 429s per node before DDoS alert fires |
| `LATENCY_THRESHOLD_MS` | `200` | Response time above which latency is anomalous |

---

## Live Demo

Frontend: [aegis-cyber-infrastructure-defense.vercel.app](https://aegis-cyber-infrastructure-defense.vercel.app)
