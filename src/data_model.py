from dataclasses import dataclass, field
from typing import Optional
from collections import deque
import threading
import time


@dataclass
class WiFiSample:
    """Represents a single Wi-Fi signal measurement at a 3D position."""
    x: float
    y: float
    z: float = 0.0
    rssi: float = -70.0
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_json(cls, data: dict) -> "WiFiSample":
        """Create a WiFiSample from a JSON dictionary."""
        return cls(
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            z=float(data.get("z", 0)),
            rssi=float(data.get("rssi", -70)),
            ssid=data.get("ssid"),
            bssid=data.get("bssid"),
            timestamp=float(data.get("timestamp", time.time()))
        )

    def is_valid(self) -> bool:
        """Check if the sample has valid required fields."""
        try:
            _ = float(self.x)
            _ = float(self.y)
            _ = float(self.z)
            _ = float(self.rssi)
            return True
        except (TypeError, ValueError):
            return False


class PointCloudData:
    """Thread-safe container for point cloud data with size limits."""

    def __init__(self, max_points: int = 100000):
        self.max_points = max_points
        self._points: deque[WiFiSample] = deque(maxlen=max_points)
        self._lock = threading.RLock()
        self._total_received = 0
        self._total_dropped = 0

    def add(self, sample: WiFiSample) -> bool:
        """Add a sample to the point cloud. Returns True if added, False if dropped."""
        with self._lock:
            self._total_received += 1
            dropped = len(self._points) >= self.max_points
            if dropped:
                self._total_dropped += 1
            self._points.append(sample)
            return not dropped

    def add_many(self, samples: list[WiFiSample]) -> int:
        """Add multiple samples. Returns number of samples added."""
        added = 0
        with self._lock:
            for sample in samples:
                if self.add(sample):
                    added += 1
        return added

    def get_all(self) -> list[WiFiSample]:
        """Get a snapshot of all points (thread-safe copy)."""
        with self._lock:
            return list(self._points)

    def clear(self) -> None:
        """Clear all points."""
        with self._lock:
            self._points.clear()

    def get_stats(self) -> dict:
        """Get statistics about the point cloud."""
        with self._lock:
            return {
                "count": len(self._points),
                "max": self.max_points,
                "total_received": self._total_received,
                "total_dropped": self._total_dropped
            }

    def get_bounds(self) -> tuple:
        """Get the bounding box of all points."""
        with self._lock:
            if not self._points:
                return (-10, 10, -10, 10, -10, 10)
            xs = [p.x for p in self._points]
            ys = [p.y for p in self._points]
            zs = [p.z for p in self._points]
            return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
