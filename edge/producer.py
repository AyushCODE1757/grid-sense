import argparse
import json
import os
import random
import time
from dataclasses import dataclass

import redis

LANES = ["North", "South", "East", "West"]
CHANNEL = "traffic-telemetry"


@dataclass
class LaneSignal:
    density: float = 10.0
    trend: float = 1.0


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def run_simulator(r: redis.Redis, interval_seconds: float, ambulance_every: int) -> None:
    lane_state = {lane: LaneSignal(random.uniform(8, 35), random.choice([-2, -1, 1, 2])) for lane in LANES}
    tick = 0

    while True:
        tick += 1
        emergency_lane = random.choice(LANES) if ambulance_every > 0 and tick % ambulance_every == 0 else None

        for lane in LANES:
            signal = lane_state[lane]
            if random.random() < 0.15:
                signal.trend *= -1
            noise = random.uniform(-4, 4)
            signal.density = clamp(signal.density + signal.trend + noise, 0.0, 100.0)
            count = int((signal.density / 100.0) * 50)

            payload = {
                "lane": lane,
                "count": count,
                "density": round(signal.density, 1),
                "ambulance": lane == emergency_lane,
                "ts": int(time.time()),
            }
            r.publish(CHANNEL, json.dumps(payload))

        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge AI telemetry producer (MVP simulator)")
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379"))
    parser.add_argument("--interval", type=float, default=float(os.getenv("PUBLISH_INTERVAL", "1")))
    parser.add_argument("--ambulance-every", type=int, default=int(os.getenv("AMBULANCE_EVERY", "45")))
    args = parser.parse_args()

    r = redis.Redis.from_url(args.redis_url, decode_responses=True)
    r.ping()
    run_simulator(r, args.interval, args.ambulance_every)


if __name__ == "__main__":
    main()
