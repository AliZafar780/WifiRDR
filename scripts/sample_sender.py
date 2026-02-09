#!/usr/bin/env python3
"""
Sample data sender for WiMap3D testing.

Streams synthetic Wi-Fi signal data to the WiMap3D WebSocket server.
Use this to test the visualization without real Wi-Fi hardware.
"""

import asyncio
import json
import argparse
import random
import math
import signal
import sys
from typing import Optional

import websockets


class SampleDataGenerator:
    """Generates synthetic Wi-Fi signal data for testing."""

    # Wi-Fi signal strength ranges (dBm)
    RSSI_MIN = -90
    RSSI_MAX = -30

    def __init__(self, mode: str = "random"):
        self.mode = mode
        self._time = 0.0
        self._index = 0

    def generate(self) -> dict:
        """Generate a single sample."""
        if self.mode == "random":
            return self._generate_random()
        elif self.mode == "walk":
            return self._generate_walk()
        elif self.mode == "scan":
            return self._generate_scan()
        elif self.mode == "helix":
            return self._generate_helix()
        else:
            return self._generate_random()

    def _generate_random(self) -> dict:
        """Generate a random sample."""
        # Random position in a 20x20x5 meter area
        x = random.uniform(-10, 10)
        y = random.uniform(-10, 10)
        z = random.uniform(0, 5)

        # RSSI based on distance from center (stronger near center)
        distance = math.sqrt(x**2 + y**2 + z**2)
        max_dist = math.sqrt(10**2 + 10**2 + 5**2)
        rssi_base = self.RSSI_MAX - (distance / max_dist) * (self.RSSI_MAX - self.RSSI_MIN)
        rssi = rssi_base + random.uniform(-5, 5)  # Add noise

        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3),
            "rssi": round(rssi, 2),
            "ssid": random.choice(["TestNet", "HomeWiFi", "Office5G", "Guest"]),
            "bssid": f"00:11:22:33:44:{random.randint(0x10, 0xFF):02X}",
            "timestamp": asyncio.get_event_loop().time()
        }

    def _generate_walk(self) -> dict:
        """Generate a sample from a random walk."""
        # Initialize position on first call
        if not hasattr(self, '_pos'):
            self._pos = [0.0, 0.0, 1.0]
            self._vel = [0.1, 0.05, 0.0]

        # Update position with velocity
        self._pos[0] += self._vel[0] + random.uniform(-0.1, 0.1)
        self._pos[1] += self._vel[1] + random.uniform(-0.1, 0.1)
        self._pos[2] = max(0.5, min(5, self._pos[2] + random.uniform(-0.2, 0.2)))

        # Bounce off walls
        for i in range(3):
            if abs(self._pos[i]) > 10:
                self._vel[i] *= -1
                self._pos[i] = max(-10, min(10, self._pos[i]))

        # RSSI based on position with some noise
        rssi = random.uniform(self.RSSI_MIN + 10, self.RSSI_MAX - 10)

        return {
            "x": round(self._pos[0], 3),
            "y": round(self._pos[1], 3),
            "z": round(self._pos[2], 3),
            "rssi": round(rssi, 2),
            "ssid": "WalkTest",
            "bssid": "00:11:22:33:44:55",
            "timestamp": asyncio.get_event_loop().time()
        }

    def _generate_scan(self) -> dict:
        """Generate samples in a grid scan pattern."""
        grid_size = 5
        x = (self._index % grid_size) * 4 - 8
        y = (self._index // grid_size) % grid_size * 4 - 8
        z = (self._index // (grid_size * grid_size)) % 3 * 2

        self._index += 1
        if self._index >= grid_size * grid_size * 3:
            self._index = 0

        # Signal strength varies by position
        distance = math.sqrt(x**2 + y**2)
        rssi = self.RSSI_MAX - distance * 2 + random.uniform(-3, 3)

        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3),
            "rssi": round(rssi, 2),
            "ssid": "ScanGrid",
            "bssid": f"00:11:22:33:44:{self._index % 256:02X}",
            "timestamp": asyncio.get_event_loop().time()
        }

    def _generate_helix(self) -> dict:
        """Generate samples along a helical path."""
        t = self._time
        radius = 5.0
        frequency = 0.5
        height_scale = 2.0

        x = radius * math.cos(t)
        y = radius * math.sin(t)
        z = 2.5 + height_scale * math.sin(frequency * t)

        self._time += 0.2

        # RSSI varies with height (stronger at higher points)
        rssi = self.RSSI_MIN + (z / 5) * (self.RSSI_MAX - self.RSSI_MIN)
        rssi += random.uniform(-2, 2)

        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3),
            "rssi": round(rssi, 2),
            "ssid": "HelixTest",
            "bssid": "00:AA:BB:CC:DD:EE",
            "timestamp": asyncio.get_event_loop().time()
        }


async def send_samples(
    uri: str,
    generator: SampleDataGenerator,
    rate: float,
    count: Optional[int],
    batch_size: int = 1
) -> None:
    """Send generated samples to the WebSocket server."""
    sent = 0
    interval = 1.0 / rate

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            print(f"Sending {rate} samples/sec (batch size: {batch_size})")

            batch = []
            while count is None or sent < count:
                sample = generator.generate()
                batch.append(sample)

                if len(batch) >= batch_size:
                    if batch_size == 1:
                        await websocket.send(json.dumps(batch[0]))
                    else:
                        await websocket.send(json.dumps(batch))
                    sent += len(batch)
                    batch = []
                    print(f"Sent: {sent} samples", end='\r')

                await asyncio.sleep(interval / batch_size)

            # Send remaining samples
            if batch:
                await websocket.send(json.dumps(batch))
                sent += len(batch)

            print(f"\nTotal samples sent: {sent}")

    except websockets.exceptions.ConnectionRefused:
        print(f"Error: Could not connect to {uri}")
        print("Make sure WiMap3D is running.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Sample data sender for WiMap3D testing"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="WebSocket server host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Samples per second (default: 10)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Total samples to send (default: infinite)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="random",
        choices=["random", "walk", "scan", "helix"],
        help="Sample generation mode (default: random)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=1,
        help="Batch size for sending samples (default: 1)"
    )
    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    uri = f"ws://{args.host}:{args.port}"
    generator = SampleDataGenerator(mode=args.mode)

    # Handle Ctrl+C gracefully
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        print("\nStopping...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    print(f"WiMap3D Sample Sender")
    print(f"Mode: {args.mode}, Rate: {args.rate}/sec")
    print(f"Target: {uri}")
    print("Press Ctrl+C to stop\n")

    try:
        await send_samples(
            uri=uri,
            generator=generator,
            rate=args.rate,
            count=args.count,
            batch_size=args.batch
        )
    except asyncio.CancelledError:
        pass

    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
