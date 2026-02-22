"""Redis client for pub/sub and caching"""

import json
from typing import Optional, Any
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from nexwave.common.config import settings
from nexwave.common.logger import logger


class RedisClient:
    """Redis client wrapper for async operations"""

    def __init__(self):
        self._client: Optional[AsyncRedis] = None
        self._sync_client: Optional[Redis] = None

    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self._client = await AsyncRedis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis")

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        """Publish message to Redis channel"""
        if not self._client:
            await self.connect()

        try:
            await self._client.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
            raise

    async def xadd(
        self, stream: str, fields: dict[str, Any], maxlen: Optional[int] = None
    ) -> str:
        """Add message to Redis Stream"""
        if not self._client:
            await self.connect()

        try:
            args = {}
            if maxlen:
                args["maxlen"] = maxlen
                args["approximate"] = True

            # Convert fields to string values for Redis
            redis_fields = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                          for k, v in fields.items()}
            
            return await self._client.xadd(stream, redis_fields, **args)
        except Exception as e:
            logger.error(f"Failed to add to Redis stream: {e}")
            raise

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set key-value pair"""
        if not self._client:
            await self.connect()

        try:
            serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            await self._client.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.error(f"Failed to set Redis key: {e}")
            raise

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self._client:
            await self.connect()

        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Failed to get Redis key: {e}")
            return None

    async def subscribe(self, channel: str):
        """Subscribe to Redis channel (returns pubsub object)"""
        if not self._client:
            await self.connect()

        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def xgroup_create(self, stream: str, group_name: str, mkstream: bool = False):
        """Create a consumer group."""
        if not self._client:
            await self.connect()
        try:
            await self._client.xgroup_create(stream, group_name, mkstream=mkstream)
        except Exception as e:
            # redis.exceptions.ResponseError: BUSYGROUP Consumer Group name already exists
            if "BUSYGROUP" not in str(e):
                logger.error(f"Failed to create consumer group {group_name} for stream {stream}: {e}")
                raise

    async def xreadgroup(self, group_name: str, consumer_name: str, streams: dict, count: int, block: int):
        """Read from a stream using a consumer group."""
        if not self._client:
            await self.connect()
        try:
            return await self._client.xreadgroup(group_name, consumer_name, streams, count=count, block=block)
        except Exception as e:
            logger.error(f"Failed to read from streams with group {group_name}: {e}")
            return []

    async def xack(self, stream: str, group_name: str, *ids):
        """Acknowledge messages."""
        if not self._client:
            await self.connect()
        try:
            await self._client.xack(stream, group_name, *ids)
        except Exception as e:
            logger.error(f"Failed to acknowledge messages in stream {stream}: {e}")


# Global Redis client instance
redis_client = RedisClient()

