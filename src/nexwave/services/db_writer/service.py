"""Database Writer Service - Consumes from Redis Streams and writes to TimescaleDB"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List
from sqlalchemy import insert, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from nexwave.common.config import settings
from nexwave.common.logger import logger
from nexwave.common.redis_client import redis_client
from nexwave.db.session import AsyncSessionLocal, engine
from nexwave.db.models import Tick, WhaleActivity
from nexwave.schemas.market_data import TickData


class DatabaseWriter:
    """Service that writes market data to TimescaleDB"""

    def __init__(self, batch_size: int = 5000, write_interval: int = 5):
        self.batch_size = batch_size
        self.write_interval = write_interval
        self.tick_buffer: Dict[str, List[Dict]] = {}
        self.running = False
        self.group_name = "db_writers"
        self.consumer_name = f"writer-{os.getpid()}"

    async def _create_consumer_groups(self, channels: List[str]) -> None:
        """Create consumer groups for all streams if they don't exist"""
        for channel in channels:
            stream_name = f"market_data:{channel}"
            try:
                await redis_client.xgroup_create(
                    stream_name, self.group_name, mkstream=True
                )
                logger.info(f"Created consumer group '{self.group_name}' for stream '{stream_name}'")
            except Exception as e:
                if "BUSYGROUP" in str(e):
                    logger.info(f"Consumer group '{self.group_name}' already exists for stream '{stream_name}'")
                else:
                    logger.error(f"Error creating consumer group for '{stream_name}': {e}")


    async def ensure_hypertable(self) -> None:
        """Ensure ticks table is a TimescaleDB hypertable"""
        async with AsyncSessionLocal() as session:
            try:
                # Check if hypertable exists
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM timescaledb_information.hypertables 
                        WHERE hypertable_name = 'ticks'
                    """)
                )
                count = result.scalar()

                if count == 0:
                    # Create hypertable
                    logger.info("Creating TimescaleDB hypertable for ticks...")
                    await session.execute(
                        text("""
                            SELECT create_hypertable('ticks', 'time', 
                                chunk_time_interval => INTERVAL '1 day')
                        """)
                    )
                    await session.commit()
                    logger.info("Hypertable created successfully")
                else:
                    logger.info("Hypertable already exists")

            except Exception as e:
                logger.error(f"Error ensuring hypertable: {e}")
                await session.rollback()

    async def consume_streams(self) -> None:
        """Consume from Redis Streams using a consumer group and buffer messages"""
        logger.info(f"Starting to consume Redis Streams for group '{self.group_name}' as consumer '{self.consumer_name}'")

        channels = ["prices", "trades", "orderbook"]
        await self._create_consumer_groups(channels)
        
        stream_names = {f"market_data:{channel}": ">" for channel in channels}

        while self.running:
            try:
                messages = await redis_client.xreadgroup(
                    self.group_name, self.consumer_name, stream_names, count=100, block=1000
                )

                if not messages:
                    continue

                for stream, stream_messages in messages:
                    for msg_id, fields in stream_messages:
                        try:
                            data_json_str = fields.get("data", "{}")
                            tick_data = json.loads(data_json_str)
                            symbol = tick_data.get("symbol")
                            if not symbol:
                                continue

                            if symbol not in self.tick_buffer:
                                self.tick_buffer[symbol] = []

                            price = float(tick_data.get("mark") or tick_data.get("mid") or tick_data.get("oracle") or 0)
                            if price <= 0:
                                continue
                            
                            mid_price = float(tick_data.get("mid") or price)

                            self.tick_buffer[symbol].append({
                                "id": msg_id,
                                "stream": stream,
                                "tick": {
                                    "time": datetime.utcnow(),
                                    "symbol": symbol,
                                    "price": price,
                                    "volume": float(tick_data.get("volume_24h", 0)),
                                    "bid": mid_price - (mid_price * 0.0001),
                                    "ask": mid_price + (mid_price * 0.0001),
                                }
                            })

                        except Exception as e:
                            logger.error(f"Error parsing message {msg_id} from stream {stream}: {e}")

            except Exception as e:
                logger.error(f"Error consuming streams: {e}")
                await asyncio.sleep(1)

    async def write_batch(self) -> None:
        """Write buffered ticks to database and acknowledge messages"""
        while self.running:
            try:
                await asyncio.sleep(self.write_interval)

                if not self.tick_buffer:
                    continue

                for symbol, items in list(self.tick_buffer.items()):
                    if not items:
                        continue

                    batch_to_write = items[:self.batch_size]
                    remaining_items = items[self.batch_size:]
                    
                    ticks_to_insert = [item['tick'] for item in batch_to_write]
                    
                    try:
                        async with AsyncSessionLocal() as session:
                            await session.execute(insert(Tick), ticks_to_insert)
                            await session.commit()
                            
                            logger.info(f"Wrote {len(batch_to_write)} ticks for {symbol}")

                            # Acknowledge messages
                            acks_by_stream = {}
                            for item in batch_to_write:
                                stream = item['stream']
                                if stream not in acks_by_stream:
                                    acks_by_stream[stream] = []
                                acks_by_stream[stream].append(item['id'])
                            
                            for stream, ids in acks_by_stream.items():
                                await redis_client.xack(stream, self.group_name, *ids)
                                logger.debug(f"Acknowledged {len(ids)} messages for stream {stream}")

                        self.tick_buffer[symbol] = remaining_items

                    except Exception as e:
                        logger.error(f"Error writing batch for {symbol}, will retry: {e}")
                        await asyncio.sleep(1) # Wait before retrying
                        continue

            except Exception as e:
                logger.error(f"Error in write_batch: {e}")
                await asyncio.sleep(1)

    async def run(self) -> None:
        """Main service loop"""
        logger.info("Starting Database Writer Service...")

        await self.ensure_hypertable()
        await redis_client.connect()

        self.running = True

        consumer_task = asyncio.create_task(self.consume_streams())
        writer_task = asyncio.create_task(self.write_batch())

        try:
            await asyncio.gather(consumer_task, writer_task)
        except KeyboardInterrupt:
            logger.info("Shutting down Database Writer Service...")
        finally:
            self.running = False
            consumer_task.cancel()
            writer_task.cancel()
            await redis_client.disconnect()



async def run_db_writer_service():
    """Entry point for Database Writer Service"""
    from nexwave.common.logger import setup_logging
    
    setup_logging(level=settings.log_level)
    logger.info("Starting Database Writer Service...")
    
    writer = DatabaseWriter(
        batch_size=settings.batch_size,
        write_interval=settings.write_interval_sec,
    )
    await writer.run()


if __name__ == "__main__":
    asyncio.run(run_db_writer_service())

