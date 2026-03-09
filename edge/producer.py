import json
import os
import sys
import time

import cv2
import redis
from ultralytics import YOLO

LANES = ["North", "South", "East", "West"]
CHANNEL = "traffic-telemetry"
VEHICLE_CLASSES = {2, 3, 5, 7}  # car, motorcycle, bus, truck


def get_lane(cx: float, cy: float, fw: int, fh: int) -> str:
    if cx < fw / 2 and cy < fh / 2:
        return "North"
    elif cx >= fw / 2 and cy < fh / 2:
        return "East"
    elif cx < fw / 2 and cy >= fh / 2:
        return "South"
    else:
        return "West"


def connect_redis(url: str) -> redis.Redis:
    for i in range(10):
        try:
            r = redis.Redis.from_url(url, decode_responses=True)
            r.ping()
            print("✅ Redis connected")
            return r
        except redis.ConnectionError:
            print(f"⚠️  Redis not ready ({i+1}/10), retrying...")
            time.sleep(3)
    print("❌ Redis failed")
    sys.exit(1)


def run():
    video_path = os.getenv("VIDEO_PATH", "/app/traffic.mp4.mp4")
    redis_url  = os.getenv("REDIS_URL", "redis://localhost:6379")
    interval   = float(os.getenv("PUBLISH_INTERVAL", "1"))

    r = connect_redis(redis_url)
    model = YOLO("yolov8n.pt")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        sys.exit(1)

    print(f"🎬 Processing: {video_path}")
    print("🚦 YOLO running — publishing to Redis every 1s")

    frame_idx = 0
    last_publish = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("🔁 Looping video")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame_idx += 1
        if frame_idx % 3 != 0:
            continue

        fh, fw = frame.shape[:2]
        results = model(frame, verbose=False)[0]

        lane_counts = {lane: 0 for lane in LANES}

        for box in results.boxes:
            if int(box.cls) not in VEHICLE_CLASSES:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            lane = get_lane((x1 + x2) / 2, (y1 + y2) / 2, fw, fh)
            lane_counts[lane] += 1

        if time.time() - last_publish >= interval:
            for lane in LANES:
                count = lane_counts[lane]
                payload = {
                    "lane": lane,
                    "count": count,
                    "density": round(min((count / 15) * 100, 100.0), 1),
                    "ambulance": False,  # only trigger via dashboard button
                    "ts": int(time.time()),
                }
                r.publish(CHANNEL, json.dumps(payload))
            last_publish = time.time()


if __name__ == "__main__":
    run()