"""Pacifica WebSocket client for market data"""

import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed
from nexwave.common.config import settings
from nexwave.common.logger import logger
from nexwave.common.redis_client import redis_client


class ConnectionState(Enum):
    """WebSocket connection state"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class PacificaWSClient:
    """WebSocket client for Pacifica DEX"""

    def __init__(
        self,
        ws_url: Optional[str] = None,
        symbols: Optional[list[str]] = None,
    ):
        self.ws_url = ws_url or settings.pacifica_ws_url
        self.symbols = symbols or settings.symbol_list
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.subscriptions: Dict[str, bool] = {}
        self.reconnect_delays = [1, 2, 4, 8, 16, 60]  # Exponential backoff
        self.running = False

    async def connect(self) -> None:
        """Connect to WebSocket with exponential backoff"""
        self.state = ConnectionState.CONNECTING

        delay_index = 0
        while self.running:
            try:
                logger.info(f"Connecting to {self.ws_url}...")

                headers = {}
                if settings.pacifica_api_key:
                    headers["X-API-KEY"] = settings.pacifica_api_key

                self.websocket = await websockets.connect(
                    self.ws_url,
                    additional_headers=headers,
                    ping_interval=30,
                    ping_timeout=20,
                    close_timeout=10,
                )
                self.state = ConnectionState.CONNECTED
                delay_index = 0  # Reset on success
                logger.info("WebSocket connected successfully")

                # Subscribe to all channels
                await self._subscribe_all()

                return

            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                delay = self.reconnect_delays[min(delay_index, len(self.reconnect_delays) - 1)]
                delay_index += 1
                logger.info(f"Reconnecting in {delay} seconds...")
                await asyncio.sleep(delay)
                self.state = ConnectionState.RECONNECTING

    async def _subscribe_all(self) -> None:
        """Subscribe to all required channels"""
        if not self.websocket:
            return

        try:
            # Subscribe to data sources using Pacifica's format
            # Format: {"method": "subscribe", "params": {"source": "channel_name"}}
            subscriptions = [
                {"method": "subscribe", "params": {"source": "prices"}},
                {"method": "subscribe", "params": {"source": "orderbook"}},
                {"method": "subscribe", "params": {"source": "trades"}},
                # Note: Pacifica may not support all channels, adjust as needed
            ]

            for sub in subscriptions:
                await self.websocket.send(json.dumps(sub))
                logger.debug(f"Subscribed to {sub}")

            logger.info(f"Subscribed to {len(subscriptions)} data sources")

        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            raise

    async def _process_message(self, message: dict) -> None:
        """Process incoming WebSocket message"""
        try:
            channel = message.get("channel")
            data = message.get("data")

            # Skip subscription confirmations
            if channel == "subscribe":
                logger.info(f"Subscription confirmed: {data}")
                return

            # Handle data messages - data is an array of ticker objects
            if not data or not isinstance(data, list):
                logger.debug(f"Skipping message with no data: {message}")
                return

            # Process each ticker in the data array
            for ticker in data:
                if not isinstance(ticker, dict):
                    continue

                symbol = ticker.get("symbol")
                if not symbol:
                    continue

                # Normalize and publish to Redis
                normalized = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "channel": channel,
                    "data": ticker,
                }

                # Publish to Redis Stream
                stream_name = f"market_data:{channel}"
                await redis_client.xadd(stream_name, normalized)

                logger.debug(f"Processed {channel} message for {symbol}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def listen(self) -> None:
        """Listen for WebSocket messages"""
        self.running = True

        while self.running:
            try:
                if not self.websocket or self.state != ConnectionState.CONNECTED:
                    await self.connect()

                # Receive message
                message_str = await self.websocket.recv()
                message = json.loads(message_str)

                # Process message
                await self._process_message(message)

            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.state = ConnectionState.DISCONNECTED
                if self.running:
                    await self.connect()
            except asyncio.TimeoutError:
                logger.warning("WebSocket receive timeout")
                # Reconnect if timeout
                if self.running:
                    await self.connect()
            except Exception as e:
                logger.error(f"Error in WebSocket listener: {e}")
                await asyncio.sleep(1)
                if self.running:
                    await self.connect()

    async def stop(self) -> None:
        """Stop the WebSocket client"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        self.state = ConnectionState.DISCONNECTED
        logger.info("WebSocket client stopped")


async def run_market_data_service():
    """Main entry point for Market Data Service"""
    from nexwave.common.logger import setup_logging
    from nexwave.common.config import settings
    
    setup_logging(level=settings.log_level)
    logger.info("Starting Market Data Service...")

    await redis_client.connect()

    client = PacificaWSClient()
    
    try:
        await client.listen()
    except KeyboardInterrupt:
        logger.info("Shutting down Market Data Service...")
    finally:
        await client.stop()
        await redis_client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_market_data_service())

