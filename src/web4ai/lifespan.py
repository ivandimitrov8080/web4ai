"""Creates the shared browser resources once; inject them wherever you need."""
from shutil import which
from pathlib import Path
from typing import Annotated

from crawl4ai import AsyncWebCrawler, BrowserConfig, UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from fastmcp import Context
from fastmcp.dependencies import CurrentContext, Depends
from fastmcp.server.lifespan import lifespan   # 2.x/3.x: use @asynccontextmanager
from playwright.async_api import BrowserContext, Playwright, async_playwright

HOME = Path.home()


@lifespan
async def web_lifespan(_):
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=str(HOME / ".local/share/web4ai/profile-playwright"),
        executable_path=which("chromium"),
        headless=True,
    )

    browser_config = BrowserConfig(
        headless=True,
        use_persistent_context=True,
        user_data_dir=str(HOME / ".local/share/web4ai/profile"),
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


def get_playwright(ctx: Context = CurrentContext()) -> Playwright:
    return ctx.lifespan_context["pw"]


def get_browser_context(ctx: Context = CurrentContext()) -> BrowserContext:
    return ctx.lifespan_context["context"]


def get_crawler(ctx: Context = CurrentContext()) -> AsyncWebCrawler:
    return ctx.lifespan_context["crawler"]


PW = Annotated[Playwright, Depends(get_playwright)]
BrowserCtx = Annotated[BrowserContext, Depends(get_browser_context)]
Crawler = Annotated[AsyncWebCrawler, Depends(get_crawler)]
