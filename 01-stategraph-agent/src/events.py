"""
事件系统：记录图执行过程中的各种事件
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Any, Callable, List
from uuid import uuid4


class EventType(Enum):
    """事件类型"""
    GRAPH_START = "graph_start"
    GRAPH_END = "graph_end"
    GRAPH_ERROR = "graph_error"
    NODE_START = "node_start"
    NODE_END = "node_end"
    NODE_ERROR = "node_error"
    CONDITIONAL_ROUTE = "conditional_route"
    CHECKPOINT_SAVE = "checkpoint_save"
    CHECKPOINT_LOAD = "checkpoint_load"
    STEP_LIMIT = "step_limit"


@dataclass
class Event:
    """事件基础类"""
    event_type: EventType
    timestamp: float
    event_id: str
    data: dict

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "data": self.data
        }


class EventLogger:
    """事件记录器"""

    def __init__(self, max_events: int = 1000):
        self.events: List[Event] = []
        self.max_events = max_events
        self.subscribers: List[Callable[[Event], None]] = []

    def log(self, event_type: EventType, data: dict) -> Event:
        """记录事件"""
        event = Event(
            event_type=event_type,
            timestamp=self._get_timestamp(),
            event_id=str(uuid4()),
            data=data
        )

        # 添加事件
        if len(self.events) >= self.max_events:
            self.events.pop(0)
        self.events.append(event)

        # 通知订阅者
        for subscriber in self.subscribers:
            try:
                subscriber(event)
            except Exception:
                pass  # 订阅者错误不影响主流程

        return event

    def on_graph_start(self, graph_id: str, input_summary: str) -> Event:
        return self.log(EventType.GRAPH_START, {
            "graph_id": graph_id,
            "input_summary": input_summary
        })

    def on_graph_end(self, graph_id: str, steps: int, success: bool) -> Event:
        return self.log(EventType.GRAPH_END, {
            "graph_id": graph_id,
            "steps": steps,
            "success": success
        })

    def on_graph_error(self, graph_id: str, error: str) -> Event:
        return self.log(EventType.GRAPH_ERROR, {
            "graph_id": graph_id,
            "error": error
        })

    def on_node_start(self, graph_id: str, node_name: str, input_summary: str) -> Event:
        return self.log(EventType.NODE_START, {
            "graph_id": graph_id,
            "node_name": node_name,
            "input_summary": input_summary
        })

    def on_node_end(self, graph_id: str, node_name: str, output_summary: str) -> Event:
        return self.log(EventType.NODE_END, {
            "graph_id": graph_id,
            "node_name": node_name,
            "output_summary": output_summary
        })

    def on_node_error(self, graph_id: str, node_name: str, error: str) -> Event:
        return self.log(EventType.NODE_ERROR, {
            "graph_id": graph_id,
            "node_name": node_name,
            "error": error
        })

    def on_conditional_route(self, graph_id: str, node_name: str, route: str) -> Event:
        return self.log(EventType.CONDITIONAL_ROUTE, {
            "graph_id": graph_id,
            "node_name": node_name,
            "route": route
        })

    def on_checkpoint_save(self, graph_id: str, checkpoint_id: str) -> Event:
        return self.log(EventType.CHECKPOINT_SAVE, {
            "graph_id": graph_id,
            "checkpoint_id": checkpoint_id
        })

    def on_checkpoint_load(self, graph_id: str, checkpoint_id: str) -> Event:
        return self.log(EventType.CHECKPOINT_LOAD, {
            "graph_id": graph_id,
            "checkpoint_id": checkpoint_id
        })

    def on_step_limit(self, graph_id: str, max_steps: int) -> Event:
        return self.log(EventType.STEP_LIMIT, {
            "graph_id": graph_id,
            "max_steps": max_steps
        })

    def subscribe(self, callback: Callable[[Event], None]):
        """订阅事件"""
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Event], None]):
        """取消订阅"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def get_events(self) -> List[Event]:
        """获取所有事件"""
        return self.events.copy()

    def get_events_dict(self) -> List[dict]:
        """获取所有事件的字典形式"""
        return [e.to_dict() for e in self.events]

    def clear(self):
        """清理事件"""
        self.events.clear()

    def _get_timestamp(self) -> float:
        """获取时间戳（简单实现）"""
        import time
        return time.time()

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        import json
        return json.dumps(self.get_events_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "EventLogger":
        """从 JSON 字符串重建"""
        import json
        logger = cls()
        data = json.loads(json_str)
        # 注意：实际重建可能需要更复杂的时间戳处理
        for item in data:
            event = Event(
                event_type=EventType(item["event_type"]),
                timestamp=item["timestamp"],
                event_id=item["event_id"],
                data=item["data"]
            )
            logger.events.append(event)
        return logger
