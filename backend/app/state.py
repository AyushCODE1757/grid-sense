import time
from dataclasses import dataclass, field
from typing import Dict

from .models import LANES, LightColor

W_DENSITY = 0.6
W_TIME = 0.4
MIN_GREEN = 15
MAX_GREEN = 60
STARVATION_SECONDS = 90
EVALUATION_INTERVAL_SECONDS = 5


@dataclass
class IntersectionState:
    lights: Dict[str, LightColor] = field(default_factory=lambda: {lane: LightColor.RED for lane in LANES})
    densities: Dict[str, float] = field(default_factory=lambda: {lane: 0.0 for lane in LANES})
    counts: Dict[str, int] = field(default_factory=lambda: {lane: 0 for lane in LANES})
    last_green_at: Dict[str, float] = field(default_factory=lambda: {lane: time.time() for lane in LANES})
    current_green_lane: str = "North"
    green_until: float = 0.0
    emergency_active: bool = False
    emergency_lane: str | None = None
    emergency_until: float = 0.0
    cycle_count: int = 0
    last_event: str = "Initialized"

    def __post_init__(self) -> None:
        self.set_green("North", reason="Initial startup")

    def set_green(self, lane: str, reason: str) -> None:
        now = time.time()
        for key in LANES:
            self.lights[key] = LightColor.GREEN if key == lane else LightColor.RED
        self.current_green_lane = lane
        self.last_green_at[lane] = now
        self.cycle_count += 1
        self.last_event = reason
        duration = self.compute_green_duration(self.densities[lane])
        self.green_until = now + duration

    def compute_green_duration(self, density: float) -> int:
        scaled = MIN_GREEN + (density / 100.0) * (MAX_GREEN - MIN_GREEN)
        return int(max(MIN_GREEN, min(MAX_GREEN, scaled)))

    def wait_seconds(self, lane: str) -> int:
        return int(time.time() - self.last_green_at[lane])

    def priority_score(self, lane: str) -> float:
        wait = self.wait_seconds(lane)
        if wait > STARVATION_SECONDS:
            return 999.0
        return (self.densities[lane] * W_DENSITY) + (wait * W_TIME)

    def choose_next_lane(self) -> str:
        ranked = sorted(LANES, key=lambda lane: self.priority_score(lane), reverse=True)
        return ranked[0]

    def trigger_emergency(self, lane: str, duration_seconds: int) -> None:
        now = time.time()
        self.emergency_active = True
        self.emergency_lane = lane
        self.emergency_until = now + duration_seconds
        for key in LANES:
            self.lights[key] = LightColor.GREEN if key == lane else LightColor.RED
        self.current_green_lane = lane
        self.last_green_at[lane] = now
        self.last_event = f"Emergency override for {lane} ({duration_seconds}s)"

    def tick(self) -> bool:
        now = time.time()

        if self.emergency_active:
            if now < self.emergency_until:
                return False
            self.emergency_active = False
            self.emergency_lane = None
            self.last_event = "Emergency window ended"

        if now < self.green_until:
            return False

        next_lane = self.choose_next_lane()
        if next_lane != self.current_green_lane:
            self.set_green(next_lane, reason=f"Scheduled switch to {next_lane}")
            return True

        self.green_until = now + self.compute_green_duration(self.densities[self.current_green_lane])
        return False

    def avg_wait_seconds(self) -> float:
        waits = [self.wait_seconds(lane) for lane in LANES]
        return sum(waits) / len(waits)

    def snapshot(self) -> dict:
        return {
            "lights": self.lights,
            "densities": self.densities,
            "counts": self.counts,
            "active_emergency": self.emergency_active,
            "emergency_lane": self.emergency_lane,
            "cycle_count": self.cycle_count,
            "avg_wait_seconds": round(self.avg_wait_seconds(), 2),
            "last_event": self.last_event,
            "evaluation_interval_seconds": EVALUATION_INTERVAL_SECONDS,
            "min_green_seconds": MIN_GREEN,
            "max_green_seconds": MAX_GREEN,
        }
