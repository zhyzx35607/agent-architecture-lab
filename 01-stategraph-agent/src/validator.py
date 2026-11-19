"""
图验证：检测无效图结构
拒绝不存在节点或循环
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Optional


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]

    def add_error(self, error: str):
        self.errors.append(error)

    def __bool__(self):
        return self.is_valid


class GraphValidator:
    """图验证器"""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: List[tuple] = []  # (source, target)

    def add_node(self, node_name: str):
        self.nodes.add(node_name)

    def remove_node(self, node_name: str):
        self.nodes.discard(node_name)

    def add_edge(self, source: str, target: str):
        self.edges.append((source, target))

    def validate_all(self) -> ValidationResult:
        """执行所有验证"""
        result = ValidationResult(is_valid=True, errors=[])

        if not self.nodes:
            result.add_error("图没有定义任何节点")
            return result

        self._validate_node_exists(result)
        self._validate_no_cycles(result)
        self._validate_start_exists(result)

        return result

    def _validate_node_exists(self, result: ValidationResult):
        """验证每条边的目标节点都存在"""
        for source, target in self.edges:
            if source not in self.nodes:
                result.add_error(f"边起点 '{source}' 不存在")
            if target not in self.nodes:
                result.add_error(f"边终点 '{target}' 不存在")

    def _validate_no_cycles(self, result: ValidationResult):
        """验证图无循环"""
        if not self.edges:
            return

        # 构建邻接表
        graph: Dict[str, List[str]] = {node: [] for node in self.nodes}
        for source, target in self.edges:
            graph[source].append(target)

        # DFS 检测循环
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(node: str) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph[node]:
                if has_cycle(neighbor):
                    return True

            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                if has_cycle(node):
                    result.add_error(f"图存在循环: {node}")
                    break

    def _validate_start_exists(self, result: ValidationResult):
        """验证存在起始节点（入度为0或标记为start）"""
        # 简单实现：找出入度为0的节点
        in_degree: Dict[str, int] = {node: 0 for node in self.nodes}

        for source, target in self.edges:
            if target in in_degree:
                in_degree[target] += 1

        start_nodes = [node for node, degree in in_degree.items() if degree == 0]

        # 如果没有入度为0的节点，可能存在循环或未连接图
        if not start_nodes:
            result.add_error("图没有起始节点（所有节点都有入度）")

    def validate_order(self, order: List[str]) -> ValidationResult:
        """验证节点的执行顺序"""
        result = ValidationResult(is_valid=True, errors=[])

        # 检查顺序是否包含有效节点
        for node in order:
            if node not in self.nodes:
                result.add_error(f"执行顺序中不停在的节点: {node}")

        # 检查边顺序是否满足
        node_positions: Dict[str, int] = {node: i for i, node in enumerate(order)}
        for source, target in self.edges:
            if source in node_positions and target in node_positions:
                if node_positions[source] >= node_positions[target]:
                    result.add_error(f"执行顺序违反边: {source} -> {target}")

        return result
