from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    async def generate_stream(
            self,
            messages: list[dict[str, str]],
    ):
        pass