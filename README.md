# AEGIS Cyber Infrastructure Defense 🛡️🛰️

**Team:** Code-Blooded  
**Mission:** To protect Nexus City using a high-performance, autonomous, cloud-native forensic intelligence platform.

AEGIS (Autonomous Experimental Grid Intelligence System) is a complete full-stack cybersecurity dashboard engineered for real-time anomaly detection, node health monitoring, and automated forensic ingestion. Built for the hackathon, AEGIS simulates a 24/7 telemetry data stream, analyzes it using machine learning models, and visualizes network health through an immersive, cyberpunk-themed web dashboard.

---

## 🌟 Hackathon Highlights & Features

1. **Zero-Cost Autonomous Telemetry Pulse** 🌀  
   An in-process background worker runs silently alongside the FastAPI server, pulling forensic data from local manifests and pushing telemetry into the cloud database at ~25 packets/sec—simulating live traffic 24/7 without requiring external paid workers.
2. **Machine Learning "Brain"** 🧠  
   Integrated `IsolationForest` (unsupervised) and `XGBoost` (supervised) models scan all incoming logs in real-time, assigning anomaly scores and generating an Alert Ticker for malicious activity.
3. **Immersive Cyberpunk Dashboard** 🌃  
   A pure Vanilla HTML/JS/CSS frontend featuring a CRT scanline overlay, dynamic network heatmaps, smooth staggered layout animations, and typing terminal effects.
4. **Intelligent Schema Rotation** 🔄  
   The ingestion engine seamlessly handles dynamic data-model shifts, automatically determining whether incoming packets match the `V1` or `V2` forensic schema.
5. **Cloud-Native Resilience** ⚡  
   Engineered for managed PostgreSQL with `asyncpg`, featuring a custom 5-attempt retry loop and automatic sequence calibration to ensure flawless startups on cloud infrastructure.

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy (Async), Uvicorn, Pandas, Scikit-Learn, XGBoost.
- **Frontend:** Vanilla HTML5, CSS3, JavaScript (Fetch API).
- **Database:** PostgreSQL (Render Managed Provider).
- **Cache / Message Broker:** Redis (Upstash).

---

## 🚀 Manual Deployment & Setup Guide

This guide walks you through deploying the AEGIS system manually, from setting up the required cloud resources to spinning up the terminal.

### Prerequisites
- Python 3.10+
- Git
- Accounts on **Render.com** (PostgreSQL hosting) and **Upstash.com** (Redis hosting).

---

### Step 1: Provision Cloud Resources ☁️
1. **Database:** Head to Render and deploy a free **PostgreSQL** instance. Choose `Oregon` (US-West) as the region for optimal latency. Note your **External Database URL**.
2. **Redis:** Head to Upstash and deploy a free **Redis** database. Note the connection URL (starting with `rediss://`).

---

### Step 2: Clone & Configure Environment 🔐

1. Clone the repository:
   ```bash
   git clone https://github.com/Tanmay1214/Code-Blooded_AEGIS-Cyber-Infrastructure-Defense.git
   cd Code-Blooded_AEGIS-Cyber-Infrastructure-Defense
   ```

2. Create a `.env` file inside the `aegis_backend/` folder based on `.env.example`:
   ```bash
   cd aegis_backend
   # Create a `.env` file and insert the following:
   ```

   **Example `.env` content:**
   ```env
   # Your Render External PostgreSQL URL
   DATABASE_URL="postgresql://user:pass@render-hostname.com/db_name"
   
   # Your Upstash Redis URL
   REDIS_URL="rediss://default:password@upstash-hostname.io:6379"
   
   APP_NAME="AEGIS Defense System [LOCAL]"
   APP_VERSION="1.0.0"
   DEBUG=true
   ANOMALY_THRESHOLD=0.0
   ISOLATION_FOREST_CONTAMINATION=0.08
   
   NODE_REGISTRY_PATH="data/node_registry.csv"
   SYSTEM_LOGS_PATH="data/system_logs.csv"
   SCHEMA_CONFIG_PATH="data/schema_config.csv"
   ```

---

### Step 3: Initialize the Database (Surgical Reset & Seed) 🧹
For a 100% clean mission, wipe the tables and rebuild the data registry from scratch.

*Ensure you are actively inside the `aegis_backend` directory.*
```bash
# 1. Setup a python virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Wipe any existing data (Optional/For clean start)
python reset_db.py

# 4. Seed the Database with initial nodes and 10,000 logs
python scripts/seed_db.py

# 5. Calibrate the Sequences to fix auto-incrementing IDs
python scripts/calibrate_sequences.py
```

---

### Step 4: Engage the Mission Backend 🛰️
Start the FastAPI server. This will also trigger the self-sustaining 24/7 **Autonomous Pulse**.

```bash
uvicorn main:app --reload
```
*Your backend intelligence is now online at `http://localhost:8000`. Watch your terminal as the pulses flow automatically!*

---

### Step 5: Launch the Cyberpunk Dashboard 💻
You can launch the frontend using any basic HTTP server from the root of the project.

Open a new terminal session, ensuring you are in the **Root Project Folder**:
```bash
# Launch a built-in Python Web Server
python -m http.server 8080
```

1. Navigate to: `http://localhost:8080`
2. You should now see the Cyberpunk AEGIS Terminal, updating autonomously with real-time analytics mapped directly from your cloud database!

---

## ☁️ Quick Cloud Re-Deployment (Optional)
If you wish to deploy this entire architecture natively to **Render**, the project contains a definitive `render.yaml` Blueprint.
1. Connect this GitHub repository to Render using the **"New Blueprint"** option.
2. Provide your existing **Redis URL** in the environment prompts.
3. Once the build finishes, manually update the `DATABASE_URL` environment variable within the Render Dashboard to point to your new External Postgres endpoint.

---
**Mission Complete. Nexus City is Secured.** 🏆
