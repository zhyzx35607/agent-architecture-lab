"""
内存浏览器模拟 - 提供 mock 网站和页面数据
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


@dataclass
class MockPage:
    """单页 mock 数据"""
    url: str
    title: str
    content: str
    links: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    is_relevant: bool = False

    def to_fetched(self) -> "Fetched":
        """转换为 Fetched 格式"""
        from .fetcher import Fetched
        return Fetched(
            url=self.url,
            title=self.title,
            content=self.content,
            links=self.links,
            timestamp=self.timestamp
        )


@dataclass
class Fetched:
    """获取结果"""
    url: str
    title: str
    content: str
    links: List[str]
    timestamp: float


class MockBrowser:
    """模拟浏览器 - 纯内存站点管理"""

    def __init__(self):
        self.pages: Dict[str, MockPage] = {}
        self._setup_mock_sites()

    def _setup_mock_sites(self) -> None:
        """设置演示用的 mock 站点"""
        # Mock 页面 1 - 科技新闻首页
        self.pages["https://news.mock.com/tech"] = MockPage(
            url="https://news.mock.com/tech",
            title="科技新闻 - 首页",
            content="""
            # 科技新闻头条

            ## 人工智能新突破
            研究人员开发出新型 AI 模型，在多个基准测试中取得显著成绩。该模型采用新的架构设计，提高了推理效率。

            ## 量子计算进展
            量子计算机在特定问题上展现出指数级加速能力，为密码学和材料科学带来新机遇。

            ## 链接：[量子计算详解](https://news.mock.com/tech/quantum)、[AI 模型分析](https://news.mock.com/tech/ai-analysis)
            """,
            links=[
                "https://news.mock.com/tech/quantum",
                "https://news.mock.com/tech/ai-analysis",
                "https://news.mock.com/science",
            ]
        )

        # Mock 页面 2 - 量子计算详解
        self.pages["https://news.mock.com/tech/quantum"] = MockPage(
            url="https://news.mock.com/tech/quantum",
            title="量子计算详解",
            content="""
            # 量子计算详解

            量子计算利用量子力学原理进行计算，具有传统计算机无法比拟的并行处理能力。

            ## 基本原理
            量子比特可以同时处于多个状态，这使得量子计算机能够同时处理大量计算。

            ## 应用领域
            - 密码学：破解传统加密，开发量子密码
            - 材料科学：模拟分子结构
            - 优化问题：物流、金融等领域的复杂优化

            ## 链接：[回到科技首页](https://news.mock.com/tech)、[科学新闻](https://news.mock.com/science)
            """,
            links=[
                "https://news.mock.com/tech",
                "https://news.mock.com/science",
            ]
        )

        # Mock 页面 3 - AI 模型分析
        self.pages["https://news.mock.com/tech/ai-analysis"] = MockPage(
            url="https://news.mock.com/tech/ai-analysis",
            title="AI 模型深度分析",
            content="""
            # AI 模型深度分析

            新型 AI 模型采用了一些创新的设计，使其在保持高精度的同时提高了效率。

            ## 架构特点
            1. 分层注意力机制
            2. 动态路由网络
            3. 混合精度训练

            ## 性能对比
            在图像识别任务上，推理速度提升 40%，准确性提高 5%。

            ## 链接：[回到科技首页](https://news.mock.com/tech)
            """,
            links=[
                "https://news.mock.com/tech",
            ]
        )

        # Mock 页面 4 - 科学新闻
        self.pages["https://news.mock.com/science"] = MockPage(
            url="https://news.mock.com/science",
            title="科学新闻",
            content="""
            # 科学新闻

            ## 新物种发现
            科学家在深海探险中发现多个新物种，丰富了生物多样性研究。

            ## 气候变化研究
            最新研究揭示气候变化对生态系统的影响比预期更为严重。

            ## 链接：[科技新闻](https://news.mock.com/tech)、[医学进展](https://news.mock.com/medical)
            """,
            links=[
                "https://news.mock.com/tech",
                "https://news.mock.com/medical",
            ]
        )

        # Mock 页面 5 - 医学进展
        self.pages["https://news.mock.com/medical"] = MockPage(
            url="https://news.mock.com/medical",
            title="医学进展",
            content="""
            # 医学进展

            ## 新药研发突破
            新型药物在临床试验中展现出显著疗效，为治疗某种疾病带来希望。

            ## 基因编辑技术
            基因编辑技术在遗传病治疗方面取得重要进展。

            ## 链接：[科学新闻](https://news.mock.com/science)
            """,
            links=[
                "https://news.mock.com/science",
            ]
        )

        # Mock 页面 6 - 政治新闻（用于测试非相关页面）
        self.pages["https://news.mock.com/politics"] = MockPage(
            url="https://news.mock.com/politics",
            title="政治新闻",
            content="""
            # 政治新闻

            各国政府正在讨论新的经济政策，以应对全球挑战。

            ## 链接：[返回首页](https://news.mock.com)
            """,
            links=[
                "https://news.mock.com",
            ]
        )

    async def visit(self, url: str, timeout: float = 5.0) -> Optional[Fetched]:
        """访问页面，返回结果或 None（超时/不存在）"""
        await self._simulate_delay(timeout)

        if url in self.pages:
            return self.pages[url].to_fetched()
        return None

    async def _simulate_delay(self, timeout: float) -> None:
        """模拟网络延迟"""
        # 简化：不实际 sleep，但保留接口
        pass

    def get_page(self, url: str) -> Optional[MockPage]:
        """直接获取 MockPage 对象"""
        return self.pages.get(url)

    def add_page(self, page: MockPage) -> None:
        """添加自定义页面到内存浏览器"""
        self.pages[page.url] = page

    def clear(self) -> None:
        """清除所有页面"""
        self.pages.clear()

    def is_valid_url(self, url: str) -> bool:
        """检查 URL 是否在 mock 站点中"""
        return url in self.pages
