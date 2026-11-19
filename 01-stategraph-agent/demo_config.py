"""
演示配置：定义图中的节点和逻辑
"""


def process_state(state):
    """处理状态"""
    state["processed"] = True
    state["count"] = state.get("count", 0) + 1
    return state


def validate_state(state):
    """状态验证器"""
    return isinstance(state, dict) and "value" in state


def conditional_router(state):
    """条件路由函数"""
    if state.get("value", 0) > 10:
        return "high"
    elif state.get("value", 0) > 5:
        return "mid"
    return "low"


def high_route(state):
    """高值路由处理"""
    state["route"] = "high"
    return state


def mid_route(state):
    """中值路由处理"""
    state["route"] = "mid"
    return state


def low_route(state):
    """低值路由处理"""
    state["route"] = "low"
    return state


def end_state(state):
    """结束状态"""
    state["finished"] = True
    return state


# 演示数据
DEMO_INITIAL_STATE = {
    "value": 7,
    "name": "demo"
}
