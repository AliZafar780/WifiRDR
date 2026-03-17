# 📡 WiMap3D - Wi-Fi Signal Visualization

> A cross-platform desktop application for visualizing Wi-Fi signal strength as a 3D point cloud heatmap

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=flat&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="License" />
  <img src="https://img.shields.io/badge/OpenGL-Ready-blue?style=flat" alt="OpenGL" />
</p>

---

## ✨ Overview

WiMap3D ingests live Wi-Fi signal data over WebSocket and renders a real-time 3D point cloud heatmap colored by RSSI (Received Signal Strength Indicator).

## 🛠️ Features

| Feature | Description |
|:--------|:------------|
| 📡 **Real-time Mapping** | Live Wi-Fi signal visualization |
| 🎨 **3D Heatmap** | Color-coded by signal strength |
| 🔄 **Interactive Controls** | Orbit, pan, and zoom |
| 🌐 **WebSocket API** | Easy data ingestion |

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/AliZafar780/WifiRDR.git
cd WifiRDR

# Install dependencies
pip install -r requirements.txt

# Run the application
python wimap3d.py
```

## 📡 WebSocket Schema

Send JSON messages with this schema:

```json
{
  "x": float,        // X coordinate (meters)
  "y": float,        // Y coordinate (meters)
  "z": float,        // Z coordinate (optional)
  "rssi": float,     // Signal strength in dBm
  "ssid": string,    // Network name (optional)
  "bssid": string,   // MAC address (optional)
  "timestamp": float // Unix timestamp (optional)
}
```

## 🏗️ Architecture

| Component | Technology |
|:----------|:-----------|
| GUI | PyQt6 |
| 3D Rendering | PyOpenGL |
| Networking | asyncio + websockets |
| Data Queue | Thread-safe queue |

## 📁 Project Structure

```
WifiRDR/
├── wimap3d.py       # Main application
├── renderer/        # OpenGL rendering
├── network/        # WebSocket server
└── requirements.txt # Dependencies
```

## 📜 License

MIT License

---

*Visualize your Wi-Fi world 🌐*
