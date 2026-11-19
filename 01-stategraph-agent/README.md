# 01-stategraph-agent：确定性状态图 Agent

这是一个使用 Python 3.12 标准库独立实现的状态图执行原型，设计上参考 [LangGraph](https://github.com/langchain-ai/langgraph)，不复制上游代码。它不连接模型或网络，节点只在当前 Python 进程中执行。

## 能力

- 注册节点和顺序边，支持条件路由；
- 在执行前拒绝空图、未知节点、循环图和坏路由；
- 节点输入校验、有限重试、最大步数和错误因果传播；
- 对 JSON 状态做深拷贝，防止节点直接改变调用者输入；
- 用 JSON 状态、下一节点、图指纹和步数表示检查点，可暂停/恢复；
- 为开始、恢复、节点、重试、失败、暂停和完成生成有序事件记录；
- `OfflineStub` 不在本项目中调用模型；需要接模型时应通过上层自己的适配器注入。
`StateGraph(model=...)` 可注入上层自带的 `ModelAdapter`；默认 `OfflineStub` 不发送请求，节点行为和测试始终由本地确定性 Python 函数提供。
## 运行

```powershell
python demo.py
python -m unittest discover -s tests -v
```

`demo.py` 会执行 `collect -> route -> approved`，在路由后暂停，再从 JSON 检查点恢复。当前测试 19 项，覆盖图路由、JSON checkpoint round-trip、重试、错误传播、输入检查和步数限制。

## 代码入口

- `src/graph.py`：`StateGraph`、`Checkpoint`、`RunResult`、`GraphError`；
- `tests/test_agent.py`：实际验收测试；其余 `test_*.py` 是保留的兼容空测试模块；
- `requirements.txt`：仅声明 Python 版本和标准库；
- `demo.py`：无需 API key 的离线演示。

本项目是教学和架构验证原型，不是 LangGraph 的兼容实现，也不执行任意外部命令。
