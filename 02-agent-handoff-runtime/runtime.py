"""确定性多 Agent 协作运行时。"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from datetime import datetime, timezone
from protocol import ModelAdapter, OfflineStub


class RuntimeErrorBase(RuntimeError): pass
class ApprovalRequired(RuntimeErrorBase): pass
class PermissionDenied(RuntimeErrorBase): pass
class BudgetExceeded(RuntimeErrorBase): pass

@dataclass(frozen=True)
class Agent:
    name: str
    role: str
    allowed_tools: frozenset[str] = frozenset()
    can_handoff_to: frozenset[str] = frozenset()

@dataclass(frozen=True)
class Tool:
    name: str
    handler: Callable[..., Any]
    requires_approval: bool = False

@dataclass
class EventLog:
    entries: list[dict[str, Any]] = field(default_factory=list)
    def emit(self, actor: str, action: str, outcome: str, **detail: Any) -> dict[str, Any]:
        entry={"sequence":len(self.entries),"timestamp":datetime.now(timezone.utc).isoformat(),"actor":actor,"action":action,"outcome":outcome,"detail":detail}
        self.entries.append(entry); return entry

class Runtime:
    def __init__(self, *, max_calls: int = 10, model: ModelAdapter | None = None):
        if max_calls < 1: raise ValueError("max_calls must be positive")
        self.max_calls=max_calls; self.calls=0; self.model=model or OfflineStub(); self.agents={}; self.tools={}; self.log=EventLog()
    def add_agent(self, agent: Agent):
        if agent.name in self.agents: raise ValueError("duplicate agent")
        self.agents[agent.name]=agent; self.log.emit(agent.name,"register_agent","ok",role=agent.role)
    def add_tool(self, tool: Tool):
        if tool.name in self.tools: raise ValueError("duplicate tool")
        self.tools[tool.name]=tool; self.log.emit("runtime","register_tool","ok",tool=tool.name)
    def call_tool(self, actor: str, tool_name: str, args: dict[str, Any], *, approved: bool = False) -> Any:
        if actor not in self.agents: raise PermissionDenied("unknown actor")
        agent=self.agents[actor]
        if tool_name not in agent.allowed_tools: self.log.emit(actor,"tool_call","denied",tool=tool_name); raise PermissionDenied("tool not allowed")
        if tool_name not in self.tools: raise PermissionDenied("unknown tool")
        tool=self.tools[tool_name]
        if tool.requires_approval and not approved:
            self.log.emit(actor,"tool_call","approval_required",tool=tool_name); raise ApprovalRequired(tool_name)
        if self.calls >= self.max_calls:
            self.log.emit(actor,"tool_call","budget_exceeded",tool=tool_name); raise BudgetExceeded("call budget exhausted")
        self.calls += 1
        try:
            result=tool.handler(**args); self.log.emit(actor,"tool_call","ok",tool=tool_name); return result
        except Exception as exc:
            self.log.emit(actor,"tool_call","error",tool=tool_name,error=type(exc).__name__); raise
    def handoff(self, actor: str, target: str, task: str) -> str:
        if actor not in self.agents or target not in self.agents: raise PermissionDenied("unknown agent")
        if target not in self.agents[actor].can_handoff_to:
            self.log.emit(actor,"handoff","denied",target=target); raise PermissionDenied("handoff not allowed")
        self.log.emit(actor,"handoff","ok",target=target,task=task)
        return f"{target} accepted: {task}"
    def run_plan(self, actor: str, plan: list[dict[str, Any]]) -> list[Any]:
        results=[]
        for step in plan:
            kind=step.get("kind")
            if kind=="tool": results.append(self.call_tool(actor,step["name"],step.get("args",{}),approved=step.get("approved",False)))
            elif kind=="handoff": results.append(self.handoff(actor,step["target"],step["task"]))
            else: raise RuntimeErrorBase("unknown plan step")
        return results
