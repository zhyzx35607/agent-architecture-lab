"""完全离线的白名单浏览器研究 Agent。网页内容永远只是未信任数据。"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import re
from typing import Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

class URLPolicyError(ValueError): pass

@dataclass(frozen=True)
class Page:
    url: str
    title: str
    text: str
    links: tuple[str,...]=()

@dataclass(frozen=True)
class Citation:
    url: str
    title: str
    quote: str

class ModelAdapter(Protocol):
    def answer(self, query: str, citations: list[Citation]) -> str: ...

@dataclass(frozen=True)
class OfflineModelStub:
    def answer(self, query: str, citations: list[Citation]) -> str:
        return f"offline summary for {query}: {len(citations)} citations"

@dataclass
class ResearchResult:
    query: str
    pages_visited: list[str]
    citations: list[Citation]
    errors: list[str]
    summary: str = ""
Answerer = ModelAdapter
OfflineAnswerer = OfflineModelStub
class MockBrowser:
    def __init__(self, allowed_hosts: set[str]):
        self.allowed_hosts=frozenset(host.lower() for host in allowed_hosts)
        self.pages: dict[str,Page]={}
    def validate_url(self, url: str) -> str:
        try: parts=urlsplit(url)
        except ValueError as exc: raise URLPolicyError(f"invalid URL: {exc}") from exc
        if parts.scheme.lower()!="https": raise URLPolicyError(f"scheme {parts.scheme or '(missing)'} not allowed; require https")
        if not parts.hostname: raise URLPolicyError("URL has no host")
        host=parts.hostname.lower().rstrip(".")
        if parts.username or parts.password: raise URLPolicyError("userinfo in URL is forbidden")
        if host not in self.allowed_hosts: raise URLPolicyError(f"host {host!r} is not allow-listed")
        try:
            if parts.port not in (None,443): raise URLPolicyError("custom URL ports are forbidden")
        except ValueError as exc: raise URLPolicyError("invalid port") from exc
        return urlunsplit(("https",host,parts.path or "/",parts.query,""))
    def add_page(self, page: Page) -> None:
        url=self.validate_url(page.url)
        self.pages[url]=Page(url,page.title,page.text,tuple(page.links))
    def open(self, url: str) -> Page:
        canonical=self.validate_url(url)
        if canonical not in self.pages: raise LookupError(f"mock page not found: {canonical}")
        return self.pages[canonical]

def query_terms(text: str) -> tuple[str,...]:
    terms=[]
    for token in re.findall(r"[A-Za-z0-9]+|[\u3400-\u9fff]+",text.casefold()):
        if len(token)>1 and "\u3400"<=token[0]<="\u9fff": terms.extend(token[i:i+2] for i in range(len(token)-1))
        else: terms.append(token)
    return tuple(dict.fromkeys(terms))

class BrowserResearchAgent:
    def __init__(self, browser: MockBrowser, *, max_pages: int=8, max_depth: int=3,
                 model: ModelAdapter | None=None):
        if max_pages<1 or max_depth<0: raise ValueError("invalid research budget")
        self.browser=browser;self.max_pages=max_pages;self.max_depth=max_depth
        self.model=model or OfflineModelStub()
    def research(self, start_url: str, query: str) -> ResearchResult:
        terms=query_terms(query);pending=deque([(start_url,0)]);visited=[];seen=set();citations=[];errors=[]
        while pending and len(visited)<self.max_pages:
            raw,depth=pending.popleft()
            try: url=self.browser.validate_url(raw)
            except URLPolicyError as exc: errors.append(str(exc));continue
            if url in seen or depth>self.max_depth:continue
            seen.add(url)
            try: page=self.browser.open(url)
            except LookupError as exc: errors.append(str(exc));continue
            visited.append(url)
            clean=" ".join(page.text.split())
            matched=[term for term in terms if term in clean.casefold()]
            if matched: citations.append(Citation(page.url,page.title,clean[:240]))
            # Page-provided text is never executed; navigation is revalidated on each hop.
            if depth<self.max_depth:
                for link in page.links: pending.append((urljoin(page.url,link),depth+1))
        summary=self.model.answer(query,citations)
        return ResearchResult(query,visited,citations,errors,summary)
