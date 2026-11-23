from os import getenv

from fastmcp import FastMCP
from patchright.async_api import async_playwright

_pw = _ctx = _page = None

async def page():
    global _pw, _ctx, _page
    if _page is None or _page.is_closed():
        _pw = _pw or await async_playwright().start()
        _ctx = _ctx or await _pw.chromium.launch_persistent_context(
            "/tmp/prof",
            executable_path=getenv("CHROMIUM_PATH"),
            channel="chrome",
            headless=False,
            no_viewport=True)
        _page = _ctx.pages[-1] if _ctx.pages else await _ctx.new_page()
    return _page

async def see() -> str:
    """
    Get the aria_snapshot of the current page.
    """
    return await (await page()).locator("body").aria_snapshot()


async def go(url: str) -> str:
    """
    Visit a page in the browser.
    """
    p = await page(); await p.goto(url); return p.url


async def click(selector: str) -> str:
    """
    Click an element.
    Args:
    selector: The selector found in aria_snapshot
    """
    await (await page()).click(selector); return "ok"


async def type_text(selector: str, text: str) -> str:
    """
    Type text into an element.
    Args:
    selector: The selector found in aria_snapshot
    """
    await (await page()).fill(selector, text); return "ok"


async def html() -> str:
    """
    Get the entire raw HTML content of the current page.
    """
    return await (await page()).content()
    
def register_tools(mcp: FastMCP):
    mcp.tool(see)
    mcp.tool(go)
    mcp.tool(click)
    mcp.tool(type_text)
    mcp.tool(html)
