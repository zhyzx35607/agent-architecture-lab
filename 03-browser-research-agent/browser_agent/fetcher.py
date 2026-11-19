"""
安全 Fetcher - 实现 Protocol 抽象，提供 URL 验证和安全检查
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Protocol
import re
import time


@dataclass
class Fetched:
    """获取结果数据类"""
    url: str
    title: str
    content: str
    links: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None
    is_security_violation: bool = False


class FetchProtocol(Protocol):
    """Fetcher 协议接口"""

    async def fetch(self, url: str, timeout: float = 5.0) -> Optional[Fetched]:
        """获取页面内容"""
        ...


class SecurityError(Exception):
    """安全错误异常"""
    pass


class URLValidator:
    """URL 验证器 - 严格的安全检查"""

    # 白名单域名（仅允许这些 mock 域名）
    WHITELIST_DOMAINS = {
        "news.mock.com",
        "demo.mock.com",
        "local.mock.com",
    }

    # 禁止的协议
    FORBIDDEN_PROTOCOLS = {"http", "ftp", "file", "javascript"}

    # 禁止的 host（SSRF 防护）
    FORBIDDEN_HOSTS = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "localhost.localdomain",
    }

    # HTTPS 模式（仅允许的协议）
    ALLOWED_PROTOCOLS = {"https"}

    # URL 正则（简化的 URL 解析）
    URL_PATTERN = re.compile(
 r'^([a-zA-Z]+)://'  # 协议
 r'([^:/?#]+)'       # host
 r'(?::\d+)?'        # 端口
 r'([^?#]*)'         # 路径
 r'(?:\?([^#]*))?'   # 查询参数
 r'(?:#(.*))?'       # 片段
    )

    @classmethod
    def validate(cls, url: str) -> tuple[bool, Optional[str]]:
        """
        验证 URL 安全性
        返回：(是否有效，错误信息)
        """
        if not url or not isinstance(url, str):
            return False, "URL 不能为空"

        # 检查是否为文件协议
        if url.startswith("file://"):
            return False, "禁止使用 file:// 协议"

        # 检查是否为 javascript 协议
        if url.startswith("javascript:"):
            return False, "禁止使用 javascript:// 协议"

        # 简单的协议和 host 提取
        if "://" in url:
            protocol, rest = url.split("://", 1)
            protocol = protocol.lower()

            # 检查协议是否被禁止
            if protocol in cls.FORBIDDEN_PROTOCOLS:
                return False, f"禁止使用 {protocol}:// 协议"

            # 检查协议是否允许（如果没有显式禁止，则要求 https）
            if protocol not in cls.ALLOWED_PROTOCOLS:
                return False, f"仅允许 {', '.join(cls.ALLOWED_PROTOCOLS)} 协议"

            # 提取 host
            host = rest.split("/")[0].split(":")[0]

            # 检查 host 是否在黑名单中
            if host in cls.FORBIDDEN_HOSTS:
                return False, f"禁止访问 {host} (SSRF 防护)"

            # 检查 host 是否在白名单中
            if host not in cls.WHITELIST_DOMAINS:
                return False, f"域名 {host} 不在白名单中，仅允许：{', '.join(cls.WHITELIST_DOMAINS)}"

            return True, None
        else:
            return False, "URL 格式无效，必须包含协议 (如 https://)"

    @classmethod
    def is_valid_https(cls, url: str) -> bool:
        """快速检查 URL 是否是有效的白名单 HTTPS URL"""
        valid, _ = cls.validate(url)
        return valid


class MockFetcher:
    """
    Mock Fetcher - 实现 FetchProtocol 的安全 fetcher
    使用内置 MockBrowser 获取内存页面
    """

    def __init__(self, browser, allowed_domains: Optional[set] = None):
        self.browser = browser
        self.allowed_domains = allowed_domains or URLValidator.WHITELIST_DOMAINS
        self.security_log: List[dict] = []

    async def fetch(self, url: str, timeout: float = 5.0) -> Optional[Fetched]:
        """
        安全地获取页面内容
        1. 进行 URL 安全检查
        2. 通过验证后调用浏览器访问
        3. 记录所有操作
        """
        # 安全检查
        is_valid, error_msg = URLValidator.validate(url)
        if not is_valid:
            self._log_security_event(url, "blocked", error_msg)
            return Fetched(
                url=url,
                title="",
                content="",
                error=error_msg,
                is_security_violation=True
            )

        # URL 合法，尝试访问
        try:
            fetched = await self.browser.visit(url, timeout)

            if fetched:
                self._log_security_event(url, "allowed", "success")
                return fetched
            else:
                self._log_security_event(url, "not_found", "页面不存在")
                return Fetched(
                    url=url,
                    title="",
                    content="",
                    error="页面不存在"
                )

        except Exception as e:
            self._log_security_event(url, "error", str(e))
            return Fetched(
                url=url,
                title="",
                content="",
                error=f"访问失败：{str(e)}"
            )

    def _log_security_event(self, url: str, status: str, message: str) -> None:
        """记录安全事件"""
        self.security_log.append({
            "timestamp": time.time(),
            "url": url,
            "status": status,
            "message": message,
        })

    def get_security_log(self) -> List[dict]:
        """获取安全日志"""
        return self.security_log.copy()

    def clear_log(self) -> None:
        """清除安全日志"""
        self.security_log.clear()


class HtmlSanitizer:
    """HTML 内容清理器 - 确保处理不可信数据"""

    @staticmethod
    def sanitize(content: str) -> str:
        """
        清理页面内容，移除潜在危险元素
        这里我们只返回纯文本内容
        """
        # 移除所有脚本标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)

        # 移除所有事件处理器属性
        content = re.sub(r'\son\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)

        # 移除 style 标签中的表达式
        content = re.sub(r'expression\s*\(', '', content, flags=re.IGNORECASE)

        # 移除 hyperlink 中的 javascript:
        content = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', '', content, flags=re.IGNORECASE)

        # 转换为纯文本（简化）
        text_content = re.sub(r'<[^>]+>', '', content)

        # 清理多余空白
        text_content = re.sub(r'\s+', ' ', text_content).strip()

        return text_content

    @staticmethod
    def extract_links(html: str) -> List[str]:
        """从 HTML 中提取链接"""
        links = []
        # 简单的链接提取
        pattern = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
        for match in pattern.finditer(html):
            link = match.group(1)
            if link and not link.startswith(('javascript:', 'mailto:', 'tel:')):
                links.append(link)
        return links
