from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import httpx
from pydantic import BaseModel

# TypeVar = "some type, decided later"
# "T" some type that is a subclass of BaseModel
T = TypeVar("T", bound=BaseModel)


class SourceProvider(ABC, Generic[T]):
    def __init__(self, client: httpx.AsyncClient, url: str):
        self._client = client
        self._url = url

    @abstractmethod
    async def fetch(self) -> list[T]:
        raise NotImplementedError
