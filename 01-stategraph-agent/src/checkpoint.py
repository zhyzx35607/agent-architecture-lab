"""
检查点管理：持久 JSON 保存与载入，支持暂停和恢复
"""

import json
import os
import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional


@dataclass
class Checkpoint:
    """检查点数据结构"""
    checkpoint_id: str
    graph_id: str
    state: Any
    step: int
    max_steps: int
    timestamp: float
    event_log: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "graph_id": self.graph_id,
            "state": self.state,
            "step": self.step,
            "max_steps": self.max_steps,
            "timestamp": self.timestamp,
            "event_log": self.event_log
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """从字典创建"""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            graph_id=data["graph_id"],
            state=data["state"],
            step=data["step"],
            max_steps=data["max_steps"],
            timestamp=data["timestamp"],
            event_log=data.get("event_log")
        )


class CheckpointManager:
    """
    检查点管理器
    支持 JSON 格式保存/恢复状态，可持久化
    """

    def __init__(self, path: str = "checkpoints"):
        self.path = path
        self.checkpoints: Dict[str, Checkpoint] = {}
        self._ensure_dir()

    def _ensure_dir(self):
        """确保检查点目录存在"""
        os.makedirs(self.path, exist_ok=True)

    def create_checkpoint(self, graph_id: str, state: Any,
                         step: int, max_steps: int,
                         event_log: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """创建并保存检查点"""
        checkpoint = Checkpoint(
            checkpoint_id=self._generate_id(),
            graph_id=graph_id,
            state=state,
            step=step,
            max_steps=max_steps,
            timestamp=time.time(),
            event_log=event_log
        )

        self.save_checkpoint(checkpoint)
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint

        return checkpoint

    def save_checkpoint(self, checkpoint: Checkpoint) -> str:
        """将检查点保存到 JSON 文件"""
        filepath = os.path.join(self.path, f"{checkpoint.checkpoint_id}.json")

        data = checkpoint.to_dict()
        # 注意：state 可能不是可序列化的，实际使用需要特殊处理
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except TypeError as e:
            raise ValueError(f"状态不可序列化: {e}")

        return filepath

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """从 JSON 文件加载检查点"""
        if checkpoint_id in self.checkpoints:
            return self.checkpoints[checkpoint_id]

        filepath = os.path.join(self.path, f"{checkpoint_id}.json")

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            checkpoint = Checkpoint.from_dict(data)
            self.checkpoints[checkpoint_id] = checkpoint

            return checkpoint
        except (json.JSONDecodeError, KeyError) as e:
            return None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        if checkpoint_id not in self.checkpoints:
            return False

        filepath = os.path.join(self.path, f"{checkpoint_id}.json")

        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            del self.checkpoints[checkpoint_id]
            return True
        except OSError:
            return False

    def list_checkpoints(self) -> list:
        """列出所有检查点"""
        return [
            {
                "checkpoint_id": c.checkpoint_id,
                "graph_id": c.graph_id,
                "step": c.step,
                "timestamp": c.timestamp
            }
            for c in self.checkpoints.values()
        ]

    def get_latest(self, graph_id: str) -> Optional[Checkpoint]:
        """获取指定图最新的检查点"""
        graph_checkpoints = [
            c for c in self.checkpoints.values() if c.graph_id == graph_id
        ]

        if not graph_checkpoints:
            return None

        return max(graph_checkpoints, key=lambda c: c.timestamp)

    def _generate_id(self) -> str:
        """生成唯一检查点 ID"""
        import uuid
        return f"chk_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    def clear_all(self):
        """清空所有检查点"""
        for checkpoint_id in list(self.checkpoints.keys()):
            self.delete_checkpoint(checkpoint_id)
