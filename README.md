# Agent Architecture Lab

**目标**：在本地用 Python 3.12 和 Python 标准库，从零实现可运行、可测试的 Agent 架构样例。每个子项目都是独立目录，不复制上游仓库的源代码或文档；用确定性 mock 运行，不需要 API key、网络、容器或收费服务。

> 四个示例相互独立，目录本身不依赖其他本机仓库。安全代码 Agent 仅在演示用临时沙盒中工作。

## 四个独立项目

| 目录 | 架构实验 | 设计参考 | 入口 |
| --- | --- | --- | --- |
| [01-stategraph-agent](01-stategraph-agent/) | 有状态工作流、条件路由、检查点与恢复 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | `python demo.py` |
| [02-agent-handoff-runtime](02-agent-handoff-runtime/) | Agent 与受限工具、任务交接、审批和事件记录 | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | `python demo.py` |
| [03-browser-research-agent](03-browser-research-agent/) | 域名白名单内的模拟浏览器、跨页收集和引用 | [browser-use/browser-use](https://github.com/browser-use/browser-use) | `python demo.py` |
| [04-safe-coding-agent](04-safe-coding-agent/) | 边界约束、只读源码查找、补丁哈希审批和模拟验证 | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | `python demo.py` |

## 快速运行

在每个项目目录中运行 `python -m unittest discover -s tests -v` 与 `python demo.py`。全部验收（执行所需的临时文件写入仅发生在本目录之下）：

```powershell
python run_checks.py
```

只执行某个项目时：

```powershell
Set-Location .\01-stategraph-agent
python -m unittest discover -s tests -v
python demo.py
```

以上项目目录的 `requirements.txt` 均注明 Python 版本并且不安装第三方依赖。**四个项目和测试均是本地原型而非生产或上游全功能兼容版本。** Agent 的回答、网页、工具和模型适配器使用明确标记的离线样例或 Protocol；测试通过不代表真实模型质量、真正访问网站、隔离容器或已证明的生产安全性。

## 上游调研

 - [19 个 GitHub 候选项目、许可证和 GitHub API 核验数据](sources/AGENT_PROJECTS.md)
- [可供程序进一步处理的同批来源 JSON](sources/repositories.json)

GitHub 搜索结果与来源清单只用于调研参考，Star 数和最近推送时间是 **2026-11-19 UTC** 的一次查询快照，并非质量评价。尚未在清单上核对的许可证标为 `NOASSERTION`，不是假设其开放许可。使用上游时须单独阅读对应仓库实际许可证和目录级声明。此处为架构启发而写的原创实现，没有复制或再发布上述仓库源码。

## License

This repository is licensed under the [MIT License](LICENSE).
