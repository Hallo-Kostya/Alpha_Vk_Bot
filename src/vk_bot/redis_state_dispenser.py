import json
from typing import Any
from vkbottle.dispatch.dispenser.abc import ABCStateDispenser
import redis.asyncio as redis


from dataclasses import dataclass


@dataclass
class StatePeer:
    state: str
    payload: dict


class RedisStateDispenser(ABCStateDispenser):
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _key(self, user_id: int) -> str:
        return f"fsm:{user_id}"

    async def set(self, peer_id: int, state: str, **payload: Any):
        data = {"state": state, "payload": payload or {}}

        await self.redis.set(
            self._key(peer_id), json.dumps(data, default=str), ex=60 * 60 * 2
        )

    async def get(self, peer_id: int):
        raw = await self.redis.get(self._key(peer_id))
        if not raw:
            return None
        data = json.loads(raw)
        return StatePeer(state=data["state"], payload=data.get("payload", {}))

    async def clear(self, peer_id: int):
        await self.redis.delete(self._key(peer_id))

    async def delete(self, peer_id: int): ...
