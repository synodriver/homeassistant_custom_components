"""Redis client helpers."""

import redis.asyncio as aioredis

from .const import SOCKET_CONNECT_TIMEOUT, SOCKET_TIMEOUT


def create_redis_client(
    host: str,
    port: int,
    username: str | None,
    password: str | None,
) -> aioredis.Redis:
    """Create a redis.asyncio.Redis client."""
    return aioredis.Redis(
        host=host,
        port=port,
        username=username or None,
        password=password or None,
        socket_connect_timeout=SOCKET_CONNECT_TIMEOUT,
        socket_timeout=SOCKET_TIMEOUT,
        decode_responses=True,
    )
