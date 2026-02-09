# WiMap3D

A cross-platform desktop MVP for visualizing Wi-Fi signal strength as a 3D point cloud heatmap.

## Overview

WiMap3D ingests live Wi-Fi signal data over WebSocket and renders a real-time 3D point cloud heatmap colored by RSSI (Received Signal Strength Indicator). Features interactive orbit, pan, and zoom controls.

## Architecture

- **PyQt6**: Cross-platform GUI framework
- **PyOpenGL**: 3D rendering with hardware acceleration
- **asyncio + websockets**: WebSocket server for real-time data ingestion
- **Thread-safe queue**: Decouples network I/O from rendering

## WebSocket Schema

WiMap3D listens for JSON messages over WebSocket with the following schema:

```json
{
  "x": float,        // X coordinate (meters)
  "y": float,        // Y coordinate (meters)
  "z": float,        // Z coordinate (meters, optional, defaults to 0)
  "rssi": float,     // Signal strength in dBm (typically -30 to -90)
  "ssid": string,    // Network name (optional)
  "bssid": string,   // MAC address (optional)
  "timestamp": float // Unix timestamp (optional)
}
```

### Example message:
```json
{"x": 1.5, "y": 2.0, "z": 0.5, "rssi": -45.5, "ssid": "MyNetwork"}
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the Desktop App

```bash
python src/main.py
```

Options:
- `--port`: WebSocket port (default: 8765)
- `--max-points`: Maximum points to render (default: 100000)

```bash
python src/main.py --port 9000 --max-points 50000
```

### Send Test Data

Use the included sample sender to stream synthetic data:

```bash
python scripts/sample_sender.py
```

Options:
- `--host`: WebSocket host (default: localhost)
- `--port`: WebSocket port (default: 8765)
- `--rate`: Points per second (default: 10)
- `--count`: Total points to send (default: infinite)

```bash
python scripts/sample_sender.py --host 192.168.1.100 --port 8765 --rate 20
```

## Controls

| Action | Control |
|--------|---------|
| Orbit | Left click + drag |
| Pan | Right click + drag |
| Zoom | Scroll wheel |
| Reset view | R key |

## Project Structure

```
.
├── src/
│   ├── main.py        # Application entry point
│   ├── ui.py          # Main window and UI layout
│   ├── gl_view.py     # OpenGL 3D renderer
│   ├── ws_server.py   # WebSocket server
│   └── data_model.py  # Data structures and queue
├── scripts/
│   └── sample_sender.py  # Test data generator
├── requirements.txt
└── README.md
```

## Performance Notes

- Point list is capped at 100,000 points by default to prevent GPU/CPU overload
- Older points are automatically removed when the limit is exceeded
- Rendering uses OpenGL vertex buffers for efficient GPU upload
