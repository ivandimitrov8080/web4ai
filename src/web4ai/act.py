from fastmcp import FastMCP, Context

from web4ai.lifespan import BrowserCtx

def get_page(ctx: Context) -> int:
    req = ctx.request_context
    if req:
        meta = req.meta or {}
        return meta["page"]
    else:
        return 0

async def page(browser: BrowserCtx, ctx: Context):
    pages = browser.pages
    idx = get_page(ctx)
    if len(pages) > idx:
        return browser.pages[idx]
    else:
        return await browser.new_page()

async def see(browser: BrowserCtx, ctx: Context) -> str:
    """
    Get the aria_snapshot of the current page.
    """
    return await (await page(browser, ctx)).locator("body").aria_snapshot()


async def go(url: str, browser: BrowserCtx, ctx: Context) -> str:
    """
    Visit a page in the browser.
    """
    p = await page(browser, ctx); await p.goto(url); return p.url


async def click(selector: str, browser: BrowserCtx, ctx: Context) -> str:
    """
    Click an element.
    Args:
    selector: The selector found in aria_snapshot
    """
    await (await page(browser, ctx)).click(selector); return "ok"


async def type_text(selector: str, text: str, browser: BrowserCtx, ctx: Context) -> str:
    """
    Type text into an element.
    Args:
    selector: The selector found in aria_snapshot
    """
    await (await page(browser, ctx)).fill(selector, text); return "ok"


async def html(browser: BrowserCtx, ctx: Context) -> str:
    """
    Get the entire raw HTML content of the current page.
    """
    return await (await page(browser, ctx)).content()
    
def register_tools(mcp: FastMCP):
    mcp.tool(see)
    mcp.tool(go)
    mcp.tool(click)
    mcp.tool(type_text)
    mcp.tool(html)
