from abc import ABC, abstractmethod


class TTSProvider(ABC):

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def synthesize(self, text: str) -> None:
        pass

    @abstractmethod
    async def receive_audio(self):
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass