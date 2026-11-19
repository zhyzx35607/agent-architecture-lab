"""Browser research agent: deterministic local sample pages only."""
from browser_agent.mini import BrowserResearchAgent, Citation, MockBrowser, Page, ResearchResult, URLPolicyError

BASE="https://news.mock.com/tech"

def sample_browser():
    browser=MockBrowser({"news.mock.com"})
    browser.add_page(Page(BASE,"Technology", "AI 技术推荐与测评：本页介绍人工智能的发展与评测方法。",("/research","/other")))
    browser.add_page(Page("https://news.mock.com/research","Research notes", "AI 推荐基于可解释的 benchmark 和人工评测，来源需要比对。",("/other",)))
    browser.add_page(Page("https://news.mock.com/other","Related notes", "This local mock page discusses unrelated garden plants."))
    return browser

def main():
    result=BrowserResearchAgent(sample_browser(),max_pages=5,max_depth=2).research(BASE,"AI 推荐")
    print("Summary:",result.summary)
    print(f"Pages visited: {len(result.pages_visited)}")
    for citation in result.citations: print(f"[{citation.title}] {citation.url}\n  {citation.quote}")
    print(f"Citations: {len(result.citations)}; recoverable errors: {len(result.errors)}")

if __name__=="__main__":main()
