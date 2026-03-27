# AEGIS Backend — Cyber-Infrastructure Defense System

## Architecture

```
Data Sources  →  Ingestion Layer  →  Processing Layer  →  ML Detection  →  Storage  →  API Layer
(CSVs/Stream)    (FastAPI+Kafka)      (Pandas/Polars)     (IsoForest/XGB)  (PG+Redis)  (FastAPI)
```

## Project Structure

```
aegis_backend/
├── app/
│   ├── api/           # FastAPI route handlers
│   ├── core/          # Config, DB, Redis, startup
│   ├── models/        # SQLAlchemy ORM models
│   ├── services/      # Business logic (ingestion, processing)
│   └── ml/            # ML detection layer
├── data/              # Raw CSVs (node_registry, system_logs, schema_config)
├── scripts/           # Train & seed scripts
├── tests/             # pytest test suite
├── main.py
├── requirements.txt
└── docker-compose.yml
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start infrastructure
docker-compose up -d

# 3. Train the ML model
python scripts/train_model.py

# 4. Seed the database
python scripts/seed_db.py

# 5. Start the API server
uvicorn main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/nodes` | All nodes with decoded serial numbers |
| GET | `/api/nodes/{node_id}/status` | Node forensic status |
| GET | `/api/city-map` | All nodes with HTTP-based status codes |
| GET | `/api/heatmap` | Response time heatmap per node |
| GET | `/api/schema-console` | Active schema version (cookie-based) |
| GET | `/api/anomalies` | ML-detected anomalous nodes |
| POST | `/api/ingest` | Ingest a new log entry |
| GET | `/api/health` | System health check |

## Key Design Decisions

- **Status Truth**: HTTP response codes (not JSON `OPERATIONAL` label) determine node health
- **Schema Rotation**: Active column switches at log_id=5000 (`load_val` → `L_V1`)
- **Serial Numbers**: Base64 decoded from `user_agent` field in node_registry
- **Anomaly Detection**: IsolationForest on response_time_ms + http_response_code + load metric
- **Caching**: Redis caches city-map and heatmap for 30s (fast dashboard refresh)
