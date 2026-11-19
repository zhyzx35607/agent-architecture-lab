from dataclasses import dataclass
@dataclass(frozen=True)
class RuntimeConfig:
    max_calls:int=10
