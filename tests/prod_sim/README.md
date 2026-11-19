# EDITH-X Production Simulation & Reliability Test Suite

An enterprise-grade, zero-bias performance, reliability, and security test harness for the EDITH-X gateway.

---

## 1. Architecture Overview
- **Deployment**: Real HTTP socket communication against running API gateway (`http://127.0.0.1:8000`) and Mock LLM (`http://127.0.0.1:8001`).
- **Mock LLM**: Simulates Local Tier lognormal latency (median 400ms, P99 3s) and Cloud Tier (median 1.2s, P99 8s), with 1% 429s, 0.5% 500s, and token audit ledger.
- **Canary Isolation Testing**: Every tenant embeds unique `CANARY-org_XX-xxxxxx` cryptographic signatures in documents. Any cross-tenant data leak is detected automatically by string matching.

---

## 2. Directory Structure
```
tests/prod_sim/
├── RECON.md                  # Honest architectural gap analysis of M1–M14
├── BUGS.md                   # Formal defect log (P0-P2) without touching edith_x/
├── thresholds.yaml           # Pre-committed immutable pass/fail thresholds
├── docker-compose.prod-sim.yml # Production Docker compose definition
├── prometheus.yml            # Prometheus scrape configuration
├── calibrate_ollama.py       # Live model hardware calibration probe
├── system_monitor.py         # 1-second interval CPU/RAM/handle/FD scraper
├── generate_data.py          # Fixed-seed dataset builder (50 tenants, 1,000 users, 25k chunks)
├── locustfile.py             # Multi-persona Locust load generator (5 personas + adversarial)
├── run_prod_sim.py           # Orchestrator running T0 through T8 over real HTTP
├── mock_llm/
│   ├── main.py               # OpenAI-compatible mock LLM with lognormal latency & faults
│   └── Dockerfile            # Container build for mock LLM
├── data/                     # Generated test datasets (tenants, users, queries, canaries, PII)
└── results/                  # Raw execution traces, CSVs, and JSON logs
```

---

## 3. Execution Commands

### Step 1: Generate Realistic Datasets (Fixed Seed 1337)
```powershell
.\.venv\Scripts\python tests/prod_sim/generate_data.py
```

### Step 2: Run Full Automated Production Simulation Suite (T0 to T8)
```powershell
.\.venv\Scripts\python tests/prod_sim/run_prod_sim.py
```

### Step 3: Run Interactive Locust UI (Optional)
```powershell
.\.venv\Scripts\locust -f tests/prod_sim/locustfile.py --host http://127.0.0.1:8000
```
Open browser to: `http://localhost:8089`

### Step 4: Docker Compose Run (In environments with Docker installed)
```bash
docker compose -f tests/prod_sim/docker-compose.prod-sim.yml up --build -d
```
