"""Data model for Wi-Fi signal samples."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json


@dataclass
class WiFiSample:
    """Represents a single Wi-Fi signal measurement at a 3D location."""
    x: float
    y: float
    z: float
    rssi: int
    ssid: Optional[str] = None
    bssid: Optional[str] = None
    frequency: Optional[int] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def from_json(cls, data: dict) -> 'WiFiSample':
        """Parse a WiFiSample from JSON dictionary."""
        timestamp = None
        if 'timestamp' in data and data['timestamp']:
            try:
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                timestamp = None

        return cls(
            x=float(data['x']),
            y=float(data['y']),
            z=float(data['z']),
            rssi=int(data['rssi']),
            ssid=data.get('ssid'),
            bssid=data.get('bssid'),
            frequency=data.get('frequency'),
            timestamp=timestamp
        )

    def is_valid(self) -> bool:
        """Check if the sample has valid required fields."""
        if not isinstance(self.rssi, int):
            return False
        if self.rssi < -120 or self.rssi > 0:
            return False
        return True


class PointCloudData:
    """Manages the collection of Wi-Fi samples with size limits."""

    def __init__(self, max_points: int = 100000):
        self.max_points = max_points
        self.samples: list[WiFiSample] = []
        self._rssi_min: Optional[int] = None
        self._rssi_max: Optional[int] = None

    def add_sample(self, sample: WiFiSample) -> bool:
        """Add a sample, enforcing size limit (FIFO). Returns True if added."""
        if not sample.is_valid():
            return False

        self.samples.append(sample)

        if len(self.samples) > self.max_points:
            self.samples.pop(0)

        self._update_rssi_range(sample.rssi)
        return True

    def _update_rssi_range(self, rssi: int) -> None:
        """Update cached RSSI range."""
        if self._rssi_min is None or rssi < self._rssi_min:
            self._rssi_min = rssi
        if self._rssi_max is None or rssi > self._rssi_max:
            self._rssi_max = rssi

    def get_rssi_range(self) -> tuple[int, int]:
        """Return (min, max) RSSI values."""
        if self._rssi_min is None:
            return (-90, -30)
        return (self._rssi_min, self._rssi_max)

    def clear(self) -> None:
        """Clear all samples."""
        self.samples.clear()
        self._rssi_min = None
        self._rssi_max = None

    def __len__(self) -> int:
        return len(self.samples)
