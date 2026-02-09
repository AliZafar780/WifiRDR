import asyncio
import json
import logging
from typing import Optional, Callable
from websockets.server import WebSocketServerProtocol, serve
from websockets.exceptions import ConnectionClosed
from data_model import WiFiSample, PointCloudData


logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server that receives Wi-Fi samples and adds them to a point cloud."""

    def __init__(
        self,
        point_cloud: PointCloudData,
        host: str = "0.0.0.0",
        port: int = 8765,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None
    ):
        self.point_cloud = point_cloud
        self.host = host
        self.port = port
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self._server: Optional[asyncio.Server] = None
        self._connected_clients: set[WebSocketServerProtocol] = set()
        self._running = False

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle a single WebSocket client connection."""
        self._connected_clients.add(websocket)
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_addr}")

        if self.on_connect:
            try:
                self.on_connect()
            except Exception as e:
                logger.error(f"Error in on_connect callback: {e}")

        try:
            async for message in websocket:
                await self._process_message(message)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            self._connected_clients.discard(websocket)
            if not self._connected_clients and self.on_disconnect:
                try:
                    self.on_disconnect()
                except Exception as e:
                    logger.error(f"Error in on_disconnect callback: {e}")

    async def _process_message(self, message: str) -> None:
        """Parse and process a single JSON message."""
        try:
            data = json.loads(message)

            # Handle single sample or batch
            if isinstance(data, list):
                samples = []
                for item in data:
                    try:
                        sample = WiFiSample.from_json(item)
                        if sample.is_valid():
                            samples.append(sample)
                        else:
                            logger.warning(f"Invalid sample data: {item}")
                    except Exception as e:
                        logger.warning(f"Failed to parse sample: {e}")
                if samples:
                    self.point_cloud.add_many(samples)
                    logger.debug(f"Added {len(samples)} samples from batch")
            else:
                sample = WiFiSample.from_json(data)
                if sample.is_valid():
                    self.point_cloud.add(sample)
                    logger.debug(f"Added sample: {sample}")
                else:
                    logger.warning(f"Invalid sample data: {data}")

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        self._server = await serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )
        logger.info("WebSocket server started")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False
        logger.info("Stopping WebSocket server...")

        # Close all connected clients
        close_tasks = [client.close() for client in self._connected_clients]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        self._connected_clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("WebSocket server stopped")

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running

    def client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self._connected_clients)

    async def run_forever(self) -> None:
        """Run the server until stopped."""
        await self.start()
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
