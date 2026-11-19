"""可选模型协议：默认只使用确定性 Stub。"""
from dataclasses import dataclass
from typing import Protocol


class ModelAdapter(Protocol):
    def respond(self, prompt: str) -> str: ...


@dataclass
class OfflineStub:
    prefix: str = "offline"
    def respond(self, prompt: str) -> str:
        return f"{self.prefix}: {prompt.strip()}"
