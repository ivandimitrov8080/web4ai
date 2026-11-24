"""Creates the shared browser resources once; inject them wherever you need."""
from contextlib import asynccontextmanager
from pathlib import Path
from shutil import which
from typing import Annotated

from crawl4ai import AsyncWebCrawler, BrowserConfig, UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from fastmcp import Context
from fastmcp.dependencies import CurrentContext, Depends
from fastmcp.server.lifespan import lifespan
from patchright.async_api import BrowserContext, Playwright, async_playwright

HOME = Path.home()

@lifespan
async def web_lifespan(_):
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=f"{HOME}/.local/share/web4ai/profile-patchright",
        executable_path=which("chromium"),
        headless=False,
    )

    browser_config = BrowserConfig(
        headless=True
    )
    strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=UndetectedAdapter(),
    )
    crawler = AsyncWebCrawler(crawler_strategy=strategy, config=browser_config)
    await crawler.start()

    try:
        yield {"pw": pw, "context": context, "crawler": crawler}
    finally:
        await crawler.close()
        await context.close()
        await pw.stop()

_current_context = CurrentContext()

@asynccontextmanager
async def get_playwright(ctx: Context = _current_context):
    yield ctx.lifespan_context["pw"]

@asynccontextmanager
async def get_browser_context(ctx: Context = _current_context):
    yield ctx.lifespan_context["context"]

@asynccontextmanager
async def get_crawler(ctx: Context = _current_context):
    yield ctx.lifespan_context["crawler"]


PW = Annotated[Playwright, Depends(get_playwright)]
BrowserCtx = Annotated[BrowserContext, Depends(get_browser_context)]
Crawler = Annotated[AsyncWebCrawler, Depends(get_crawler)]
