"""
LLM/策略适配器 - 提供查询提取和相关性评估
"""

from typing import List, Optional, Tuple, Protocol
import re
from dataclasses import dataclass

 # 关键词同义词映射，解决中文匹配问题
 KEYWORD_SYNONYMS = {
     "ai": ["ai", "人工智能", "智能"],
     "科技": ["科技", "科学", "技术"],
 }

@dataclass
class QueryResult:
    """查询结果"""
    query: str
    relevance_score: float  # 0-1
    is_relevant: bool
    key_points: List[str]
    source_url: str
    title: str


class AdapterProtocol(Protocol):
    """适配器协议接口"""

    def extract_query(self, html_content: str) -> str:
        """从内容中提取相关查询"""
        ...

    def judge_relevance(self, content: str, query: str) -> Tuple[bool, float]:
        """判断内容相关性，返回(是否相关，相关度分数)"""
        ...


class RelevanceAdapter:
    """
    相关性适配器 - 基于关键词匹配和相关性策略
    模拟 LLM 的查询处理和相关性评估
    """

    def __init__(self, query_keywords: List[str], sensitivity: float = 0.6):
        """
        初始化适配器

        Args:
            query_keywords: 关键查询词列表
            sensitivity: 敏感度阈值 (0.0-1.0)，越低越容易判定为相关
        """
        self.query_keywords = [kw.lower() for kw in query_keywords]
        self.sensitivity = min(max(sensitivity, 0.0), 1.0)
        self.recall_count = 0

    def extract_query(self, html_content: str) -> str:
        """
        从 HTML 内容中提取与查询相关的信息
        提取标题和主要内容作为上下文
        """
        # 提取标题
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if not title_match:
            # 如果主要内容中有标题标记
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
            if h1_match:
                title = h1_match.group(1)
            else:
                title = "未命名页面"
        else:
            title = title_match.group(1)

        # 清理 HTML 标签，提取纯文本
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()

        # 限制文本长度
        if len(text_content) > 1000:
            text_content = text_content[:1000] + "..."

        # 组合查询
        query = f"查询：{' '.join(self.query_keywords)}\n上下文：{title} - {text_content}"

        return query

    def judge_relevance(self, content: str, query: str) -> Tuple[bool, float]:
        """
        基于关键词匹配和语义分析判断相关性

        Returns:
            Tuple[bool, float]: (是否相关，相关度分数 0-1)
        """
        # 将内容转换为小写
        content_lower = content.lower()
        query_lower = query.lower()

        # 1. 关键词匹配
        keyword_matches = 0
        total_keywords = len(self.query_keywords)
        keyword_scores = []

        for keyword in self.query_keywords:
            keyword_lower = keyword.lower()
            # 获取同义词列表
            synonyms = KEYWORD_SYNONYMS.get(keyword_lower, [keyword_lower])
            matched = False
            min_pos = float('inf')
            for syn in synonyms:
                pos = content_lower.find(syn)
                if pos != -1:
                    matched = True
                    if pos < min_pos:
                        min_pos = pos
            if matched:
                keyword_matches += 1
                # 优先计算标题和前面的段落
                if min_pos < 200:
                    keyword_scores.append(1.0)
                elif min_pos < 500:
                    keyword_scores.append(0.8)
                else:
                    keyword_scores.append(0.6)
            else:
                keyword_scores.append(0.0)

        # 关键词得分
        keyword_score = keyword_matches / total_keywords if total_keywords > 0 else 0.0

        # 2. 语义相关性（简化的词频分析）
        # 统计 query 中每个词在 content 中的出现次数
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())

        # Jaccard 相似系数
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)

        if union:
            semantic_score = len(intersection) / len(union)
        else:
            semantic_score = 0.0

        # 3. 标题相关性（权重更高）
        title_matches = 0
        for keyword in self.query_keywords:
            # 检查是否在标题或大标题中
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE)
            h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', content, re.IGNORECASE)

            contextual_text = ""
            if h1_match:
                contextual_text += h1_match.group(1).lower() + " "
            if h2_match:
                contextual_text += h2_match.group(1).lower() + " "

            if keyword.lower() in contextual_text:
                title_matches += 1

        title_score = title_matches / total_keywords if total_keywords > 0 else 0.0

        # 4. 综合得分（加权）
        # 关键词匹配， semantics，标题权重分别为 0.5, 0.3, 0.2
        composite_score = (
            keyword_score * 0.5 +
            semantic_score * 0.3 +
            title_score * 0.2
        )

        # 加上 momentum 因素（之前的相关性已知）
        momentum = 0.0
        if self.recall_count > 0:
            # 如果有历史记录，给予一定 boost
            momentum = 0.1

        final_score = min((composite_score + momentum), 1.0)

        # 判定是否相关
        is_relevant = final_score >= self.sensitivity

        self.recall_count += 1

        # 提取关键点
        key_points = self._extract_key_points(content, query)

        return is_relevant, final_score, key_points

    def _extract_key_points(self, content: str, query: str) -> List[str]:
         points = []

         # 按中文句号分割句子
         sentences = re.split(r'[。！？!]', content)

         for sent in sentences[:10]:
             sent = sent.strip()
             if sent and not sent.startswith('#') and len(sent) > 20:
                 points.append(sent[:200])

         return points

         return points

    def get_relevant_urls(self, results: List[QueryResult]) -> List[str]:
        """从相关结果中提取 relevant URLs"""
        relevant_urls = []
        for result in results:
            if result.is_relevant:
                relevant_urls.append(result.source_url)
        return relevant_urls

    def deduplicate_content(self, content_fragments: List[str]) -> List[str]:
        """去重内容片段"""
        seen = set()
        unique = []

        for fragment in content_fragments:
            # 标准化比较
            normalized = fragment.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(fragment)

        return unique

    def reset(self) -> None:
        """重置适配器状态"""
        self.recall_count = 0


