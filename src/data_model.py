import logging
from dataclasses import dataclass, field
from typing import Optional
from collections import deque
import threading
import time


logger = logging.getLogger(__name__)


# Valid coordinate range bounds
COORD_MIN: float = -10000.0
COORD_MAX: float = 10000.0
RSSI_MIN_VALID: float = -100.0
RSSI_MAX_VALID: float = 0.0


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
        """Check if the sample has valid required fields and reasonable value ranges."""
        try:
            x = float(self.x)
            y = float(self.y)
            z = float(self.z)
            rssi = float(self.rssi)
        except (TypeError, ValueError):
            return False

        # Coordinate range validation
        if not (COORD_MIN <= x <= COORD_MAX):
            return False
        if not (COORD_MIN <= y <= COORD_MAX):
            return False
        if not (COORD_MIN <= z <= COORD_MAX):
            return False

        # RSSI range validation (typical Wi-Fi: -100 dBm to 0 dBm)
        if not (RSSI_MIN_VALID <= rssi <= RSSI_MAX_VALID):
            return False

        return True


class PointCloudData:
    """Thread-safe container for point cloud data with size limits."""

    def __init__(self, max_points: int = 100000, max_batch_size: int = 1000):
        self.max_points = max_points
        self.max_batch_size = max_batch_size
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
        # Enforce maximum batch size
        if len(samples) > self.max_batch_size:
            logger.warning(
                f"Batch size {len(samples)} exceeds max_batch_size "
                f"{self.max_batch_size}, truncating to {self.max_batch_size}"
            )
            samples = samples[:self.max_batch_size]

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
