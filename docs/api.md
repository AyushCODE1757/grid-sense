# API Contracts

## Channel: traffic-telemetry (Edge AI -> Backend)

Publish interval: every 1 second

```json
{
  "lane": "North",
  "count": 12,
  "density": 72.5,
  "ambulance": false,
  "ts": 1712345678
}
```

Fields:
- `lane`: `North|South|East|West`
- `count`: integer `0-50`
- `density`: float `0-100`
- `ambulance`: boolean
- `ts`: unix timestamp

## Signal payload (Backend -> UI via SSE and Redis signal-commands)

```json
{
  "type": "SIGNAL_UPDATE",
  "intersection": "INT-001",
  "lights": {
    "North": "GREEN",
    "South": "RED",
    "East": "RED",
    "West": "RED"
  },
  "densities": {
    "North": 72.5,
    "South": 20.1,
    "East": 12.0,
    "West": 55.2
  },
  "active_emergency": false,
  "ts": 1712345680,
  "cycle_count": 8,
  "avg_wait_seconds": 17.6,
  "last_event": "Scheduled switch to East"
}
```

## REST Endpoints

- `GET /health`
- `GET /state`
- `GET /stream` (SSE)
- `POST /emergency`

Emergency request payload:

```json
{
  "lane": "North",
  "duration_seconds": 30
}
```
