import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError

from .models import EmergencyRequest, SignalUpdate, TelemetryEvent
from .state import EVALUATION_INTERVAL_SECONDS, IntersectionState

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
TELEMETRY_CHANNEL = "traffic-telemetry"
SIGNAL_CHANNEL = "signal-commands"

state = IntersectionState()
redis_client: Redis | None = None
subscribers: list[asyncio.Queue[str]] = []


def _now_ts() -> int:
    return int(time.time())


async def broadcast(update: SignalUpdate) -> None:
    payload = update.model_dump_json()

    if redis_client is not None:
        try:
            await redis_client.publish(SIGNAL_CHANNEL, payload)
        except RedisError:
            pass

    stale: list[asyncio.Queue[str]] = []
    for q in subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            stale.append(q)
    for q in stale:
        if q in subscribers:
            subscribers.remove(q)


async def emit_signal(event_type: str) -> None:
    update = SignalUpdate(
        type=event_type,
        lights=state.lights,
        densities=state.densities,
        active_emergency=state.emergency_active,
        ts=_now_ts(),
        cycle_count=state.cycle_count,
        avg_wait_seconds=state.avg_wait_seconds(),
        last_event=state.last_event,
    )
    await broadcast(update)


async def telemetry_consumer() -> None:
    if redis_client is None:
        return

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(TELEMETRY_CHANNEL)
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if not message:
            await asyncio.sleep(0.05)
            continue

        try:
            payload = json.loads(message["data"])
            telemetry = TelemetryEvent.model_validate(payload)
        except Exception:
            continue

        state.densities[telemetry.lane] = telemetry.density
        state.counts[telemetry.lane] = telemetry.count

        if telemetry.ambulance and not state.emergency_active:
            state.trigger_emergency(telemetry.lane, duration_seconds=30)
            await emit_signal("EMERGENCY_OVERRIDE")
        else:
            await emit_signal("DENSITY_UPDATE")


async def scheduler_loop() -> None:
    while True:
        changed = state.tick()
        if changed:
            await emit_signal("SIGNAL_UPDATE")
        await asyncio.sleep(EVALUATION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global redis_client
    try:
        redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
    except RedisError:
        redis_client = None

    tasks = [asyncio.create_task(scheduler_loop())]
    if redis_client is not None:
        tasks.append(asyncio.create_task(telemetry_consumer()))

    await emit_signal("SIGNAL_UPDATE")
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if redis_client is not None:
            await redis_client.aclose()


app = FastAPI(title="AI Traffic Control Engine", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    redis_ok = False
    if redis_client is not None:
        try:
            redis_ok = bool(await redis_client.ping())
        except RedisError:
            redis_ok = False

    return {
        "status": "ok",
        "redis_connected": redis_ok,
        "ts": _now_ts(),
    }


@app.get("/state")
async def get_state() -> dict:
    snapshot = state.snapshot()
    snapshot["ts"] = _now_ts()
    return snapshot


@app.post("/emergency")
async def emergency(request: EmergencyRequest) -> dict:
    if state.emergency_active:
        raise HTTPException(status_code=409, detail="Emergency override already active")

    state.trigger_emergency(request.lane, request.duration_seconds)
    await emit_signal("EMERGENCY_OVERRIDE")
    return {
        "message": "Emergency override triggered",
        "lane": request.lane,
        "duration_seconds": request.duration_seconds,
        "ts": _now_ts(),
    }


@app.get("/stream")
async def stream() -> StreamingResponse:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    subscribers.append(queue)

    async def event_generator() -> AsyncIterator[str]:
        try:
            # Initial snapshot for instant UI render.
            initial = SignalUpdate(
                type="SIGNAL_UPDATE",
                lights=state.lights,
                densities=state.densities,
                active_emergency=state.emergency_active,
                ts=_now_ts(),
                cycle_count=state.cycle_count,
                avg_wait_seconds=state.avg_wait_seconds(),
                last_event=state.last_event,
            )
            yield f"data: {initial.model_dump_json()}\n\n"
            while True:
                payload = await queue.get()
                yield f"data: {payload}\n\n"
        finally:
            if queue in subscribers:
                subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
