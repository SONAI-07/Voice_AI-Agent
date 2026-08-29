import json

from app.core.redis import redis_client


class CallMemory:

    def __init__(
            self,
            ttl_seconds: int = 60 * 60 * 6,
    ) -> None:
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _key(call_sid: str) -> str:
        return f"call:{call_sid}:conversation"

    async def append_message(
            self,
            call_sid: str,
            role: str,
            content: str,
    ) -> None:
        if not call_sid:
            raise ValueError("call_sid is required")

        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"Unsupported message role: {role}")

        if not content:
            return

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

        if not call_sid:
            raise ValueError("call_sid is required")

        raw_messages = await redis_client.lrange(
            self._key(call_sid),
            0,
            -1,
        )

        messages: list[dict[str, str]] = []

        for raw_message in raw_messages:
            message = json.loads(raw_message)

            if (
                    not isinstance(message, dict)
                    or "role" not in message
                    or "content" not in message
            ):
                raise ValueError(
                    "Invalid message stored in call memory"
                )

            messages.append(
                {
                    "role": str(message["role"]),
                    "content": str(message["content"]),
                }
            )

        return messages

    async def exists(
            self,
            call_sid: str,
    ) -> bool:
        return bool(
            await redis_client.exists(
                self._key(call_sid)
            )
        )

    async def delete(
            self,
            call_sid: str,
    ) -> None:
        await redis_client.delete(
            self._key(call_sid)
        )

    async def ttl(
            self,
            call_sid: str,
    ) -> int:
        return await redis_client.ttl(
            self._key(call_sid)
        )