"""WiMap3D - Wi-Fi Signal 3D Visualization Tool

A cross-platform desktop application that ingests live Wi-Fi signal JSON over
WebSocket and renders a 3D point cloud heatmap colored by RSSI.
"""

import sys
import argparse
import logging
from queue import Queue
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from data_model import PointCloudData, WiFiSample
from ws_server import WiFiWebSocketServer
from ui import MainWindow


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='WiMap3D - Wi-Fi Signal Visualizer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--ws-port',
        type=int,
        default=8765,
        help='WebSocket server port'
    )
    parser.add_argument(
        '--ws-host',
        type=str,
        default='0.0.0.0',
        help='WebSocket server host'
    )
    parser.add_argument(
        '--max-points',
        type=int,
        default=100000,
        help='Maximum number of points to retain in memory'
    )
    return parser.parse_args()


class DataBridge:
    """Bridge between WebSocket server and data model.

    Consumes samples from the WebSocket queue and adds them to the point cloud.
    This is called from the Qt main loop to ensure thread safety.
    """

    def __init__(self, queue: Queue, data: PointCloudData):
        self.queue = queue
        self.data = data

    def process_pending(self) -> int:
        """Process all pending samples in the queue. Returns count processed."""
        count = 0
        while not self.queue.empty():
            try:
                sample = self.queue.get_nowait()
                if isinstance(sample, WiFiSample):
                    self.data.add_sample(sample)
                    count += 1
            except Exception:
                break
        return count


def main() -> int:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    args = parse_args()

    logger.info(f"Starting WiMap3D with WebSocket on {args.ws_host}:{args.ws_port}")
    logger.info(f"Max points: {args.max_points:,}")

    sample_queue: Queue = Queue()
    data = PointCloudData(max_points=args.max_points)

    ws_server = WiFiWebSocketServer(
        output_queue=sample_queue,
        host=args.ws_host,
        port=args.ws_port
    )
    ws_server.start()

    app = QApplication(sys.argv)
    app.setApplicationName("WiMap3D")
    app.setApplicationVersion("0.1.0")

    window = MainWindow(data, ws_server)
    window.show()

    bridge = DataBridge(sample_queue, data)

    from PyQt6.QtCore import QTimer
    def process_samples():
        processed = bridge.process_pending()
        if processed > 0:
            window.gl_view.update()

    sample_timer = QTimer()
    sample_timer.timeout.connect(process_samples)
    sample_timer.start(16)

    logger.info("Application started. Waiting for WebSocket connections...")

    try:
        return app.exec()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        ws_server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
