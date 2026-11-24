from fastmcp import FastMCP

from web4ai.lifespan import BrowserCtx


async def page(ctx: BrowserCtx):
    return ctx.pages[0]

async def see(ctx: BrowserCtx) -> str:
    """
    Get the aria_snapshot of the current page.
    """
    return await (await page(ctx)).locator("body").aria_snapshot()


async def go(url: str, ctx: BrowserCtx) -> str:
    """
    Visit a page in the browser.
    """
    p = await page(ctx); await p.goto(url); return p.url


async def click(selector: str, ctx: BrowserCtx) -> str:
    """
    Click an element.
    Args:
    selector: The selector found in aria_snapshot
    """
    await (await page(ctx)).click(selector); return "ok"


async def type_text(selector: str, text: str, ctx: BrowserCtx) -> str:
    """
    Type text into an element.
    Args:
    selector: The selector found in aria_snapshot
    """
    await (await page(ctx)).fill(selector, text); return "ok"


async def html(ctx: BrowserCtx) -> str:
    """
    Get the entire raw HTML content of the current page.
    """
    return await (await page(ctx)).content()
    
def register_tools(mcp: FastMCP):
    mcp.tool(see)
    mcp.tool(go)
    mcp.tool(click)
    mcp.tool(type_text)
    mcp.tool(html)
