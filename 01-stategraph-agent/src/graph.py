"""本地确定性状态图 Agent；不执行模型或外部副作用。"""
from __future__ import annotations
from dataclasses import dataclass, field
import copy
import hashlib
import json
from collections import deque
from typing import Any, Callable, Protocol


class ModelAdapter(Protocol):
    def generate(self, prompt: str) -> str: ...

@dataclass(frozen=True)
class OfflineStub:
    def generate(self, prompt: str) -> str:
        return "offline-stub: model calls are disabled"
class GraphError(RuntimeError):
    pass


@dataclass(frozen=True)
class Checkpoint:
    graph_hash: str
    state_json: str
    next_node: str | None
    steps: int
    sequence: int
    def to_json(self) -> str:
        return json.dumps({"graph_hash":self.graph_hash,"state_json":self.state_json,
                           "next_node":self.next_node,"steps":self.steps,"sequence":self.sequence},sort_keys=True)

    @classmethod
    def from_json(cls, document: str) -> "Checkpoint":
        try: data=json.loads(document)
        except (ValueError,TypeError) as exc: raise GraphError("invalid checkpoint JSON") from exc
        try: return cls(data["graph_hash"],data["state_json"],data["next_node"],int(data["steps"]),int(data["sequence"]))
        except (KeyError,TypeError,ValueError) as exc: raise GraphError("invalid checkpoint fields") from exc


@dataclass
class RunResult:
    status: str
    state: Any
    steps: int
    next_node: str | None = None
    checkpoint: Checkpoint | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class StateGraph:
    """按单条状态路径执行显式 DAG，并拒绝坏图或失控循环。"""
    def __init__(self, *, max_steps: int = 100, model: ModelAdapter | None = None):
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.max_steps = max_steps
        self.model = model or OfflineStub()
        self.nodes: dict[str, tuple[Callable[[Any], Any], Callable[[Any], bool] | None, int]] = {}
        self.edges: dict[str, list[str]] = {}
        self.routers: dict[str, tuple[Callable[[Any], str | None], dict[str, str]]] = {}
        self.start: str | None = None
        self.events: list[dict[str, Any]] = []

    def add_node(self, name: str, handler: Callable[[Any], Any], *, validator=None, retries: int = 0):
        if not name or name in self.nodes or not callable(handler):
            raise ValueError(f"invalid or duplicate node: {name!r}")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        self.nodes[name] = (handler, validator, retries)
        self.edges.setdefault(name, [])
        self.start = self.start or name
        return self

    def add_edge(self, source: str, target: str):
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("edge references an unknown node")
        if source in self.routers:
            raise ValueError("node may have either normal or conditional edges")
        if target not in self.edges[source]:
            self.edges[source].append(target)
        return self

    def add_conditional_edges(self, source: str, router: Callable[[Any], str | None], routes: dict[str, str]):
        if source not in self.nodes or not callable(router) or not routes:
            raise ValueError("invalid conditional route")
        if source in self.edges and self.edges[source]:
            raise ValueError("node may have either normal or conditional edges")
        if any(target not in self.nodes for target in routes.values()):
            raise ValueError("conditional route references an unknown node")
        self.routers[source] = (router, dict(routes))
        return self

    def validate(self) -> bool:
        if self.start not in self.nodes:
            raise GraphError("graph requires a start node")
        adjacency = {name: list(targets) for name, targets in self.edges.items()}
        for name, (_, destinations) in self.routers.items():
            adjacency[name].extend(destinations.values())
        if any(target not in self.nodes for targets in adjacency.values() for target in targets):
            raise GraphError("graph contains an unknown target")
        degree = {name: 0 for name in self.nodes}
        for targets in adjacency.values():
            for target in targets:
                degree[target] += 1
        queue = deque(name for name, count in degree.items() if count == 0)
        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for target in adjacency[current]:
                degree[target] -= 1
                if degree[target] == 0:
                    queue.append(target)
        if visited != len(self.nodes):
            raise GraphError("cycles are not permitted in a state graph")
        return True

    def fingerprint(self) -> str:
        shape = {"nodes": list(self.nodes), "edges": self.edges,
                 "routers": {name: sorted(routes.items()) for name, (_, routes) in self.routers.items()},
                 "start": self.start}
        return hashlib.sha256(json.dumps(shape, sort_keys=True).encode()).hexdigest()

    def invoke(self, initial_state: Any, *, pause_after: int | None = None,
               checkpoint: Checkpoint | None = None) -> RunResult:
        self.validate()
        self.events = []
        sequence = 0
        if checkpoint is not None:
            if checkpoint.graph_hash != self.fingerprint():
                raise GraphError("checkpoint belongs to a different graph")
            try:
                state = json.loads(checkpoint.state_json)
            except (ValueError, TypeError) as exc:
                raise GraphError("invalid checkpoint state") from exc
            current = checkpoint.next_node
            steps = checkpoint.steps
            sequence = checkpoint.sequence
            self._event("resume", current, steps)
        else:
            try:
                state = copy.deepcopy(initial_state)
                json.dumps(state)
            except (TypeError, ValueError) as exc:
                raise GraphError("state must be JSON serializable") from exc
            current = self.start
            steps = 0
            self._event("start", current, steps)
        if pause_after is not None and pause_after < 1:
            raise ValueError("pause_after must be positive")
        while current is not None:
            if steps >= self.max_steps:
                self._event("limit", current, steps)
                raise GraphError(f"maximum steps ({self.max_steps}) exceeded")
            handler, validator, retries = self.nodes[current]
            if validator is not None and not validator(copy.deepcopy(state)):
                self._event("rejected", current, steps)
                raise GraphError(f"input validation failed at {current!r}")
            last_error: Exception | None = None
            for attempt in range(retries + 1):
                try:
                    state = handler(copy.deepcopy(state))
                    json.dumps(state)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    self._event("retry" if attempt < retries else "error", current, steps)
            if last_error is not None:
                raise GraphError(f"node {current!r} failed") from last_error
            steps += 1
            self._event("node", current, steps)
            if current in self.routers:
                route, destinations = self.routers[current]
                key = route(copy.deepcopy(state))
                if key is None:
                    target = None
                elif key not in destinations:
                    raise GraphError(f"unknown route {key!r} from {current!r}")
                else:
                    target = destinations[key]
            else:
                targets = self.edges[current]
                if len(targets) > 1:
                    raise GraphError(f"ambiguous outgoing edges from {current!r}")
                target = targets[0] if targets else None
            if pause_after is not None and steps >= pause_after and target is not None:
                saved = Checkpoint(self.fingerprint(), json.dumps(state, sort_keys=True),
                                   target, steps, sequence + steps)
                self._event("paused", target, steps)
                return RunResult("paused", state, steps, target, saved, copy.deepcopy(self.events))
            current = target
        self._event("completed", None, steps)
        return RunResult("completed", state, steps, events=copy.deepcopy(self.events))

    def _event(self, event: str, node: str | None, step: int) -> None:
        self.events.append({"sequence": len(self.events), "type": event, "node": node, "step": step})
