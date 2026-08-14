# Third
Practicing Python with microservices and much more

Imagine distributed, real-time energy management platform designed to monitor microgrids, forecast power demand, execute algorithmic energy trading, and optimize power distribution using quantum algorithms.

Structure:

[ External IoT / Weather / Market APIs ]
                 │
                 ▼  (Stage 1: Async Polling Engine & Circuit Breakers)
     ┌───────────────────────┐
     │ FastAPI Ingest Engine │
     └───────────┬───────────┘
                 │
                 ▼  (Stage 2: Async Events & Microservices)
       [ RabbitMQ / Redis ]
       /        │         \
      ▼         ▼          ▼
 ┌────────┐ ┌────────┐ ┌───────────────┐      ┌─────────────────────────┐
 │ Telemetry│ │ Market │ │ Alert/Auth    │ ◄───┤ React/TypeScript UI     │
 │ Domain │ │ Domain │ │ Domain        │      │ (Live Alerts & RBAC)    │
 └────────┘ └────────┘ └───────┬───────┘      └─────────────────────────┘
                               │
                               ▼  (Stage 3: Reliability & Observability)
                    [ Logs / Metrics / Probes ]
                               │
                               ▼  (Stage 4: Advanced Systems)
              ┌─────────────────┴─────────────────┐
              │ NumPy Matrix Math                 │
              │ FastMCP Agent Tools               │
              │ IBM Qiskit Quantum QAOA Solver    │
              └───────────────────────────────────┘

## How to run (Stage 1)

Prerequisites: [uv](https://docs.astral.sh/uv/) installed.

```bash
# 1. Install dependencies (creates .venv, pins Python 3.12)
uv sync

# 2. Create the SQLite schema
uv run alembic upgrade head

# 3. Terminal 1 — start the mock third-party APIs (port 9000)
uv run uvicorn app.mock_server.main:app --port 9000

# 4. Terminal 2 — start the ingest engine (pick a free port; 8000 is often taken)
uv run uvicorn app.main:app --port 8001
```

Then, in another terminal:

```bash
# Liveness check
curl 127.0.0.1:8001/health

# Recent readings per source (iot | weather | market)
curl 127.0.0.1:8001/readings/iot

# Circuit breaker state per source
curl 127.0.0.1:8001/status

# Simulate an outage in the mock source and watch the breaker trip
curl -X POST 127.0.0.1:9000/_control/iot/fail    # /iot now returns 503
curl 127.0.0.1:8001/status                       # iot -> "open"
curl -X POST 127.0.0.1:9000/_control/iot/recover # iot recovers, breaker half-opens then closes
```

Notes:

- The source list, polling intervals, and breaker/retry thresholds live in `config.yaml`.
  To swap a source for a real API later, just change its `url` and set `mock: false`.
- To point at a different config or database, set `THIRD_CONFIG_PATH` / `THIRD_DATABASE_URL`
  environment variables.
- Tests: `uv run pytest`
