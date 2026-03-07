<<<<<<< HEAD
import json
import os
import time
import cv2
import redis
from ultralytics import YOLO

LANES = ["North", "South", "East", "West"]
CHANNEL = "traffic-telemetry"
VEHICLE_CLASSES = {2, 3, 5, 7}  # car, motorcycle, bus, truck

# Rough quadrant split of frame into 4 lanes
def get_lane_for_box(cx, cy, fw, fh):
    if cx < fw / 2 and cy < fh / 2:
        return "North"
    elif cx >= fw / 2 and cy < fh / 2:
        return "East"
    elif cx < fw / 2 and cy >= fh / 2:
        return "South"
    else:
        return "West"

def run(video_path, redis_url, interval):
    headless = os.getenv("HEADLESS_MODE", "false").lower() == "true"
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(video_path)
    
    # Robust Redis connection with retries
    r = None
    for i in range(5):
        try:
            r = redis.Redis.from_url(redis_url, decode_responses=True)
            r.ping()
            print(f"✅ Connected to Redis at {redis_url}")
            break
        except redis.ConnectionError:
            print(f"⚠️ Redis not ready, retrying ({i+1}/5)...")
            time.sleep(2)
    
    if r is None:
        print("❌ Could not connect to Redis. Exiting.")
        return

    print("✅ YOLOv8 loaded. Starting detection...")
    
    frame_idx = 0
    last_publish = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        frame_idx += 1
        if frame_idx % 3 != 0:  # process every 3rd frame
            continue
            
        fh, fw = frame.shape[:2]
        results = model(frame, verbose=False)[0]
        
        lane_counts = {lane: 0 for lane in LANES}
        ambulance_detected = False

        for box in results.boxes:
            cls_id = int(box.cls)
            if cls_id not in VEHICLE_CLASSES:
                continue
            
            # Basic ambulance detection if class is supported (class 1 is 'bicycle' in COCO, 
            # but some models have ambulances. For now, we'll keep it as a placeholder/extendable logic)
            # In a real scenario, we'd use a dedicated model or check specific labels.
            # Using placeholder: if it's class 2 (car) and very large/specific aspect ratio etc.
            # For this exercise, we'll just demonstrate where it goes.
            
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            lane = get_lane_for_box(cx, cy, fw, fh)
            lane_counts[lane] += 1
            
        # Show annotated frame in window if not headless
        if not headless:
            annotated = results.plot()
            cv2.imshow("GridSense — Edge AI Vision", annotated)
            cv2.waitKey(1)
        
        if time.time() - last_publish >= interval:
            for lane in LANES:
                count = lane_counts[lane]
                density = min((count / 15) * 100, 100.0)
                payload = {
                    "lane": lane,
                    "count": count,
                    "density": round(density, 1),
                    "ambulance": ambulance_detected, # Populated from detection logic
                    "ts": int(time.time()),
                }
                r.publish(CHANNEL, json.dumps(payload))
            last_publish = time.time()

if __name__ == "__main__":
    run(
        video_path=os.getenv("VIDEO_PATH", "traffic.mp4.mp4"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        interval=float(os.getenv("PUBLISH_INTERVAL", "1")),
    )
=======
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
>>>>>>> a07a24a3d90872702688a065bdae1136932c1afd
