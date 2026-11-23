from asyncio import Lock
from pathlib import Path

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    DefaultMarkdownGenerator,
    PruningContentFilterLXML,
    UndetectedAdapter,
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from fastmcp import FastMCP
from requests import get
from toon import encode

from web4ai.util import rg

crawler_lock = Lock()

browser_config = BrowserConfig(
    headless=True,
    use_persistent_context=True,
    user_data_dir=str(Path.home() / ".local/share/web4ai/profile"),
)

strategy = AsyncPlaywrightCrawlerStrategy(
    browser_config=browser_config,
    browser_adapter=UndetectedAdapter(),
)

crawler = AsyncWebCrawler(crawler_strategy=strategy, config=browser_config)
config = CrawlerRunConfig(
    excluded_tags=["nav", "footer", "header", "aside", "form"],
    exclude_external_links=True,
    exclude_social_media_links=True,
    exclude_domains=["medium.com"],
    word_count_threshold=10,
    remove_overlay_elements=True,
    remove_consent_popups=True,
    cache_mode=CacheMode.ENABLED,
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilterLXML(
            threshold=0.45, threshold_type="dynamic", min_word_threshold=5)),
)

def search(query: str) -> str:
    """Search the web for query.
    Args:
    query: The search terms to look up.
    """
    results = get(f"http://localhost:8080/search?q={query}&format=json").json()["results"]
    data = [{"title": a["title"], "url": a["url"]} for a in results]
    return encode(data)


async def fetch(url: str, pattern: str = ".*") -> str:
    """Fetch a url and get the content with line numbers. Optionally use RipGrep to filter large output.
    Max 1000 lines will be returned.
    Args:
    url: The url to fetch.
    pattern: A RipGrep regex pattern to use for filtering content.
    """
    async with crawler_lock:
        r = await crawler.arun(url, config=config)
    if r.markdown is not None:
        return rg(r.markdown, pattern)
    else:
        return "Fetch returned no content."

async def register_tools(mcp: FastMCP):
    await crawler.start()
    mcp.add_tool(search)
    mcp.add_tool(fetch)
