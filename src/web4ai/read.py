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
from peewee import IntegrityError
from requests import get
from toon import encode

from web4ai.data import FetchState, SearchState

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
    cache_mode=CacheMode.BYPASS,
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilterLXML(
            threshold=0.45, threshold_type="dynamic", min_word_threshold=5)),
)


async def register_tools(mcp: FastMCP):
    await crawler.start()
    @mcp.tool
    def search(query: str) -> str:
        """Search the web for query.
        Args:
        query: The search terms to look up.
        """
        try:
            SearchState(query=query, result="In progress.").save()
            results = get(f"http://localhost:8080/search?q={query}&format=json").json()["results"]
            data = [{"title": a["title"], "url": a["url"]} for a in results]
            SearchState.update(result=data).where(SearchState.query == query).execute()
            return encode(data)
        except IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                return "That query has already been searched. Try another one."
            else:
                raise

    @mcp.tool
    async def fetch(url: str) -> str:
        """Fetch a url and get the content.
        Args:
        url: The url to fetch.
        """
        try:
            FetchState(url=url, result="In progress.").save()
            async with crawler_lock:
                r = await crawler.arun(url, config=config)
            if r.markdown is not None:
                FetchState.update(result=r.markdown).where(FetchState.url == url).execute()
                return r.markdown
            else:
                return "Fetch returned no content."
        except IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                return "That url has already been scraped. Try another one."
            else:
                raise

