"""
研究工作流 - 多跳跨页面研究引擎
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Tuple, Protocol
import asyncio
import time

from .mock_browser import MockBrowser, MockPage
from .fetcher import MockFetcher, Fetched, HtmlSanitizer
from .adapter import RelevanceAdapter, StrategyAdapter, QueryResult, MockLLMAdapter
from .security import SecurityFilter, SecurityError


@dataclass
class ResearchResult:
    """研究工作结果"""
    query: str
    relevant_pages: List[Fetched]
    citations: List[str]
    total_pages_visited: int
    max_depth_reached: int
    search_duration: float
    security_violations: List[dict]
    errors: List[str]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "relevant_pages": [
                {"url": p.url, "title": p.title, "content": p.content}
                for p in self.relevant_pages
            ],
            "citations": self.citations,
            "total_pages_visited": self.total_pages_visited,
            "max_depth_reached": self.max_depth_reached,
            "search_duration": self.search_duration,
            "security_violations": self.security_violations,
            "errors": self.errors,
        }


class ResearchWorkflow:
    """
    多跳研究工作流引擎
    实现跨页面导航、相关性评估、引用生成和安全控制
    """

    def __init__(
        self,
        browser: MockBrowser,
        query: str,
        max_depth: int = 3,
        max_pages: int = 10,
        timeout_per_page: float = 5.0,
        sensitivity: float = 0.5,
    ):
        """
        初始化研究工作流

        Args:
            browser: MockBrowser 实例
            query: 研究查询
            max_depth: 最大搜索深度
            max_pages: 最大访问页面数
            timeout_per_page: 每页超时时间
            sensitivity: 相关性敏感度 (0.0-1.0)
        """
        self.browser = browser
        self.query = query
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout_per_page = timeout_per_page

        # 解析查询关键词
        self.query_keywords = query.lower().split()

        # 初始化组件
        self.adapter = RelevanceAdapter(self.query_keywords, sensitivity)
        self.fetcher = MockFetcher(browser)
        self.security_filter = SecurityFilter()

        # 状态跟踪
        self.visited_urls: Set[str] = set()
        self.page_counter = 0
        self.current_depth = 0
        self.findings: List[Fetched] = []
        self.relevant_queue: List[Tuple[str, float]] = []

        # 结果记录
        self.citations: List[str] = []
        self.security_violations: List[dict] = []
        self.errors: List[str] = []

        # 时间跟踪
        self.start_time: Optional[float] = None
        self.duration = 0.0

    async def run(self) -> ResearchResult:
        """执行研究工作流"""
        self.start_time = time.time()

        try:
            # 1. 访问起始页面
            initial_url = "https://news.mock.com/tech"
            await self._visit_page(initial_url, depth=0)

            # 2. 开始跨页面研究
            await self._explore_relevant_links()

        except asyncio.TimeoutError:
            self.errors.append("研究超时")
        except Exception as e:
            self.errors.append(f"研究工作异常：{str(e)}")

        self.duration = time.time() - self.start_time if self.start_time else 0.0

        return ResearchResult(
            query=self.query,
            relevant_pages=self.findings,
            citations=self.citations,
            total_pages_visited=self.page_counter,
            max_depth_reached=self.current_depth,
            search_duration=self.duration,
            security_violations=self.security_violations,
            errors=self.errors,
        )

    async def _visit_page(self, url: str, depth: int) -> Optional[Fetched]:
        """访问单个页面并处理结果"""
        # 检查深度限制
        if depth > self.max_depth:
            return None

        # 安全检查
        is_valid, error = self.security_filter.is_safe_url(url)
        if not is_valid:
            violation = {"url": url, "error": error}
            self.security_violations.append(violation)
            self.errors.append(f"安全阻止：{url} - {error}")
            return None

        # 如果已访问过，跳过
        if url in self.visited_urls:
            return None

        # 检查页面数限制
        if self.page_counter >= self.max_pages:
            return None

        # 标记为已访问
        self.visited_urls.add(url)
        self.page_counter += 1
        self.current_depth = max(self.current_depth, depth)

        # 获取页面内容
        fetched = await self.fetcher.fetch(url, self.timeout_per_page)

        if fetched and fetched.error is None:
            # 处理页面内容
            await self._process_page(fetched, depth)
            return fetched

        elif fetched:
            self.errors.append(f"访问失败：{url} - {fetched.error}")

        return None

    async def _process_page(self, fetched: Fetched, depth: int) -> None:
        """处理访问的页面"""
        if not fetched.content:
            return

        # 清理内容
        cleaned_content = HtmlSanitizer.sanitize(fetched.content)

        # 评估相关性
        is_relevant, relevance_score, key_points = self.adapter.judge_relevance(
            cleaned_content,
            self.query
        )

        # 如果相关，添加到结果
        if is_relevant:
            self.findings.append(fetched)

            # 生成引用
            for point in key_points[:2]:
                citation = f"[{fetched.title}] {point.strip()}"
                if citation not in self.citations:
                    self.citations.append(citation)

        # 提取链接
        links = fetched.links if fetched.links else HtmlSanitizer.extract_links(fetched.content)

        # 过滤并排序链接
        relevant_links = []
        for link in links:
            # 完整 URL 检查
            if link.startswith(('http://', 'https://')):
                full_url = link
            else:
                # 简化的相对链接处理
                base = fetched.url[:fetched.url.rfind('/') + 1]
                full_url = base + link

            # 安全检查
            is_valid, error = self.security_filter.is_safe_url(full_url)
            if not is_valid or full_url in self.visited_urls:
                continue

            # 评估链接相关性（基于 URL 文本）
            link_relevance = self._estimate_link_relevance(full_url, cleaned_content)
            relevant_links.append((full_url, link_relevance))

        # 按相关性排序
        relevant_links.sort(key=lambda x: x[1], reverse=True)

        # 按深度优先顺序访问下一跳
        for next_url, _ in relevant_links[:2]:  # 每次最多访问 2 个相关链接
            await self._visit_page(next_url, depth + 1)

    def _estimate_link_relevance(self, url: str, context: str) -> float:
        """估算链接与查询的相关性"""
        url_lower = url.lower()
        context_lower = context.lower()

        # 统计查询关键词在 URL 中的出现
        keyword_matches = sum(1 for kw in self.query_keywords if kw in url_lower)

        # 统计 URL 附近上下文的相关性
        url_context_start = max(0, context_lower.find(url_lower) - 100)
        url_context_end = min(len(context_lower), context_lower.find(url_lower) + 400)
        url_context = context_lower[url_context_start:url_context_end]

        context_matches = sum(1 for kw in self.query_keywords if kw in url_context)

        # 综合评分
        score = keyword_matches * 0.3 + context_matches * 0.2

        return min(score, 1.0)

    async def _explore_relevant_links(self) -> None:
        """探索相关链接（备用的广度优先策略）"""
        # 这个方法是备用的探索策略
        # 主逻辑已在 _visit_page 的递归中实现

        pass

    def get_summary(self) -> str:
        """获取研究摘要"""
        return (
            f"研究完成！访问了 {self.page_counter} 个页面，"
            f"相关结果 {len(self.findings)} 个，"
            f"生成引用 {len(self.citations)} 条，"
            f"耗时 {self.duration:.2f} 秒。"
        )


class ResearchHub:
    """
    研究中心 - 管理多个研究工作流
    """

    def __init__(self, browser: MockBrowser):
        self.browser = browser
        self.active_workflows: List[ResearchWorkflow] = []
        self.results: List[ResearchResult] = []

    async def run_research(self, query: str, **kwargs) -> ResearchResult:
        """运行单次研究"""
        workflow = ResearchWorkflow(self.browser, query, **kwargs)
        self.active_workflows.append(workflow)

        result = await workflow.run()
        self.results.append(result)

        return result

    def merge_results(self, results: List[ResearchResult]) -> ResearchResult:
        """合并多个研究结果"""
        if not results:
            return ResearchResult(
                query="",
                relevant_pages=[],
                citations=[],
                total_pages_visited=0,
                max_depth_reached=0,
                search_duration=0.0,
                security_violations=[],
                errors=[],
            )

        # 合并所有相关页面和引用
        all_pages = []
        all_citations = set()
        all_violations = []
        all_errors = []
        max_pages = 0
        total_duration = 0.0

        for result in results:
            all_pages.extend(result.relevant_pages)
            all_citations.update(result.citations)
            all_violations.extend(result.security_violations)
            all_errors.extend(result.errors)
            max_pages = max(max_pages, result.total_pages_visited)
            total_duration += result.search_duration

        # 去重
        unique_pages = self._deduplicate_pages(all_pages)

        return ResearchResult(
            query="|".join(r.query for r in results),
            relevant_pages=unique_pages,
            citations=list(all_citations),
            total_pages_visited=max_pages,
            max_depth_reached=max(r.max_depth_reached for r in results),
            search_duration=total_duration,
            security_violations=all_violations,
            errors=all_errors,
        )

    def _deduplicate_pages(self, pages: List[Fetched]) -> List[Fetched]:
        """去重页面"""
        seen = set()
        unique = []

        for page in pages:
            if page.url not in seen:
                seen.add(page.url)
                unique.append(page)

        return unique

    def clear(self) -> None:
        """清空所有状态"""
        self.active_workflows.clear()
        self.results.clear()
        self.browser.clear()
