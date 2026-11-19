# 开源 Agent 架构调研与 GitHub 来源

> 查询时间：2026-11-19 UTC。下列数据在执行本地调研期间逐一通过 GitHub 官方 REST API `GET /repos/{owner}/{repo}` 获取；仓库许可列采用当时 GitHub API `license.spdx_id` 原值，未确认的项目明确标为 `NOASSERTION`。GitHub 指标会变化；请打开直达链接复核当前信息及仓库内是否存在路径级额外许可证。Star 数用于快速观察规模而不是质量排名。

目录覆盖图工作流、角色协作、浏览器、软件工程、多 Agent 框架、记忆与检索、MCP 接入和模型路由等公开项目；并不声称复制整个仓库。标成“设计参考”仅表示启发独立实现，**不代表兼容上游、复制了其源码或获得上游背书**。

## GitHub 官方 API 核验快照

| # | 仓库 | 类型／可研究架构 | API 许可证 ID | Stars 快照 | API 最近推送 (UTC) |
| ---: | --- | --- | --- | ---: | --- |
| 1 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 有状态图执行、检查点和多 Actor 工作流 | MIT | 45,154 | 2026-11-19 |
| 2 | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | Agent loop、工具、handoff、guardrail | MIT | 30,764 | 2026-11-19 |
| 3 | [browser-use/browser-use](https://github.com/browser-use/browser-use) | 浏览器控制和网页 Agent | MIT | 121,477 | 2026-11-19 |
| 4 | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | 软件工程 Agent 与交互式执行环境 | MIT | 93,818 | 2026-11-19 |
| 5 | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 角色团队、任务与流程编排 | MIT | 61,096 | 2026-11-19 |
| 6 | [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) | 多角色软件团队和结构化协作 | MIT | 71,355 | 2026-01-21 |
| 7 | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) | 长时间、多 Agent 研究流程与工具编排 | MIT | 85,517 | 2026-11-19 |
| 8 | [huggingface/smolagents](https://github.com/huggingface/smolagents) | 工具执行循环与代码 Agent | Apache-2.0 | 30,443 | 2026-11-18 |
| 9 | [QwenLM/Qwen-Agent](https://github.com/QwenLM/Qwen-Agent) | 工具调用、Agent 与应用框架 | Apache-2.0 | 17,273 | 2026-03-04 |
| 10 | [topoteretes/cognee](https://github.com/topoteretes/cognee) | 可检索知识图和记忆基础设施 | Apache-2.0 | 33,403 | 2026-11-18 |
| 11 | [run-llama/llama_index](https://github.com/run-llama/llama_index) | 数据连接、知识索引及 RAG | MIT | 52,953 | 2026-11-14 |
| 12 | [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) | SWE 问题求解、工具与终端 Agent 设计 | MIT | 20,832 | 2026-11-16 |
| 13 | [google/adk-python](https://github.com/google/adk-python) | 模块化 Agent、交接和工作流开发套件 | Apache-2.0 | 22,272 | 2026-11-19 |
| 14 | [Aider-AI/aider](https://github.com/Aider-AI/aider) | 仓库内协作编程和代码编辑 Agent | Apache-2.0 | 50,178 | 2026-05-22 |
| 15 | [microsoft/autogen](https://github.com/microsoft/autogen) | 多 Agent 消息传递及协作框架 | CC-BY-4.0 | 61,935 | 2026-11-12 |
| 16 | [camel-ai/camel](https://github.com/camel-ai/camel) | 多 Agent 角色扮演、工具和任务规划 | Apache-2.0 | 18,048 | 2026-11-16 |
| 17 | [elizaOS/eliza](https://github.com/elizaOS/eliza) | 插件化和角色驱动 Agent 平台 | MIT | 19,905 | 2026-11-19 |
| 18 | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | MCP Python SDK；适合研究工具协议互操作 | MIT | 24,901 | 2026-11-17 |
| 19 | [microsoft/semantic-kernel](https://github.com/microsoft/semantic-kernel) | Agent、插件、规划与跨模型 SDK | MIT | 28,789 | 2026-11-19 |

## 四个首批独立实现的主要参考

| 本仓库原型 | 设计参考直达链接 | API 核验许可证 |
| --- | --- | --- |
| `01-stategraph-agent` | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | MIT |
| `02-agent-handoff-runtime` | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | MIT |
| `03-browser-research-agent` | [browser-use/browser-use](https://github.com/browser-use/browser-use) | MIT |
| `04-safe-coding-agent` | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | MIT |

### 许可证与来源的限制

- 仓库层面的 API `license` 字段是 GitHub 的元数据识别结果，并不替代逐文件审查；例如许可证归属、第三方依赖、模型和数据文件仍需分别检查。
- `NOASSERTION` 代表本次 API 未能证明许可证；这种仓库不可据本目录假定具有任何重用许可。
- 即使 API 显示 MIT 或 Apache-2.0，上游仓库也可能包含各自的版权、NOTICE、非软件资产和独立条款。完整复刻、分发源代码或二进制前必须再次检查当时版本的 LICENSE / NOTICE。
四个主要设计参考用于启发标准库独立原型的架构；相关许可证信息仅来自 GitHub 仓库元数据，不代表导入、复制或重新发布上游实现。
