#!/usr/bin/env python3
"""Sample WebSocket client that sends synthetic Wi-Fi data for testing.

This script simulates a Wi-Fi scanner walking around a space and sending
RSSI measurements at various 3D positions.
"""

import asyncio
import json
import random
import math
import argparse
from datetime import datetime, timezone

import websockets


def generate_sample(x: float, y: float, z: float, rssi: int, ssid: str = None) -> dict:
    """Generate a Wi-Fi sample JSON object."""
    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "z": round(z, 2),
        "rssi": rssi,
        "ssid": ssid or f"Network-{random.randint(1, 5)}",
        "bssid": f"aa:bb:cc:dd:ee:{random.randint(0, 255):02x}",
        "frequency": random.choice([2412, 2437, 2462, 5180, 5200, 5220]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def send_random_walk(uri: str, rate: float = 10.0) -> None:
    """Send samples following a random walk pattern.

    Simulates a person walking around a building, measuring Wi-Fi signals
    at different positions. The signal strength varies based on distance
    from simulated access points.
    """
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        print(f"Connected. Sending {rate} samples/second...")
        print("Press Ctrl+C to stop")

        x, y, z = 0.0, 0.0, 1.5

        access_points = [
            {"x": 5.0, "y": 5.0, "z": 3.0, "power": -30},
            {"x": -5.0, "y": 5.0, "z": 3.0, "power": -35},
            {"x": 5.0, "y": -5.0, "z": 3.0, "power": -32},
            {"x": -5.0, "y": -5.0, "z": 3.0, "power": -38},
        ]

        sample_count = 0

        try:
            while True:
                dx = random.uniform(-0.5, 0.5)
                dy = random.uniform(-0.5, 0.5)
                x = max(-10, min(10, x + dx))
                y = max(-10, min(10, y + dy))

                for ap in access_points:
                    distance = math.sqrt((x - ap["x"])**2 + (y - ap["y"])**2 + (z - ap["z"])**2)
                    rssi = ap["power"] - 20 * math.log10(max(1, distance))
                    rssi += random.gauss(0, 3)
                    rssi = int(max(-95, min(-30, rssi)))

                    sample = generate_sample(x, y, z, rssi, ssid=f"AP-{ap['x']:.0f},{ap['y']:.0f}")
                    await websocket.send(json.dumps(sample))
                    sample_count += 1

                    await asyncio.sleep(1.0 / (rate * len(access_points)))

                    if sample_count % 50 == 0:
                        print(f"Sent {sample_count} samples...")

        except asyncio.CancelledError:
            print(f"\nStopped. Total samples sent: {sample_count}")


async def send_grid_scan(uri: str, rate: float = 20.0) -> None:
    """Send samples in a grid pattern for structured testing."""
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        print(f"Connected. Scanning grid at {rate} samples/second...")

        sample_count = 0
        grid_size = 8
        spacing = 2.0

        try:
            for xi in range(-grid_size, grid_size + 1):
                for yi in range(-grid_size, grid_size + 1):
                    x = xi * spacing + random.uniform(-0.2, 0.2)
                    y = yi * spacing + random.uniform(-0.2, 0.2)
                    z = 1.5 + random.uniform(-0.3, 0.3)

                    distance_from_center = math.sqrt(x**2 + y**2)
                    base_rssi = -30 - distance_from_center * 3
                    rssi = int(max(-90, min(-35, base_rssi + random.gauss(0, 5))))

                    sample = generate_sample(x, y, z, rssi)
                    await websocket.send(json.dumps(sample))
                    sample_count += 1

                    await asyncio.sleep(1.0 / rate)

                    if sample_count % 100 == 0:
                        print(f"Sent {sample_count} samples...")

            print(f"\nGrid scan complete. Total samples: {sample_count}")

        except asyncio.CancelledError:
            print(f"\nStopped. Total samples sent: {sample_count}")


async def send_burst(uri: str, count: int = 1000, rate: float = 100.0) -> None:
    """Send a burst of samples for stress testing."""
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        print(f"Sending burst of {count} samples at {rate}/second...")

        for i in range(count):
            angle = (i / count) * 4 * math.pi
            radius = 5 + 3 * math.sin(i / 50)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            z = 1.5 + 2 * math.sin(i / 100)

            rssi = int(-40 - 30 * math.sin(i / 200) + random.gauss(0, 5))
            rssi = max(-90, min(-30, rssi))

            sample = generate_sample(x, y, z, rssi)
            await websocket.send(json.dumps(sample))

            if (i + 1) % 100 == 0:
                print(f"Sent {i + 1}/{count} samples...")

            await asyncio.sleep(1.0 / rate)

        print(f"Burst complete. Sent {count} samples.")


def main():
    parser = argparse.ArgumentParser(
        description='Send synthetic Wi-Fi samples to WiMap3D',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--uri',
        type=str,
        default='ws://localhost:8765',
        help='WebSocket URI of the WiMap3D server'
    )
    parser.add_argument(
        '--mode',
        choices=['random-walk', 'grid-scan', 'burst'],
        default='random-walk',
        help='Sample generation mode'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=10.0,
        help='Samples per second (approximate)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=1000,
        help='Number of samples for burst mode'
    )

    args = parser.parse_args()

    try:
        if args.mode == 'random-walk':
            asyncio.run(send_random_walk(args.uri, args.rate))
        elif args.mode == 'grid-scan':
            asyncio.run(send_grid_scan(args.uri, args.rate))
        elif args.mode == 'burst':
            asyncio.run(send_burst(args.uri, args.count, args.rate))
    except KeyboardInterrupt:
        print("\nStopped by user")
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {args.uri}")
        print("Make sure WiMap3D is running and the port is correct")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
