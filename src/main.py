#!/usr/bin/env python3
"""
WiMap3D - Wi-Fi Signal 3D Heatmap Visualizer

A cross-platform desktop MVP that ingests live Wi-Fi signal JSON over WebSocket
and renders a 3D point cloud heatmap colored by RSSI.
"""

import sys
import argparse
import asyncio
import logging
import threading
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

from data_model import PointCloudData
from ws_server import WebSocketServer
from ui import MainWindow


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AsyncHelper(QObject):
    """Helper class to bridge asyncio and Qt event loops."""

    sig_start_server = pyqtSignal()
    sig_stop_server = pyqtSignal()

    def __init__(self, ws_server: WebSocketServer, parent=None):
        super().__init__(parent)
        self.ws_server = ws_server
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the async event loop in a separate thread."""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self._running = True
        self.thread.start()

    def stop(self) -> None:
        """Stop the async event loop."""
        self._running = False
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.ws_server.stop(), self.loop)
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        """Run the asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self.ws_server.start())
            # Keep the loop running
            while self._running:
                self.loop.run_until_complete(asyncio.sleep(0.1))
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.loop.close()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="WiMap3D - Wi-Fi Signal 3D Heatmap Visualizer"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="WebSocket server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=100000,
        help="Maximum points to store (default: 100000)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("WiMap3D")
    app.setApplicationVersion("0.1.0")

    # Create data model
    point_cloud = PointCloudData(max_points=args.max_points)

    # Create main window
    window = MainWindow(point_cloud, port=args.port)

    # Track connection state
    connected_clients = [0]

    def on_connect() -> None:
        """Handle WebSocket client connection."""
        connected_clients[0] += 1
        window.set_connected(True)
        window.set_client_count(connected_clients[0])
        window.log_message(f"Client connected (total: {connected_clients[0]})")

    def on_disconnect() -> None:
        """Handle WebSocket client disconnection."""
        connected_clients[0] = max(0, connected_clients[0] - 1)
        window.set_client_count(connected_clients[0])
        window.log_message(f"Client disconnected (total: {connected_clients[0]})")
        if connected_clients[0] == 0:
            window.set_connected(False)

    # Create WebSocket server
    ws_server = WebSocketServer(
        point_cloud=point_cloud,
        host=args.host,
        port=args.port,
        on_connect=on_connect,
        on_disconnect=on_disconnect
    )

    # Start WebSocket server in separate thread with asyncio
    async_helper = AsyncHelper(ws_server)
    async_helper.start()

    logger.info(f"Starting WiMap3D on port {args.port}")
    window.log_message(f"WebSocket server starting on ws://{args.host}:{args.port}")

    # Show window
    window.show()

    # Run Qt event loop
    try:
        result = app.exec()
    finally:
        # Cleanup
        logger.info("Shutting down...")
        window.log_message("Shutting down...")
        async_helper.stop()

    return result


if __name__ == "__main__":
    sys.exit(main())
