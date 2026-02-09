"""Asyncio WebSocket server for receiving Wi-Fi samples."""

import asyncio
import json
import logging
from queue import Queue
from typing import Optional
import websockets
from websockets.server import WebSocketServerProtocol

from data_model import WiFiSample


logger = logging.getLogger(__name__)


class WiFiWebSocketServer:
    """WebSocket server that receives Wi-Fi samples and enqueues them."""

    def __init__(self, output_queue: Queue, host: str = "0.0.0.0", port: int = 8765):
        self.output_queue = output_queue
        self.host = host
        self.port = port
        self.server: Optional[websockets.WebSocketServer] = None
        self.connected_clients: set[WebSocketServerProtocol] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle a WebSocket client connection."""
        client_addr = websocket.remote_address
        logger.info(f"Client connected: {client_addr}")
        self.connected_clients.add(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    sample = WiFiSample.from_json(data)
                    self.output_queue.put(sample)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from {client_addr}: {e}")
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Invalid sample from {client_addr}: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
        finally:
            self.connected_clients.discard(websocket)

    async def _start_server(self) -> None:
        """Start the WebSocket server."""
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
        self._running = True
        await self.server.wait_closed()

    def start(self) -> None:
        """Start the server in a new event loop (call from thread)."""
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._start_server())
            finally:
                loop.close()

        import threading
        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the server."""
        self._running = False
        if self.server:
            self.server.close()

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running and self.server is not None

    def get_client_count(self) -> int:
        """Return the number of connected clients."""
        return len(self.connected_clients)
