# WiMap3D

A cross-platform desktop MVP for visualizing live Wi-Fi signal data as a 3D point cloud heatmap.

## Features

- Real-time WebSocket ingestion of Wi-Fi signal samples
- 3D point cloud visualization with RSSI-based color heatmap
- Interactive camera controls (orbit, pan, zoom)
- Connection status and metrics display
- Thread-safe data pipeline between WebSocket server and Qt GUI

## JSON Schema for Incoming Samples

WebSocket messages must be JSON with the following structure:

```json
{
  "x": 1.5,
  "y": 2.0,
  "z": 0.5,
  "rssi": -65,
  "ssid": "MyNetwork",
  "bssid": "aa:bb:cc:dd:ee:ff",
  "frequency": 2412,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Required Fields
- `x`, `y`, `z`: Float coordinates in meters
- `rssi`: Integer signal strength in dBm (typically -100 to -30)

### Optional Fields
- `ssid`: Network name
- `bssid`: MAC address of access point
- `frequency`: Channel frequency in MHz
- `timestamp`: ISO 8601 timestamp

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the Desktop App

```bash
python src/main.py
```

Optional arguments:
```bash
python src/main.py --ws-port 8765 --max-points 100000
```

- `--ws-port`: WebSocket server port (default: 8765)
- `--max-points`: Maximum points to retain in memory (default: 100000)

### Send Test Data

```bash
python scripts/sample_sender.py
```

## Controls

- **Left Mouse Button + Drag**: Orbit camera around the scene
- **Right Mouse Button + Drag**: Pan camera
- **Scroll Wheel**: Zoom in/out
- **R**: Reset camera to default view

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PyQt6 Main Window                                          │
│  ┌─────────────────────────┬─────────────────────────────┐  │
│  │                         │                             │  │
│  │  OpenGL Point Cloud     │  Status Panel               │  │
│  │  (GLView)               │  - Connection status        │  │
│  │                         │  - Point count              │  │
│  │  Interactive:           │  - RSSI range               │  │
│  │  - Orbit/Zoom/Pan       │  - FPS                      │  │
│  │                         │                             │  │
│  └─────────────────────────┴─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ Thread-safe Queue
                           │
┌──────────────────────────┴──────────────────────────────────┐
│  Asyncio WebSocket Server (ws_server.py)                     │
│  - Receives JSON samples from network                        │
│  - Validates and enqueues to data pipeline                   │
└─────────────────────────────────────────────────────────────┘
```
