# Dynamic AI Traffic Flow Optimizer - MVP

This MVP implements the blueprint architecture in 4 layers:

1. `edge/` - telemetry producer (1s interval) with ambulance simulation
2. `backend/` - FastAPI traffic control engine + weighted priority state machine + SSE
3. `frontend/` - Next.js command center dashboard
4. `redis` - pub/sub broker (`traffic-telemetry` and `signal-commands`)

## Quick Start

Prerequisites:
- Docker Desktop with Compose

Run:

```bash
docker compose up --build
```

Open:
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## What Matches the Blueprint

- Event flow: `Edge AI -> Redis -> FastAPI -> SSE -> Next.js`
- Lanes: 4 (`North`, `South`, `East`, `West`)
- Telemetry schema and channels
- Weighted priority scoring (`density*0.6 + wait*0.4`)
- Starvation guard (`wait > 90s`)
- Min/Max green window (15s/60s)
- Emergency override (default 30s)
- SSE stream with reconnect behavior on UI
- Event log (last 20)

## Repo Layout

- `docker-compose.yml`
- `docs/api.md`
- `edge/`
- `backend/`
- `frontend/`

## Notes

- Current `edge/producer.py` is an MVP simulator. Swap this with YOLOv8 + OpenCV inference while keeping the same telemetry payload.
- Backend also publishes `signal-commands` to Redis for compatibility with future multi-client consumers.
