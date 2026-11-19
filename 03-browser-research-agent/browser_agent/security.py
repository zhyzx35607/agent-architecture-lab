"""
安全工具模块 - 提供 URL 验证和安全检查
"""

from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
import re
import time


@dataclass
class SecurityEvent:
    """安全事件记录"""
    timestamp: float
    url: str
    event_type: str  # "allowed", "blocked", "error"
    message: str
    ip_address: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "url": self.url,
            "event_type": self.event_type,
            "message": self.message,
            "ip_address": self.ip_address,
        }


class SecurityError(Exception):
    """安全异常类"""
    def __init__(self, message: str, url: str = ""):
        self.message = message
        self.url = url
        super().__init__(self.message)


class URLValidator:
    """URL 验证器 - 严格控制的安全检查"""

    # 默认白名单域名
    DEFAULT_WHITELIST_DOMAINS: Set[str] = {
        "news.mock.com",
        "demo.mock.com",
        "local.mock.com",
    }

    # 禁止的协议
    PROTOCOL_BLACKLIST: Set[str] = {"http", "ftp", "file", "javascript", "data"}

    # SSRF 防护 - 禁止的 host
    SSRF_BLACKLIST_HOSTS: Set[str] = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "localhost.localdomain",
        "::1",
        "fe80::1",
    }

    # 禁止的私有 IP 段（SSRF 防护）
    PRIVATE_IP_RANGES: List[Tuple[int, int]] = [
        (0x7f000000, 0x7fffffff),       # 127.0.0.0/8
        (0xac100000, 0xac1fffff),     # 172.16.0.0/12
        (0xc0a80000, 0xc0a8ffff),     # 192.168.0.0/16
        (0x0a000000, 0x0affffff),     # 10.0.0.0/8
    ]

    def __init__(self, whitelist_domains: Optional[Set[str]] = None):
        self.whitelist_domains = whitelist_domains or self.DEFAULT_WHITELIST_DOMAINS.copy()
        self.security_events: List[SecurityEvent] = []

    def validate(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        验证 URL 安全性

        Args:
            url: 要验证的 URL

        Returns:
            Tuple[bool, Optional[str]]: (是否安全，错误信息)
        """
        if not url or not isinstance(url, str):
            return False, "URL 格式无效"

        # 检查 URL 开头的危险协议（如 javascript:）
        url_lower = url.lower()
        for proto in self.PROTOCOL_BLACKLIST:
            if url_lower.startswith(proto + ":"):
                return False, f"禁止使用 {proto}:// 协议"

        # 1. 检查协议
        protocol, host, path = self._parse_url(url)

        if protocol is None:
            return False, "URL 格式无效，必须包含协议 (如 https://)"

        protocol = protocol.lower()

        # 2. 检查协议白名单（仅允许 https）
        if protocol not in {"https"}:
            return False, f"仅允许 https 协议，禁止使用 {protocol}:// 协议"

        # 3. 检查 SSRF 防护
        if self._is_ssrf_risk(host):
            return False, f"禁止访问 {host} (SSRF 防护)"

        # 4. 检查域名白名单
        if host not in self.whitelist_domains:
            return False, f"域名 {host} 不在白名单中"

        # 5. 检查 URL 长度限制 (防止 memory exhaustion)
        if len(url) > 2048:
            return False, "URL 过长"

        return True, None

    def _parse_url(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        解析 URL
        Returns: (protocol, host, path)
        """
        # 简单解析
        if "://" in url:
            protocol, rest = url.split("://", 1)
        else:
            return None, None, None

        # 提取 host
        if "/" in rest:
            host_path = rest.split("/", 1)
            host = host_path[0].split(":")[0]
            path = "/" + host_path[1] if len(host_path) > 1 else "/"
        else:
            host = rest.split(":")[0]
            path = "/"

        return protocol, host, path

    def _is_ssrf_risk(self, host: str) -> bool:
        """
        检查是否有 SSRF 风险
        """
        if not host:
            return True

        host = host.lower()

        # 检查黑名单 host
        if host in self.SSRF_BLACKLIST_HOSTS:
            return True

        # 检查 localhost 变体
        if host.startswith("localhost"):
            return True

        # 检查 IP 地址格式
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            try:
                parts = list(map(int, host.split('.')))
                ip_int = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
                for start, end in self.PRIVATE_IP_RANGES:
                    if start <= ip_int <= end:
                        return True
            except ValueError:
                pass

        # 检查 IPv6
        if host.startswith('::1') or host == '::1':
            return True

        return False

    def is_https_only(self, url: str) -> bool:
        """检查 URL 是否仅使用 HTTPS"""
        if "://" in url:
            protocol = url.split("://")[0].lower()
            return protocol == "https"
        return False

    def log_event(self, url: str, event_type: str, message: str, ip_address: Optional[str] = None) -> None:
        """记录安全事件"""
        event = SecurityEvent(
            timestamp=time.time(),
            url=url,
            event_type=event_type,
            message=message,
            ip_address=ip_address,
        )
        self.security_events.append(event)

    def get_events(self) -> List[SecurityEvent]:
        """获取安全事件列表"""
        return self.security_events.copy()

    def clear_events(self) -> None:
        """清除安全事件"""
        self.security_events.clear()

    def add_to_whitelist(self, domain: str) -> None:
        """向白名单添加域名"""
        self.whitelist_domains.add(domain.lower())

    def remove_from_whitelist(self, domain: str) -> None:
        """从白名单移除域名"""
        if domain.lower() in self.whitelist_domains:
            self.whitelist_domains.remove(domain.lower())

    def validate_and_log(self, url: str, user_id: Optional[str] = None) -> Tuple[bool, Optional[str], SecurityEvent]:
        """
        验证 URL 并记录事件
        Returns: (是否有效，错误信息，事件对象)
        """
        is_valid, error_msg = self.validate(url)

        if is_valid:
            self.log_event(url, "allowed", "URL 验证通过", user_id)
        else:
            self.log_event(url, "blocked", error_msg or "验证失败", user_id)

        return is_valid, error_msg, SecurityEvent(
            timestamp=time.time(),
            url=url,
            event_type="allowed" if is_valid else "blocked",
            message=error_msg or ("验证通过" if is_valid else "验证失败"),
            ip_address=user_id,
        )


class ContentSanitizer:
    """HTML 内容清理器 - 处理不可信数据"""

    # 禁止的 HTML 标签
    FORBIDDEN_TAGS = {"script", "iframe", "object", "embed", "form", "input", "button"}

    # 禁止的事件处理器
    FORBIDDEN_EVENTS = {
        "onload", "onerror", "onclick", "onmouseover", "onmouseout",
        "onfocus", "onblur", "onsubmit", "onchange", "onkeydown",
        "onkeyup", "onkeypress", "onscroll", "onresize"
    }

    # 禁止的属性前缀
    FORBIDDEN_ATTR_PREFIXES = {"javascript:", "vbscript:"}

    @classmethod
    def sanitize(cls, html_content: str) -> str:
        """彻底清理 HTML 内容"""
        # 1. 移除所有 script 标签
        html_content = re.sub(
            r'<script\b[^>]*>.*?</script>',
            '',
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )

        # 2. 移除所有事件处理器属性
        for event in cls.FORBIDDEN_EVENTS:
            html_content = re.sub(
                rf'{event}\s*=\s*["\'][^"\']*["\']',
                '',
                html_content,
                flags=re.IGNORECASE
            )

        # 3. 移除 iframe, object, embed 标签
        for tag in cls.FORBIDDEN_TAGS:
            html_content = re.sub(
                rf'<{tag}\b[^>]*>.*?</{tag}>',
                '',
                html_content,
                flags=re.IGNORECASE | re.DOTALL
            )
            html_content = re.sub(
                rf'<{tag}\b[^>]*\/>',
                '',
                html_content,
                flags=re.IGNORECASE
            )

        # 4. 清理 javascript: 链接
        html_content = re.sub(
            r'href\s*=\s*["\']javascript:[^"\']*["\']',
            'href="#"',
            html_content,
            flags=re.IGNORECASE
        )

        # 5. 转换为纯文本（最安全的做法）
        # 移除所有 HTML 标签
        text_content = re.sub(r'<[^>]+>', ' ', html_content)

        # 清理多余空白
        text_content = re.sub(r'\s+', ' ', text_content).strip()

        return text_content

    @classmethod
    def extract_links_safely(cls, html_content: str) -> List[str]:
        """安全地提取链接"""
        links = []

        # 提取 href 属性
        href_pattern = re.compile(r'href\s*=\s*["\']([^"\']+)]["\']', re.IGNORECASE)

        for match in href_pattern.finditer(html_content):
            link = match.group(1)

            # 过滤危险链接
            if cls._is_safe_link(link):
                links.append(link)

        return links

    @classmethod
    def _is_safe_link(cls, link: str) -> bool:
        """检查链接是否安全"""
        if not link:
            return False

        link_lower = link.lower()

        # 禁止 javascript: 链接
        if link_lower.startswith('javascript:'):
            return False

        # 禁止 data: 链接
        if link_lower.startswith('data:'):
            return False

        # 允许 https, http, /path 相对链接，#anchor 片段
        if link_lower.startswith('https://') or link_lower.startswith('http://'):
            return True

        if link.startswith('/') or link.startswith('./') or link.startswith('../'):
            return True

        if link.startswith('#'):
            return True

        return False

    @classmethod
    def sanitize_content(cls, text: str) -> str:
        """净化文本内容"""
        # 移除控制字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        # 清理字形控制符
        text = re.sub(r'[\u200b-\u200d]', '', text)

        # 重置方向符
        text = re.sub(r'[\u202a-\u202e]', '', text)

        return text.strip()


class SecurityFilter:
    """综合安全过滤器"""

    def __init__(self, whitelist_domains: Optional[Set[str]] = None):
        self.url_validator = URLValidator(whitelist_domains)
        self.sanitizer = ContentSanitizer()

    def is_safe_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """检查 URL 是否安全"""
        return self.url_validator.validate(url)

    def validate_and_sanitize(self, url: str, content: str) -> Tuple[Optional[str], Optional[str]]:
        """
        验证 URL 并清理内容
        Returns: (清理后的内容，错误信息)
        """
        # 验证 URL
        is_valid, error = self.is_safe_url(url)
        if not is_valid:
            return None, error

        # 清理内容
        return self.sanitizer.sanitize(content), None

    def get_security_events(self) -> List[SecurityEvent]:
        """获取所有安全事件"""
        return self.url_validator.get_events()
