# 04-safe-coding-agent：安全代码审查与补丁 Agent

这是一个 Python 3.12 标准库原创的离线代码审查/补丁原型，设计上参考 [OpenHands](https://github.com/OpenHands/OpenHands)，不复制上游代码。它不执行 shell、不运行用户项目、不连接模型或网络。

## 安全边界

调用方必须显式提供自己创建的 sandbox root。所有相对路径先做 `resolve()` 和 containment 检查；拒绝绝对路径、`..`、隐藏/凭据路径、符号链接逃逸、非允许扩展名、二进制、超过大小上限和匹配凭据模式的内容。敏感内容 fail closed，不输出原文。

## 能力

- `search(query)` 只读检索 sandbox 中的安全文本并返回相对路径和行号；
- `propose_patch(path, old_text, new_text)` 要求锚点恰好匹配一次，记录 base SHA-256 和补丁 SHA-256；
- `approve(proposal, displayed_digest)` 只接受用户展示的准确摘要，并在审批时再次确认 base 内容；
- `apply(proposal, approval)` 检查令牌、一次性使用、base SHA、锚点、敏感内容和 Python AST，然后用同目录临时文件原子替换；
- `verify_python()` 只解析 AST，不执行代码；没有真实测试器或 subprocess；
- 可选模型只能由外层注入，本目录默认完全离线。

## 运行

```powershell
python demo.py
python -m unittest discover -s tests -v
```
调用方可通过 `ModelAdapter` 显式注入审查器；默认 `OfflineReviewer` 不发送请求。读取的源码必须先通过路径和敏感内容检查；任何模型建议仍需要调用方人工审阅，再单独生成、展示并批准 SHA-256 补丁。
演示在当前项目内创建短命的临时 mock 仓库，检索 `sample.py`、批准一项安全文本补丁并校验 AST 后自动清理。当前测试 20 项，覆盖路径边界、符号链接、二进制/大文件/敏感内容、篡改和陈旧审批、AST 验证以及离线/自定义审查 Adapter。

## 代码入口

- `safe_coding_agent.py`：`SafeCodingAgent`、`Proposal`、`Approval`、`Rejected`、`StalePatch`；
- `tests/test_coding_agent.py`：实际验收测试；
- `demo.py`：确定性安全演示；
- `requirements.txt`：仅声明 Python 3.12 标准库。

这不是 OpenHands 的兼容实现，也不应当被当作生产级沙盒、代码审计器或真实测试替代品。
