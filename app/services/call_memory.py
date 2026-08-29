import json

from app.core.redis import redis_client


class CallMemory:

    def __init__(
            self,
            ttl_seconds: int = 60 * 60 * 6,
    ) -> None:
        self.ttl_seconds = ttl_seconds

    def _key(self, call_sid: str) -> str:
        return f"call:{call_sid}:conversation"

    async def append_message(
            self,
            call_sid: str,
            role: str,
            content: str,
    ) -> None:
        key = self._key(call_sid)

        message = {
            "role": role,
            "content": content,
        }

        await redis_client.rpush(
            key,
            json.dumps(message),
        )

        await redis_client.expire(
            key,
            self.ttl_seconds,
        )

    async def get_messages(
            self,
            call_sid: str,
    ) -> list[dict[str, str]]:

        key = self._key(call_sid)

        raw_messages = await redis_client.lrange(
            key,
            0,
            -1,
        )

        return [
            json.loads(message)
            for message in raw_messages
        ]

    async def delete(
            self,
            call_sid: str,
    ) -> None:
        await redis_client.delete(
            self._key(call_sid)
        )