class MockLLMAdapter:
    """
    模拟 LLM 适配器 - 提供更高级的语义理解
    用于单元测试和演示
    """

    def __init__(self, model_name: str = "mock-llm"):
        self.model_name = model_name
        self.last_query = None
        self.last_response = None

    def generate(
        self,
        query: str,
        context: Optional[str] = None,
        max_tokens: int = 100
    ) -> str:
        """生成响应"""
        self.last_query = query
        self.last_response = f"[模拟响应] 基于查询 '{query}' 和上下文'{context[:50]}...'，生成的答案是..."
        return self.last_response

    def summarize(
        self,
        content: str,
        max_length: int = 100
    ) -> str:
        """总结内容"""
        # 简化摘要
        if len(content) <= max_length:
            return content

        return content[:max_length - 3] + "..."

    def extract_citations(
        self,
        content: str,
        source_url: str,
        source_title: str
    ) -> List[str]:
        """提取引用"""
        citations = []

        # 提取关键点作为引用
        sentences = re.split(r'。|！|？', content)
        for sentence in sentences[:3]:  # 取前 3 个句子
            if sentence.strip():
                citations.append(f"[{source_title} ({source_url})] {sentence.strip()}")

        return citations


class StrategyAdapter(RelevanceAdapter):
    """
    策略适配器 - 扩展了相关性适配器
    实现多跳研究的策略逻辑
    """

    def __init__(self, query_keywords: List[str], strategy: str = "depth_first"):
        """
        初始化策略适配器

        Args:
            query_keywords: 查询关键词
            strategy: 搜索策略 ("depth_first", "breadth_first", "relevance")
        """
        super().__init__(query_keywords)
        self.strategy = strategy
        self.visted_urls = set()
        self.next_queue = []

    def reset(self) -> None:
        """重置策略状态"""
        super().reset()
        self.visted_urls.clear()
        self.next_queue.clear()

    def add_to_queue(self, url: str, relevance: float) -> None:
        """将 URL 加入队列"""
        if url not in self.visted_urls:
            self.next_queue.append((url, relevance))
            # 按相关性排序
            self.next_queue.sort(key=lambda x: x[1], reverse=True)

    def get_next_url(self) -> Optional[str]:
        """获取下一个要访问的 URL"""
        if self.next_queue:
            url, _ = self.next_queue.pop(0)
            self.visted_urls.add(url)
            return url
        return None

    def should_continue(self, depth: int, max_depth: int, page_count: int) -> bool:
        """判断是否应该继续研究"""
        if depth >= max_depth:
            return False
        if page_count >= 10:  # 最大页面数限制
            return False
        return True
