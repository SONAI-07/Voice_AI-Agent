from abc import ABC, abstractmethod


class STTProvider(ABC):

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def send_audio(self, audio: bytes) -> None:
        pass

    @abstractmethod
    async def receive_events(self):
        pass

    @abstractmethod
    async def close(self) -> None:
        pass