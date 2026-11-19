# 03-browser-research-agent：离线浏览器研究 Agent

这是一个 Python 3.12 标准库原创的浏览器研究原型，设计上参考 [browser-use](https://github.com/browser-use/browser-use)，不复制上游代码。它只读取内存中的 mock 页面，不启动真实浏览器、不联网、不使用 API key。

## 能力

- `MockBrowser` 保存页面、标题、正文和链接；
- 每次导航强制 HTTPS、白名单主机、无用户凭据和标准端口；阻止 `file://`、`javascript:`、localhost、IP/未白名单域名和跨域 SSRF；
- `BrowserResearchAgent` 按深度和页面数量预算进行 BFS 多跳导航；
- 用可重复的英文词和中文双字词匹配查询，生成包含 URL、标题和正文摘录的 `Citation`；
- 去重已访问 URL，记录缺页和安全阻止错误；页面正文仅作为不可信数据，绝不当作命令执行；
- `Page`、`MockBrowser` 和 `BrowserResearchAgent` 都可由调用方注入，便于换成真实但受控的适配器。

可选 `ModelAdapter` 加默认离线 Stub，总结已检索引用；当前 demo 与测试不需要任何模型服务或 API key。

```powershell
python demo.py
python -m unittest discover -s tests -v
```

演示研究三个本地 mock 页面并输出两个来源引用和离线摘要。当前测试 17 项，覆盖 URL 策略、跨页导航、深度/页面预算、引用、错误回退和模型 Adapter 注入。

## 代码入口

- `browser_agent/mini.py`：`Page`、`MockBrowser`、`Citation`、`ResearchResult`、`BrowserResearchAgent`；
- `browser_agent/__init__.py`：公共导出；
- `tests/test_browser_agent.py`：实际验收测试；
- `demo.py`：本地三页演示。

目录中保留了早期实验的适配器/工作流文件，但当前入口和验收只使用 `mini.py`，避免把未连接的网络适配器误当成已启用能力。
