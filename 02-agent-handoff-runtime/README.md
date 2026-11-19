# 02-agent-handoff-runtime：协作 Agent Runtime

这是一个 Python 3.12 标准库原创的多 Agent 协作运行时，设计上参考 [OpenAI Agents SDK for Python](https://github.com/openai/openai-agents-python)，不复制上游代码。默认模型是本地 `OfflineStub`，没有网络或 API key。

## 能力

- `Agent` 用名称、角色、允许的工具和允许交接的目标建立身份边界；
- `Tool` 绑定一个 Python callable，支持必须审批的工具；未知工具、未授权工具和拒绝审批都不会执行；
- `Runtime.handoff()` 以结构化结果记录 Agent 之间的任务交接；
- `max_calls` 是确定性的全局调用预算，防止工具循环失控；
 - `EventLog` 为注册、工具调用、拒绝、错误、审批和交接保存 UTC 时间戳、顺序号、主体、动作、结果和细节；
- `ModelAdapter`/`OfflineStub` 是可替换的模型协议，当前实现不发起模型请求；
- 仅演示内存中的计算和字符串工具，不读取用户文件、不执行 shell。

## 运行

```powershell
python demo.py
python -m unittest discover -s tests -v
```

演示会先调用计算器、交接给 reviewer，再展示发布工具在无审批时被拦截、获批后执行。当前测试 16 项，覆盖工具权限、审批批准/拒绝、交接、UTC 事件记录、异常记录、调用预算和可选离线模型 Adapter。

## 代码入口

- `runtime.py`：`Runtime`、`Agent`、`Tool`、`EventLog` 和安全异常；
- `protocol.py`：模型适配器 Protocol 和离线 Stub；
- `tests/test_runtime.py`：实际验收测试；
- `demo.py`：确定性离线演示；
- 其余小模块是对运行时公开类型的兼容转出。

这是一个受控顺序的本地原型，不是 OpenAI SDK 的兼容实现；超时、真实异步调度和真实模型服务不在本示例的保证范围内。
