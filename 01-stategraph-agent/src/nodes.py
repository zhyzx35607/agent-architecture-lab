"""
节点定义：StateNode 和 ConditionalRouter
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol


class NodeStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ModelProtocol(Protocol):
    """
    可选模型接口协议
    支持离线 Stub 实现，主逻辑接受用户调用的 Callable 不依赖网络
    """

    def is_available(self) -> bool:
        """检查模型是否可用"""
        ...

    def execute(self, prompt: str) -> str:
        """执行模型调用（需联网）"""
        ...

    @property
    def name(self) -> str:
        """模型名称"""
        ...


@dataclass
class StateNode:
    """
    状态节点
    不可变输入或校验，可预测转换
    """
    name: str
    func: Callable[[Any], Any]
    status: NodeStatus = NodeStatus.PENDING
    input_validator: Optional[Callable[[Any], bool]] = None
    retry_times: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate_input(self, state: Any) -> bool:
        """验证输入"""
        if self.input_validator is None:
            return True
        return self.input_validator(state)

    def execute(self, state: Any) -> Any:
        """执行节点逻辑，返回转换后的状态"""
        if not self.validate_input(state):
            raise ValueError(f"节点 {self.name} 输入验证失败")

        self.status = NodeStatus.RUNNING
        return self.func(state)

    def mark_success(self):
        self.status = NodeStatus.SUCCESS

    def mark_failed(self, error: Exception = None):
        self.status = NodeStatus.FAILED

    def mark_skipped(self):
        self.status = NodeStatus.SKIPPED

    def __repr__(self):
        return f"StateNode({self.name}, status={self.status.value})"


class ConditionalRouter:
    """
    条件路由
    基于状态执行条件判断，返回下一个节点名称
    """

    def __init__(self, route_func: Callable[[Any], Optional[str]]):
        self.route_func = route_func
        self.routes: Dict[str, str] = {}  # route_key -> next_node

    def set_routes(self, routes: Dict[str, str]):
        """设置路由映射：route_key -> next_node"""
        self.routes = routes

    def route(self, state: Any) -> Optional[str]:
        """
        根据条件路由状态
        返回下一个节点名称，None 表示结束
        """
        route_key = self.route_func(state)
        if route_key is None:
            return None

        # 查找对应的目标节点
        return self.routes.get(route_key)

    def __repr__(self):
        return f"ConditionalRouter(routes={self.routes})"
